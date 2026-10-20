# /// script
# requires-python = ">=3.10"
# dependencies = ["ctranslate2>=4", "sentencepiece>=0.1.99"]
# ///
"""Run the four machine-translation routes and write their output to `output/mt`.

    zh-en   Chinese  -> English   offline model (installed by mt/fetch_engine.py)
    en-my   English  -> Burmese   needs an API engine (no downloadable model exists)
    my-en   Burmese  -> English   needs an API engine
    zh-my   Chinese  -> Burmese   needs an API engine

Engines are resolved in this order:

1. `--engine azure` — Azure Translator v3. Only runs when the environment already
   holds `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` (plus
   `AZURE_TRANSLATOR_ENDPOINT` if the resource is not global). The key is read
   from the environment and never written to disk or printed.
2. `--engine offline` — the locally installed Argos/OPUS model for that route.
   `mt/fetch_engine.py --check` lists what exists.
3. `--engine glossary` — dictionary look-up, **not** a translation engine. It maps
   each Chinese word through CC-CEDICT to an English gloss and then through the
   English-Myanmar dictionary, and writes what it could and could not resolve.
   It exists to measure dictionary coverage, not to produce readable Burmese.

Output layout, one directory per route:

    output/mt/<route>/chapters/ch193.en.txt   one file per chapter
    output/mt/<route>/book.en.txt             the whole run, chapter by chapter
    output/mt/<route>/report.json             engine, timing, coverage, errors
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

CHINESE = ROOT / "input" / "chinese-0511241012-from-8011_93.txt"
BURMESE = ROOT / "input" / "ယဲ့နင်1-200.txt"
OUTPUT = ROOT / "output" / "mt"

ROUTES = {
    "zh-en": ("zh", "en"),
    "en-my": ("en", "my"),
    "my-en": ("my", "en"),
    "zh-my": ("zh", "my"),
}

# ---------------------------------------------------------------- chapters


@dataclass
class Chapter:
    number: int
    title: str
    body: str
    source: str


def chinese_chapters(path: Path = CHINESE) -> list[Chapter]:
    lines = path.read_text(encoding="utf-8").split("\n")
    heads = [i for i, line in enumerate(lines) if line.startswith("===== ")]
    chapters: list[Chapter] = []
    for order, index in enumerate(heads):
        end = heads[order + 1] if order + 1 < len(heads) else len(lines)
        title = lines[index].strip("= ").strip()
        match = re.match(r"^第([一二三四五六七八九十百千零〇]+)章", title)
        number = chinese_number(match.group(1)) if match else order + 1
        chapters.append(Chapter(number, title, "\n".join(lines[index + 1:end]).strip(), "chinese"))
    return chapters


@dataclass
class BurmeseChapter(Chapter):
    marker: int = 0


def burmese_chapters(path: Path = BURMESE) -> list[Chapter]:
    lines = path.read_text(encoding="utf-8").split("\n")
    marks = [i for i, line in enumerate(lines) if line.startswith("[[HCRAWLER MARKER")]
    chapters = []
    for order, index in enumerate(marks):
        end = marks[order + 1] if order + 1 < len(marks) else len(lines)
        title = lines[index + 1].strip() if index + 1 < len(lines) else ""
        chapters.append(BurmeseChapter(order + 1, title, "\n".join(lines[index + 2:end]).strip(),
                                       "burmese", marker=order + 1))
    return chapters


_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def chinese_number(text: str) -> int:
    total = 0
    digit = 0
    for char in text:
        if char in _DIGITS:
            digit = _DIGITS[char]
        elif char == "十":
            total += (digit or 1) * 10
            digit = 0
        elif char == "百":
            total += (digit or 1) * 100
            digit = 0
        elif char == "千":
            total += (digit or 1) * 1000
            digit = 0
    return total + digit


# ---------------------------------------------------------------- sentences

_SENT = re.compile(r"[^。！？!?…\n]+[。！？!?…]*")


def sentences(text: str) -> list[str]:
    out: list[str] = []
    for match in _SENT.finditer(text):
        piece = match.group(0).strip()
        if piece:
            out.append(piece)
    return out


# ---------------------------------------------------------------- engines


def detokenize(pieces: list[str]) -> str:
    """Join sentencepiece pieces without dropping unknown ones.

    `SentencePieceProcessor.decode` leaves the `▁` word marker in place for
    tokens it cannot map back, so the pieces are joined directly.
    """
    text = "".join(pieces).replace("\u2581", " ")
    return re.sub(r"\s+", " ", text).strip()


class Engine:
    name = "engine"
    detail = ""

    def translate(self, texts: list[str], source: str, target: str) -> list[str]:
        raise NotImplementedError

    def available(self) -> tuple[bool, str]:
        raise NotImplementedError


class OfflineEngine(Engine):
    """Argos/OPUS-MT checkpoint read directly with ctranslate2 + sentencepiece.

    Argos' own `translate` wrapper pulls in stanza for sentence splitting and
    tries to download its resources from raw.githubusercontent.com, which this
    machine cannot reach. The model itself needs neither: the sentences are
    split here and fed to the checkpoint.
    """

    name = "offline"

    def __init__(self, source: str, target: str) -> None:
        self.pair = f"{source}-{target}"
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        self.path = base / "argos-translate" / "packages" / f"translate-{source}_{target}-1_0"
        self.detail = str(self.path)
        self._translator = None
        self._sp = None

    def available(self) -> tuple[bool, str]:
        if not (self.path / "model" / "model.bin").is_file():
            return False, f"no offline model installed for {self.pair} (mt/fetch_engine.py --install {self.pair})"
        return True, str(self.path)

    def _load(self):
        if self._translator is None:
            import ctranslate2  # noqa: PLC0415
            import sentencepiece as spm  # noqa: PLC0415
            self._translator = ctranslate2.Translator(str(self.path / "model"), device="cpu", compute_type="int8")
            self._sp = spm.SentencePieceProcessor(model_file=str(self.path / "sentencepiece.model"))
        return self._translator, self._sp

    def translate(self, texts: list[str], source: str, target: str) -> list[str]:
        import sentencepiece as spm  # noqa: F401, PLC0415
        translator, sp = self._load()
        results: list[str] = []
        batch_size = 24
        for start in range(0, len(texts), batch_size):
            chunk = texts[start:start + batch_size]
            tokens = [sp.encode(text, out_type=str) for text in chunk]
            outputs = translator.translate_batch(tokens, beam_size=2, max_batch_size=batch_size)
            results.extend(detokenize(item.hypotheses[0]) for item in outputs)
        return results


class AzureEngine(Engine):
    """Azure Translator v3. Guidance only: the key comes from the environment."""

    name = "azure"
    ENDPOINT = "https://api.cognitive.microsofttranslator.com"

    def __init__(self) -> None:
        self.key = os.environ.get("AZURE_TRANSLATOR_KEY", "")
        self.region = os.environ.get("AZURE_TRANSLATOR_REGION", "")
        self.endpoint = os.environ.get("AZURE_TRANSLATOR_ENDPOINT", self.ENDPOINT).rstrip("/")
        self.detail = f"{self.endpoint} (key {'set' if self.key else 'missing'})"

    def available(self) -> tuple[bool, str]:
        if not self.key:
            return False, "AZURE_TRANSLATOR_KEY is not set; export it in your shell (never commit it)"
        if not self.region:
            return False, "AZURE_TRANSLATOR_REGION is not set"
        return True, self.detail

    def translate(self, texts: list[str], source: str, target: str) -> list[str]:
        import requests  # noqa: PLC0415
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json",
        }
        params = {"api-version": "3.0", "from": source, "to": target}
        results: list[str] = []
        for start in range(0, len(texts), 25):
            chunk = texts[start:start + 25]
            response = requests.post(self.endpoint + "/translate", params=params, headers=headers,
                                     json=[{"text": item} for item in chunk], timeout=60)
            response.raise_for_status()
            results.extend(item["translations"][0]["text"] for item in response.json())
        return results


class GlossaryEngine(Engine):
    """Dictionary look-up, not a translation engine."""

    name = "glossary"
    detail = "format/dicts.py (CC-CEDICT + English-Myanmar)"

    def __init__(self) -> None:
        sys.path.insert(0, str(ROOT / "format"))
        self.ready = False
        try:
            from dicts import Cedict, EnMy  # noqa: PLC0415
            self.cedict = Cedict()
            self.enmy = EnMy()
            self.ready = True
        except Exception as error:  # pragma: no cover - depends on install
            self.error = str(error)

    def available(self) -> tuple[bool, str]:
        return (True, self.detail) if self.ready else (False, getattr(self, "error", "dictionaries missing"))

    @staticmethod
    def _burmese(defn: str, limit: int = 3) -> list[str]:
        out: list[str] = []
        for part in re.split(r"[။၊]", defn):
            for run in re.findall(r"[\u1000-\u109f][\u1000-\u109f\s]*", part):
                if re.search(r"[A-Za-z]", run):
                    continue
                for token in run.split():
                    if 2 <= len(token) <= 24 and token not in out:
                        out.append(token)
        return out[:limit]

    def translate(self, texts: list[str], source: str, target: str) -> list[str]:
        from dicts import gloss_keys  # noqa: PLC0415
        results = []
        for text in texts:
            words = self.cedict.terms(text, min_length=2) if source == "zh" else {text: []}
            pieces = []
            for word, entries in words.items():
                burmese: list[str] = []
                for entry in entries[:2]:
                    for key in gloss_keys(entry)[:3]:
                        rows = self.enmy.lookup(key)
                        if rows:
                            burmese.extend(self._burmese(rows[0]["definition"], 2))
                            if burmese:
                                break
                    if burmese:
                        break
                pieces.append(f"{word}→{'/'.join(dict.fromkeys(burmese)) if burmese else '∅'}")
            results.append(" ".join(pieces) if pieces else "∅")
        return results


def resolve(engine: str, source: str, target: str) -> Engine:
    if engine == "azure":
        return AzureEngine()
    if engine == "glossary":
        return GlossaryEngine()
    return OfflineEngine(source, target)


# ---------------------------------------------------------------- running


@dataclass
class Report:
    route: str
    engine: str
    chapters: int = 0
    sentences: int = 0
    empty: int = 0
    skipped: int = 0
    tokens: int = 0
    unresolved: int = 0
    started: float = 0.0
    seconds: float = 0.0
    status: str = "ok"
    detail: str = ""
    files: list[str] = field(default_factory=list)


def run_route(route: str, engine_name: str, limit: int | None, out_dir: Path,
              chapters: list[Chapter], resume: bool = False) -> Report:
    source, target = ROUTES[route]
    engine = resolve(engine_name, source, target)
    ok, detail = engine.available()
    report = Report(route=route, engine=engine.name, detail=detail)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not ok:
        report.status = "unavailable"
        (out_dir / "report.json").write_text(json.dumps(report.__dict__, indent=2) + "\n", encoding="utf-8")
        print(f"[mt] {route}: unavailable — {detail}")
        return report

    chosen = chapters[:limit] if limit else chapters
    book: list[str] = []
    report.started = time.time()
    for chapter in chosen:
        name = f"ch{chapter.number:04d}.{target}.txt"
        existing = out_dir / "chapters" / name
        if resume and existing.is_file() and existing.stat().st_size > 0:
            report.chapters += 1
            report.skipped += 1
            book.append("\n\n===== " + chapter.title + " =====\n" + existing.read_text(encoding="utf-8").split("\n", 2)[-1])
            continue
        lines = sentences(chapter.body)
        translated = engine.translate(lines, source, target)
        report.chapters += 1
        report.sentences += len(lines)
        report.empty += sum(1 for item in translated if not item.strip())
        if engine.name == "glossary":
            report.tokens += sum(len(item.split()) for item in translated)
            report.unresolved += sum(item.count("∅") for item in translated)
        title = chapter.title if not hasattr(chapter, "marker") else f"[HCRAWLER MARKER {chapter.marker}] {chapter.title}"
        body = "\n".join(translated)
        text = f"{title}\n{'=' * len(title)}\n{body}\n"
        (out_dir / "chapters").mkdir(parents=True, exist_ok=True)
        (out_dir / "chapters" / name).write_text(text, encoding="utf-8")
        try:
            report.files.append(str((out_dir / "chapters" / name).relative_to(ROOT)))
        except ValueError:
            report.files.append(str(out_dir / "chapters" / name))
        book.append(f"\n\n===== {title} =====\n")
        book.append(body)
    report.seconds = round(time.time() - report.started, 1)
    (out_dir / f"book.{target}.txt").write_text("".join(book).lstrip() + "\n", encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps(report.__dict__, indent=2, ensure_ascii=False) + "\n",
                                         encoding="utf-8")
    print(f"[mt] {route}: {report.chapters} chapters, {report.sentences} sentences, "
          f"{report.seconds}s -> {out_dir}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--route", action="append", choices=sorted(ROUTES), default=[],
                        help="route to run; repeatable, default: all four")
    parser.add_argument("--engine", choices=["offline", "azure", "glossary"], default="offline")
    parser.add_argument("--source-file", type=Path, default=None,
                        help="Chinese text; default input/chinese-0511241012-from-8011_93.txt")
    parser.add_argument("--limit", type=int, default=None, help="only the first N chapters")
    parser.add_argument("--only", action="append", default=[], help="chapter number to include")
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--list", action="store_true", help="show route availability and exit")
    parser.add_argument("--resume", action="store_true", help="skip chapters that already have output")
    args = parser.parse_args(argv)

    if args.list:
        print(f"{'route':<8}{'engine':<10}{'available':<11}detail")
        for route in ROUTES:
            source, target = ROUTES[route]
            ok, detail = resolve("offline", source, target).available()
            print(f"{route:<8}{'offline':<10}{str(ok):<11}{detail}")
        for route in ROUTES:
            ok, detail = AzureEngine().available()
            print(f"{route:<8}{'azure':<10}{str(ok):<11}{detail}")
        ok, detail = GlossaryEngine().available()
        print(f"{'all':<8}{'glossary':<10}{str(ok):<11}{detail} (dictionary look-up, not MT)")
        return 0

    chapters = chinese_chapters(args.source_file or CHINESE)
    if args.only:
        wanted = set()
        for item in args.only:
            for piece in str(item).replace(" ", "").split(","):
                if piece:
                    wanted.add(int(piece))
        chapters = [chapter for chapter in chapters if chapter.number in wanted]
    if not chapters:
        print("[mt] no chapters selected", file=sys.stderr)
        return 2

    routes = args.route or sorted(ROUTES)
    reports = []
    for route in routes:
        out_dir = args.out_dir / route
        reports.append(run_route(route, args.engine, args.limit, out_dir, chapters, args.resume))

    summary = {
        "engine": args.engine,
        "routes": {report.route: {"status": report.status, "detail": report.detail,
                                  "chapters": report.chapters, "sentences": report.sentences,
                                  "seconds": report.seconds} for report in reports},
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
