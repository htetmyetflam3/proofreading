# /// script
# requires-python = ">=3.10"
# dependencies = ["ctranslate2>=4", "sentencepiece>=0.1.99"]
# ///
"""Run the Chinese/English translation routes and write them to `content/mtranslate`.

    zh-en   Chinese -> English   offline model (installed by mt/fetch_engine.py)
    en-zh   English -> Chinese   offline model

That is the whole set. There is no machine translation to or from Burmese: the
Burmese text the proofreading agent works on comes from the translator API, and
these two routes exist so a local agent can read the Chinese source in English
and cross-check meaning against it. Chinese -> Burmese was dropped deliberately —
see `MT.md`.

Engines are resolved in this order:

1. `--engine offline` — the locally installed Argos/OPUS model for that route.
   `mt/fetch_engine.py --check` lists what exists.
2. `--engine azure` — Azure Translator v3. Only runs when the environment already
   holds `AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` (plus
   `AZURE_TRANSLATOR_ENDPOINT` if the resource is not global). The key is read
   from the environment and never written to disk or printed.
3. `--engine cmd` — any translator installed as a command; see `--cmd-template`.

Output layout, one directory per route:

    content/mtranslate/<route>/chapters/ch0001.en.txt   one file per chapter
    content/mtranslate/<route>/book.en.txt               the whole run, chapter by chapter
    content/mtranslate/<route>/report.json               engine, timing, coverage, errors
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

CHINESE = ROOT / "content" / "source" / "chinese-0511241012-from-8011_1.txt"
BURMESE = ROOT / "content" / "source" / "ယဲ့နင်.txt"
OUTPUT = ROOT / "content" / "mtranslate"

ROUTES = {
    "zh-en": ("zh", "en"),
    "en-zh": ("en", "zh"),
}

# ---------------------------------------------------------------- chapters


@dataclass
class Chapter:
    number: int
    title: str
    body: str
    source: str


# Crawler OCR damage: katakana ー for 一, ハ for 八, 意 for 章 (第六四意),
# plus inline titles glued inside an unsplit section.
_CN_NUMERALS = "一二三四五六七八九十百千零〇ーハ"
_CN_TITLE = re.compile(r"第([" + _CN_NUMERALS + r"]+)[章意]")
_CN_GARBLED = str.maketrans({"ー": "一", "ハ": "八"})
_CN_DIGIT = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_label(numerals: str) -> int:
    numerals = numerals.translate(_CN_GARBLED)
    if not any(unit in numerals for unit in "十百千"):
        total = 0
        for char in numerals:
            total = total * 10 + _CN_DIGIT[char]
        return total
    return chinese_number(numerals)


def _chinese_boundaries(lines: list[str]) -> list[tuple[int, int, int, int, str]]:
    bounds: list[tuple[int, int, int, int, str]] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("===== "):
            title = stripped.strip("= ").strip()
            match = _CN_TITLE.match(title)
            bare = re.fullmatch(r"\d+", title)
            if match:
                bounds.append((index, 0, len(line), _cn_label(match.group(1)), title))
            elif bare:
                bounds.append((index, 0, len(line), int(bare.group()), title))
        elif not stripped.startswith("[[KMTCRAWLER"):
            for match in _CN_TITLE.finditer(line):
                bounds.append((index, match.start(), match.end(),
                               _cn_label(match.group(1)), match.group(0).strip()))
    return bounds


def chinese_chapters(path: Path = CHINESE) -> list[Chapter]:
    lines = path.read_text(encoding="utf-8").split("\n")
    bounds = _chinese_boundaries(lines)
    chapters: list[Chapter] = []
    for order, (index, start_cut, end_cut, number, title) in enumerate(bounds, 1):
        if order < len(bounds):
            end_line, end_start = bounds[order][0], bounds[order][1]
        else:
            end_line, end_start = len(lines), 0
        if start_cut or end_cut:
            segment = [lines[index][end_cut:]] + lines[index + 1:end_line]
        else:
            segment = lines[index + 1:end_line]
        if end_start and segment:
            segment[-1] = segment[-1][:end_start]
        chapters.append(Chapter(number, title, "\n".join(segment).strip(), "chinese"))
    return chapters


@dataclass
class BurmeseChapter(Chapter):
    marker: int = 0


def english_chapters(route_dir: Path) -> list[Chapter]:
    """Chapters of an earlier zh-en run, used as the source for en-zh."""
    chapters: list[Chapter] = []
    for path in sorted((route_dir / "chapters").glob("ch*.en.txt")):
        match = re.match(r"ch(\d+)\.en\.txt$", path.name)
        if not match:
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        title = lines[0].strip() if lines else ""
        body = "\n".join(lines[2:]).strip()
        chapters.append(Chapter(int(match.group(1)), title, body, "english"))
    return chapters


# Native PDF headings ("Chapter 1:", "အခန်း (၅)", "အပိုင်း ၅၁", split parts,
# Arabic-digit and OCR ရ-for-၇ variants); used when the text has no crawler markers.
_BURMESE_HEADING = re.compile(
    r"^Chapter\s*[\-\u2013:]?\s*(?P<cn>\d+)\b"
    r"|^(?:အခန်း|အပိုင်း)\s*[\-\u2013（(]?\s*"
    r"(?P<bn>[၀-၉0-9ရ]+)\s*[）)]?(?:\s*(?P<part>[၁၂]))?\s*$"
)


def _burmese_native_heads(lines: list[str]) -> list[tuple[int, int | None, str]]:
    heads: list[tuple[int, int | None, str]] = []
    for index, line in enumerate(lines):
        match = _BURMESE_HEADING.match(line.strip())
        if not match:
            continue
        if match.group("cn"):
            label: int | None = int(match.group("cn"))
        else:
            digit_map = {chr(0x1040 + i): str(i) for i in range(10)}
            digits = "".join(digit_map.get(char, char) for char in match.group("bn"))
            found = re.search(r"\d+", digits)
            label = int(found.group()) if found else None
        heads.append((index, label, line.strip()))
    for order, (index, label, title) in enumerate(heads):
        if label is None:
            previous = heads[order - 1][1] if order else None
            upcoming = next((item[1] for item in heads[order + 1:] if item[1] is not None), None)
            if previous is not None and upcoming == previous + 2:
                heads[order] = (index, previous + 1, title)
    return heads


def burmese_chapters(path: Path = BURMESE) -> list[Chapter]:
    lines = path.read_text(encoding="utf-8").split("\n")
    marks = [i for i, line in enumerate(lines) if line.startswith("[[HCRAWLER MARKER")]
    if marks:
        chapters = []
        for order, index in enumerate(marks):
            end = marks[order + 1] if order + 1 < len(marks) else len(lines)
            title = lines[index + 1].strip() if index + 1 < len(lines) else ""
            chapters.append(BurmeseChapter(order + 1, title, "\n".join(lines[index + 2:end]).strip(),
                                           "burmese", marker=order + 1))
        return chapters
    heads = _burmese_native_heads(lines)
    chapters: list[BurmeseChapter] = []
    for order, (index, label, title) in enumerate(heads):
        end = heads[order + 1][0] if order + 1 < len(heads) else len(lines)
        body = "\n".join(lines[index + 1:end]).strip()
        if chapters and chapters[-1].number == label:
            previous = chapters[-1]
            chapters[-1] = BurmeseChapter(previous.number, previous.title,
                                          previous.body + "\n\n" + body, "burmese",
                                          marker=previous.marker)
        else:
            chapters.append(BurmeseChapter(label, title, body, "burmese", marker=len(chapters) + 1))
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


class CommandEngine(Engine):
    """Any installed translator, driven by a shell command template.

    The official Argos index has no Burmese package, so a zh->my or en->my
    engine has to be installed separately. Rather than hard-code whichever one
    was installed last, this engine runs a command you supply and records it in
    the report. The template gets the text on stdin and must answer on stdout:

        --cmd-template "nllb-translate --from zho_Hans --to mya_MM"

    `{text}` may be used instead of stdin; it is replaced with the text and the
    process is run without a pipe. `{source}` and `{target}` are substituted
    with the route's language codes.
    """

    name = "cmd"
    TIMEOUT = 120

    def __init__(self, source: str, target: str, template: str | None = None) -> None:
        self.source = source
        self.target = target
        self.template = template or os.environ.get("MT_ENGINE_COMMAND", "")
        self.detail = self.template or "MT_ENGINE_COMMAND is not set"

    def available(self) -> tuple[bool, str]:
        if not self.template.strip():
            return False, ("no command template: pass --cmd-template or export "
                           "MT_ENGINE_COMMAND (see mt/MT-RESTORE.md)")
        return True, self.template

    def _render(self, text: str) -> str:
        return (self.template
                .replace("{source}", self.source)
                .replace("{target}", self.target)
                .replace("{text}", shlex.quote(text)))

    def translate(self, texts: list[str], source: str, target: str) -> list[str]:
        results: list[str] = []
        for text in texts:
            command = self._render(text)
            if "{text}" in self.template:
                completed = subprocess.run(command, shell=True, capture_output=True,
                                           text=True, timeout=self.TIMEOUT)
            else:
                completed = subprocess.run(command, shell=True, input=text,
                                           capture_output=True, text=True,
                                           timeout=self.TIMEOUT)
            if completed.returncode != 0:
                raise RuntimeError(f"{command} exited {completed.returncode}: "
                                   f"{completed.stderr.strip()[:200]}")
            results.append(completed.stdout.strip())
        return results


def resolve(engine: str, source: str, target: str,
            cmd_template: str | None = None) -> Engine:
    if engine == "azure":
        return AzureEngine()
    if engine == "cmd":
        return CommandEngine(source, target, cmd_template)
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
              chapters: list[Chapter], resume: bool = False,
              cmd_template: str | None = None,
              engine_note: str | None = None) -> Report:
    source, target = ROUTES[route]
    engine = resolve(engine_name, source, target, cmd_template)
    ok, detail = engine.available()
    if engine_name == "cmd" and engine_note:
        detail = f"{detail}  [# {engine_note}]"
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
    parser.add_argument("--engine", choices=["offline", "azure", "cmd"], default="offline")
    parser.add_argument("--cmd-template", default=None,
                        help="shell command for --engine cmd; {text} or stdin")
    parser.add_argument("--engine-note", default=None,
                        help="model id/version recorded in report.json, e.g. "
                             "'nllb-200-distilled-600M-int8'")
    parser.add_argument("--source-file", type=Path, default=None,
                        help="Chinese text; default content/source/chinese-0511241012-from-8011_1.txt")
    parser.add_argument("--limit", type=int, default=None, help="only the first N chapters")
    parser.add_argument("--only", action="append", default=[], help="chapter number to include")
    parser.add_argument("--out-dir", type=Path, default=OUTPUT)
    parser.add_argument("--list", action="store_true", help="show route availability and exit")
    parser.add_argument("--resume", action="store_true", help="skip chapters that already have output")
    parser.add_argument("--cascade", action="store_true",
                        help="run zh-en, then en-zh (which reads zh-en), then zh-my")
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
        return 0

    chapters = chinese_chapters(args.source_file or CHINESE)
    wanted_filters: list[set[int]] = []
    filters = wanted_filters
    feeds = {"en-zh": lambda: english_chapters(args.out_dir / "zh-en")}
    if args.only:
        wanted = set()
        for item in args.only:
            for piece in str(item).replace(" ", "").split(","):
                if piece:
                    wanted.add(int(piece))
        filters.append(wanted)
    if not chapters:
        print("[mt] no chapters selected", file=sys.stderr)
        return 2

    if args.cascade:
        routes = ["zh-en", "en-zh", "zh-my"]
    else:
        routes = args.route or sorted(ROUTES)
    # zh-my has no translation model; --cascade uses the documented dictionary walk
    # for that leg unless an API engine was asked for explicitly.
    reports = []
    for route in routes:
        out_dir = args.out_dir / route
        route_chapters = feeds[route]() if route in feeds else chapters
        if wanted_filters:
            route_chapters = [c for c in route_chapters if c.number in wanted_filters[0]]
        if route in feeds and not route_chapters:
            print(f"[mt] {route}: no input yet — run --route zh-en first")
            reports.append(Report(route=route, engine=args.engine, status="no_input",
                                  detail="run --route zh-en first"))
            continue
        reports.append(run_route(route, args.engine, args.limit, out_dir,
                                 route_chapters, args.resume, args.cmd_template,
                                 args.engine_note))

    summary = {
        "engine": args.engine,
        "routes": {report.route: {"status": report.status, "detail": report.detail,
                                  "chapters": report.chapters, "sentences": report.sentences,
                                  "seconds": report.seconds} for report in reports},
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                                encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
