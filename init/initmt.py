# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///

"""Chinese → Burmese and Chinese → English → Burmese candidates, with approved phrase memory.

Default is an offline plan. --run explicitly enables Azure NMT requests.
API credentials are read from the environment only, never written by this tool.
Machine translations are cached but are NEVER auto-approved into translation memory.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
from typing import Iterator
import urllib.parse

import httpx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENDPOINT = "https://api.cognitive.microsofttranslator.com"
DEFAULT_CACHE = ROOT / "content" / "mtranslate" / "cache.sqlite3"
DEFAULT_MEMORY = ROOT / "content" / "mtranslate" / "memory.sqlite3"
SCHEMA_VERSION = 2
# An HCrawler marker line belongs to the chapter header that follows it, so it
# is consumed with the header and never becomes translatable chapter text.
MARKER = r"\[\[HCRAWLER MARKER (?P<marker>\d+)\]\]"
SECTION = re.compile(
    r"^(?:" + MARKER + r"\s*\n)?=====\s+(?P<chapter>.+?)\s+=====\s*$", re.MULTILINE
)
MARKER_ONLY = re.compile(r"\s*(?:" + MARKER + r"\s*)+$")
SENTENCE_END = re.compile(r"[。！？!?]+[\"'”’』」]*")
API_VERSION = "3.0"
sys.path.insert(0, str(ROOT / "mt"))
from mt_memory import Memory, MemoryError_ as MemoryStoreError  # noqa: E402


class MTError(Exception):
    """An actionable MT error; does not contain credentials or request text."""


@dataclass(frozen=True)
class Unit:
    id: str
    chapter: str
    start: int
    end: int
    text: str


def utf16_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def source_units(text: str, max_chars: int = 2000) -> Iterator[Unit]:
    """Chunk at Chinese punctuation when possible, preserving exact source spans.

    Offsets are Python Unicode code-point offsets into the original input, not
    UTF-16 API alignment offsets. Line breaks and Chinese script are not changed.
    The limit is measured in UTF-16 units, including supplementary characters.
    """
    if max_chars < 16 or max_chars > 5000:
        raise ValueError("chunk size must be between 16 and 5000 UTF-16 units")
    headers = list(SECTION.finditer(text))
    spans = []
    if not headers or text[:headers[0].start()].strip():
        spans.append(("", 0, headers[0].start() if headers else len(text)))
    for i, header in enumerate(headers):
        finish = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        spans.append((header.group("chapter"), header.end(), finish))
    # Never leave a marker line inside chapter text, even at the very end of the
    # file where there is no following header to absorb it.
    trimmed = []
    for name, begin, finish in spans:
        segment = text[begin:finish]
        while True:
            tail = MARKER_ONLY.search(segment)
            if not tail:
                break
            segment = segment[:tail.start()]
        trimmed.append((name, begin, begin + len(segment)))
    spans = trimmed
    for chapter, begin, finish in spans:
        cursor = begin
        while cursor < finish:
            end = cursor
            count = 0
            while end < finish:
                size = 2 if ord(text[end]) > 0xFFFF else 1
                if count + size > max_chars:
                    break
                count += size
                end += 1
            if end < finish:
                boundaries = list(SENTENCE_END.finditer(text, cursor, end))
                if boundaries:
                    end = boundaries[-1].end()
            value = text[cursor:end]
            if value.strip():
                digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
                yield Unit(f"{cursor}-{end}-{digest}", chapter, cursor, end, value)
            cursor = end


def endpoint_url(endpoint: str) -> str:
    endpoint = endpoint.rstrip("/")
    parts = urllib.parse.urlsplit(endpoint)
    if (parts.scheme != "https" or not parts.hostname or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment):
        raise MTError("AZURE_TRANSLATOR_ENDPOINT must be an HTTPS base URL without credentials, query or fragment")
    try:
        parts.port
    except ValueError:
        raise MTError("AZURE_TRANSLATOR_ENDPOINT contains an invalid port") from None
    return endpoint + "/translate"


class Cache:
    def __init__(self, path: Path, *, readonly: bool = False):
        self.db = None
        if readonly and not path.exists():
            return
        if not readonly:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) if readonly else sqlite3.connect(path)
        if not readonly:
            self.db.execute("""CREATE TABLE IF NOT EXISTS translations (
                cache_key TEXT PRIMARY KEY,
                result TEXT NOT NULL
            )""")
            self.db.commit()

    def get(self, key: str) -> dict | None:
        if self.db is None:
            return None
        row = self.db.execute("SELECT result FROM translations WHERE cache_key = ?", (key,)).fetchone()
        if not row:
            return None
        try:
            value = json.loads(row[0])
        except (ValueError, TypeError):
            raise MTError("Invalid translation cache entry; no paid request was made for it") from None
        if (not isinstance(value, dict) or not isinstance(value.get("text"), str) or not value["text"].strip()
                or not isinstance(value.get("source_language"), str)
                or not isinstance(value.get("target_language"), str)
                or value.get("one_to_one_status") != "not_established"):
            raise MTError("Invalid translation cache entry; no paid request was made for it")
        return value

    def put(self, key: str, result: dict) -> None:
        self.db.execute("INSERT OR REPLACE INTO translations VALUES (?, ?)",
                        (key, json.dumps(result, ensure_ascii=False)))
        self.db.commit()

    def close(self):
        if self.db is not None:
            self.db.close()


def cache_key(text: str, source: str, target: str, url: str) -> str:
    identity = {"provider": "azure-nmt", "api": API_VERSION, "endpoint": url,
                "category": "general", "from": source, "to": target,
                "includeAlignment": True, "includeSentenceLength": True, "text": text}
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class AzureMT:
    def __init__(self, client: httpx.Client, cache: Cache, url: str):
        self.client, self.cache, self.url = client, cache, url
        self.requests = 0
        self.cache_hits = 0
        self.memory_hits = 0

    def translate(self, text: str, source: str, target: str, memory=None) -> dict:
        if memory is not None:
            remembered = memory.exact(text, source, target, count_use=True)
            if remembered is not None:
                self.memory_hits += 1
                return {"source_language": source, "target_language": target,
                        "text": remembered.target, "alignment_projection": None,
                        "sentence_lengths": None,
                        "one_to_one_status": "not_established",
                        "origin": "translation_memory", "memory_id": remembered.id}
        key = cache_key(text, source, target, self.url)
        saved = self.cache.get(key)
        if saved is not None:
            if (saved.get("source_language") != source or saved.get("target_language") != target
                    or not isinstance(saved.get("text"), str) or not saved["text"].strip()):
                raise MTError("Cached translation does not match this leg; refusing an automatic paid replacement")
            self.cache_hits += 1
            return {**saved, "origin": "provider_cache"}
        secret = os.environ.get("AZURE_TRANSLATOR_KEY", "").strip()
        if not secret:
            raise MTError("Set AZURE_TRANSLATOR_KEY locally before --run; see MT.md. No request was made")
        headers = {"Ocp-Apim-Subscription-Key": secret,
                   "Content-Type": "application/json; charset=UTF-8"}
        region = os.environ.get("AZURE_TRANSLATOR_REGION", "").strip()
        if region:
            headers["Ocp-Apim-Subscription-Region"] = region
        params = {"api-version": API_VERSION, "from": source, "to": target,
                  "textType": "plain", "category": "general",
                  "includeAlignment": "true", "includeSentenceLength": "true"}
        try:
            # No automatic retries of billable POSTs. Successful legs are cached
            # independently, so rerunning resumes even halfway through a unit.
            self.requests += 1
            response = self.client.post(self.url, params=params, headers=headers, json=[{"Text": text}])
        except httpx.HTTPError:
            raise MTError("MT network request failed; successful earlier legs are cached. Rerun to resume") from None
        if response.status_code != 200:
            raise MTError(f"Azure returned HTTP {response.status_code}; check your local key, region and quota. Earlier legs are cached")
        try:
            payload = response.json()
            if not isinstance(payload, list) or len(payload) != 1:
                raise ValueError
            item = payload[0]
            translations = item["translations"]
            if len(translations) != 1:
                raise ValueError
            translation = translations[0]
            translated = translation["text"]
            if not isinstance(translated, str) or not translated.strip() or translation["to"] != target:
                raise ValueError
            alignment = translation.get("alignment", {}).get("proj") or None
            if alignment is not None and not isinstance(alignment, str):
                raise ValueError
            lengths = translation.get("sentLen")
            if lengths is not None:
                if not isinstance(lengths, dict):
                    raise ValueError
                for field in ("srcSentLen", "transSentLen"):
                    if not isinstance(lengths.get(field), list) or any(type(n) is not int or n < 0 for n in lengths[field]):
                        raise ValueError
        except (ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise MTError("Unexpected Azure response schema; nothing from this response was cached") from None
        result = {"source_language": source, "target_language": target, "text": translated,
                  "alignment_projection": alignment,
                  "sentence_lengths": translation.get("sentLen"),
                  "one_to_one_status": "not_established",
                  "origin": "provider"}
        self.cache.put(key, result)
        return result


def translate_routes(unit: Unit, chinese: str, mt: AzureMT, memory=None,
                     *, suggestion_limit: int = 3) -> dict:
    direct = mt.translate(unit.text, chinese, "my", memory)
    english = mt.translate(unit.text, chinese, "en", memory)
    pivot = mt.translate(english["text"], "en", "my", memory)
    suggestions: dict[str, list] = {}
    phrase_hits: list = []
    glossary_hits: list = []
    if memory is not None:
        if suggestion_limit:
            for leg, text, source, target in (
                ("zh_my", unit.text, chinese, "my"),
                ("zh_en", unit.text, chinese, "en"),
                ("en_my", english["text"], "en", "my"),
            ):
                suggestions[leg] = [
                    {"score": item["score"], "source": item["entry"].source,
                     "target": item["entry"].target, "status": item["entry"].status,
                     "memory_id": item["entry"].id, "uses": item["entry"].uses}
                    for item in memory.suggestions(text, source, target,
                                                   limit=suggestion_limit)
                ]
        phrase_hits = [
            {"source": item["entry"].source, "target": item["entry"].target,
             "memory_id": item["entry"].id, "occurrences": item["occurrences"]}
            for item in memory.phrase_hits(unit.text, chinese, "my", limit=10)
        ]
        glossary_hits = [
            {"source": item["entry"].source, "target": item["entry"].target,
             "memory_id": item["entry"].id, "occurrences": item["occurrences"]}
            for item in memory.phrase_hits(unit.text, chinese, "my", limit=10, kind="term")
        ]
    return {"unit": asdict(unit), "provider": "azure-nmt", "api_version": API_VERSION,
            "schema_version": SCHEMA_VERSION,
            "chinese_language": chinese, "pipeline": "direct-vs-english-pivot",
            "zh_my": direct, "zh_en": english, "en_my": pivot,
            "comparison_candidates": {"direct": "zh_my", "english_pivot": "en_my"},
            "memory": {"suggestions": suggestions, "direct_phrase_hits": phrase_hits,
                       "glossary_hits": glossary_hits,
                       "policy": "only approved exact matches are reused; suggestions, phrases and glossary hits are review-only"},
            "compound_sentence_style_analysis": "not_implemented",
            "phrase_alignment_status": "not_established", "ai_rewrite": None}


def plan(units: list[Unit], chinese: str, cache: Cache, url: str, memory=None) -> dict:
    requests = 0
    tm_reuses = direct_hits = english_hits = pivot_cache_hits = 0
    known_pivot_misses = unknown_pivot_inputs = 0
    for unit in units:
        remembered = memory.exact(unit.text, chinese, "my") if memory else None
        if remembered is not None:
            tm_reuses += 1
        elif cache.get(cache_key(unit.text, chinese, "my", url)) is not None:
            direct_hits += 1
        else:
            requests += 1
        remembered_en = memory.exact(unit.text, chinese, "en") if memory else None
        english_text = None
        if remembered_en is not None:
            tm_reuses += 1
            english_text = remembered_en.target
        else:
            cached_en = cache.get(cache_key(unit.text, chinese, "en", url))
            if cached_en is not None:
                english_hits += 1
                english_text = cached_en["text"]
            else:
                requests += 1
        if english_text is None:
            unknown_pivot_inputs += 1
            requests += 1  # conservative estimate: pivot request after English exists
        else:
            pivot_tm = memory.exact(english_text, "en", "my") if memory else None
            if pivot_tm is not None:
                tm_reuses += 1
            elif cache.get(cache_key(english_text, "en", "my", url)) is not None:
                pivot_cache_hits += 1
            else:
                known_pivot_misses += 1
                requests += 1
    return {"mode": "offline_plan", "schema_version": SCHEMA_VERSION,
            "provider_candidate": "azure-nmt",
            "pipeline": "direct-vs-english-pivot", "units_selected": len(units),
            "source_utf16_units": sum(utf16_length(u.text) for u in units),
            "routes_per_unit": [f"{chinese}->my", f"{chinese}->en", "en->my"],
            "translation_memory_reuses": tm_reuses,
            "direct_burmese_cache_hits": direct_hits,
            "chinese_english_cache_hits": english_hits,
            "known_english_burmese_cache_hits": pivot_cache_hits,
            "known_english_burmese_cache_misses": known_pivot_misses,
            "unknown_english_pivot_inputs": unknown_pivot_inputs,
            "http_requests_upper_bound": requests,
            "english_pivot_input_length": "unknown until Chinese→English is available; no exact price/token estimate claimed",
            "requests_made": 0, "ai_requests": 0,
            "one_to_one_alignment": "not yet established",
            "memory_policy": "approved exact only; machine MT never auto-approved"}


@contextmanager
def store(path: Path, *, readonly: bool = False):
    cache = Cache(path.resolve(), readonly=readonly)
    try:
        yield cache
    finally:
        cache.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="HCrawler UTF-8 text, including its chapter headers")
    source.add_argument("--text", help="One short Chinese sample for a pilot")
    parser.add_argument("--chinese", choices=("zh-Hant", "zh-Hans"), default="zh-Hant")
    parser.add_argument("--chunk-chars", type=int, default=2000, help="UTF-16 units per source chunk, 16..5000")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--max-units", type=int, default=10, help="Pilot limit, default 10; does not skip inside a selected unit")
    selection.add_argument("--all", action="store_true", help="Explicitly select the whole input instead of a pilot")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true", help="Offline plan (the default); no credentials or requests")
    mode.add_argument("--run", action="store_true", help="Explicitly enable billable MT requests")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--memory", type=Path, default=DEFAULT_MEMORY,
                        help="Approved phrase-memory SQLite store")
    parser.add_argument("--suggestions", type=int, default=3,
                        help="Similar-phrase suggestions per candidate leg; 0 disables")
    parser.add_argument("--output", type=Path, help="JSONL with the three MT legs and exact original Chinese spans")
    args = parser.parse_args(argv)
    if args.max_units < 1:
        parser.error("--max-units must be positive")
    if args.suggestions < 0:
        parser.error("--suggestions cannot be negative")
    temporary = None
    try:
        if args.input:
            with args.input.open(encoding="utf-8", newline="") as source_file:
                text = source_file.read()
        else:
            text = args.text
        units = []
        for unit in source_units(text, args.chunk_chars):
            units.append(unit)
            if not args.all and len(units) >= args.max_units:
                break
        if not units:
            raise MTError("Input has no non-empty chapter text")
        url = endpoint_url(os.environ.get("AZURE_TRANSLATOR_ENDPOINT", DEFAULT_ENDPOINT))
        stem = args.input.stem if args.input else "sample"
        destination = (args.output or ROOT / "content" / "mtranslate" / f"{stem}-{args.chinese}-azure-candidates.jsonl").resolve()
        if destination.suffix.lower() != ".jsonl":
            raise MTError("MT output must use .jsonl; source/config files cannot be overwritten")
        if args.cache.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise MTError("MT cache must use .db, .sqlite or .sqlite3")
        if args.memory.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
            raise MTError("Phrase memory must use .db, .sqlite or .sqlite3")
        if args.input and args.cache.resolve() == args.input.resolve():
            raise MTError("Cache must not replace the source input")
        if args.input and destination == args.input.resolve():
            raise MTError("Output must not replace the source input")
        if destination == args.cache.resolve():
            raise MTError("Output and cache must be different files")
        reserved = {destination, args.cache.resolve(), args.memory.resolve()}
        if args.input and args.input.resolve() in reserved:
            raise MTError("Input, output, cache and memory must use different files")
        if args.cache.resolve() == args.memory.resolve():
            raise MTError("Cache and phrase memory must be different files")
        with store(args.cache, readonly=not args.run) as cache, Memory(args.memory, readonly=not args.run) as memory:
            if not args.run:
                report = plan(units, args.chinese, cache, url, memory)
                report["selection"] = "all" if args.all else f"first {args.max_units} unit(s), at most"
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 0
            destination.parent.mkdir(parents=True, exist_ok=True)
            with httpx.Client(timeout=60.0, follow_redirects=False) as client:
                mt = AzureMT(client, cache, url)
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                                 prefix=".mt-", suffix=".tmp", delete=False) as out:
                    temporary = Path(out.name)
                    for index, unit in enumerate(units, 1):
                        out.write(json.dumps(translate_routes(unit, args.chinese, mt, memory,
                                                              suggestion_limit=args.suggestions),
                                 ensure_ascii=False) + "\n")
                        out.flush()
                        print(f"[mt] {index}/{len(units)} {unit.chapter or unit.id}; "
                              f"{mt.requests} request(s), {mt.cache_hits} cache hit(s), "
                              f"{mt.memory_hits} approved-memory reuse(s)", file=sys.stderr, flush=True)
                    os.fsync(out.fileno())
                os.replace(temporary, destination)
                temporary = None
                print(f"[done] {destination}")
                return 0
    except (MTError, MemoryStoreError, OSError, ValueError, sqlite3.Error) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n[paused] successful MT legs are cached; rerun the same command", file=sys.stderr)
        return 130
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
