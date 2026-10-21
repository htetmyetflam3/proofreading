# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Plan, run and compare the pivot routes that need an API engine.

The chapter files in this repository contain two parallel texts of the same novel:

    Chinese   content/source/chinese-0511241012-from-8011_1.txt   377 sections, chapters 1 .. 408
    Burmese   content/source/ယဲ့နင်.txt                            197 markers, chapters 1 .. 195

They overlap in exactly one chapter -- Chinese 193 is Burmese marker 197 (title
`အခန်း ၁၉၅`, opening `ဤလူများသည် မဟာကျိုးပြည်ထောင်၏` for
`這些人口，可都是大周的底子`, closing `ခဗျားတို့ ဘာလိုပ်နေကတာလဲ` for `你們在幹什麼？`).
That single overlapping chapter is the only honest way to test a pivot without a
human reference: translate it from the Chinese side and from the Burmese side and
compare the two English results.

Routes:

    zh-en    Chinese  -> English   offline model, already runs
    my-en    Burmese  -> English   API only
    en-my    English  -> Burmese   API only
    zh-my    Chinese  -> Burmese   API only (direct) or via zh-en then en-my (pivot)

    python3 mt/pivot.py --plan                  # sizes, before spending anything
    python3 mt/pivot.py --run --legs my-en      # needs AZURE_TRANSLATOR_KEY/REGION
    python3 mt/pivot.py --compare               # zh-en vs my-en on the shared chapter
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from translate import (  # noqa: E402
    AzureEngine, GlossaryEngine, OfflineEngine, burmese_chapters, chinese_chapters,
    sentences,
)

OUTPUT = ROOT / "content" / "mtranslate"
SHARED = {"chinese": 193, "burmese_marker": 197}


def size_of(text: str) -> int:
    return len(text)


def plan() -> dict:
    chinese = chinese_chapters()
    burmese = burmese_chapters()
    cn_chars = sum(len(chapter.body) for chapter in chinese)
    my_chars = sum(len(chapter.body) for chapter in burmese)
    zn_sent = sum(len(sentences(chapter.body)) for chapter in chinese)
    my_sent = sum(len(sentences(chapter.body)) for chapter in burmese)
    return {
        "zh-en": {"status": "installed", "chapters": len(chinese), "sentences": zn_sent,
                  "characters": cn_chars, "cost": "free (local)"},
        "my-en": {"status": "needs_api", "chapters": len(burmese), "sentences": my_sent,
                  "characters": my_chars, "cost": "Azure pricing per character"},
        "en-my": {"status": "needs_api", "chapters": len(chinese), "sentences": "input = zh-en output",
                  "characters": "input = English characters of zh-en", "cost": "Azure pricing per character"},
        "zh-my": {"status": "needs_api", "chapters": len(chinese), "sentences": zn_sent,
                  "characters": cn_chars, "cost": "two calls per sentence if pivoted"},
        "overlap": SHARED,
    }


def load_zh_en() -> dict[int, str]:
    """English chapter text produced by `mt/translate.py --route zh-en`."""
    book = OUTPUT / "zh-en" / "book.en.txt"
    if not book.is_file():
        return {}
    text = book.read_text(encoding="utf-8")
    chunks = re.split(r"===== (.+?) =====", text)
    english: dict[int, str] = {}
    for index in range(1, len(chunks), 2):
        title, body = chunks[index], chunks[index + 1]
        match = re.search(r"第([一二三四五六七八九十百千零〇]+)章", title)
        if not match:
            continue
        from translate import chinese_number  # noqa: PLC0415
        english[chinese_number(match.group(1))] = body.strip()
    return english


def run_leg(leg: str, engine_name: str, limit: int | None) -> dict:
    if engine_name == "azure":
        engine = AzureEngine()
    elif engine_name == "offline":
        engine = OfflineEngine("en", "my")
    else:
        engine = GlossaryEngine()
    ok, detail = engine.available()
    if not ok:
        raise SystemExit(f"{leg}: {detail}")

    if leg == "my-en":
        source, target = "my", "en"
        chapters = burmese_chapters()
        payload = [(chapter.marker, title_of(chapter), chapter.body) for chapter in chapters]
        out_dir = OUTPUT / "my-en"
    else:
        raise SystemExit(f"leg {leg} is not wired to this runner; "
                         "use mt/translate.py for zh-en and zh-my")

    out_dir.mkdir(parents=True, exist_ok=True)
    chosen = payload[:limit] if limit else payload
    book_lines = []
    counts = {"chapters": 0, "sentences": 0}
    for key, title, body in chosen:
        lines = [line for line in sentences(body) if line.strip()]
        english = engine.translate(lines, source, target)
        counts["chapters"] += 1
        counts["sentences"] += len(lines)
        (out_dir / "chapters").mkdir(parents=True, exist_ok=True)
        suffix = "en" if target == "en" else target
        (out_dir / "chapters" / f"m{key:04d}.{suffix}.txt").write_text(
            title + "\n" + "\n".join(english) + "\n", encoding="utf-8")
        book_lines.append(f"\n\n===== {title} =====\n" + "\n".join(english))
    (out_dir / "book.en.txt").write_text("".join(book_lines).lstrip() + "\n", encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps({**counts, "engine": engine.name}, indent=2) + "\n",
                                         encoding="utf-8")
    return {**counts, "engine": engine.name, "output": str(out_dir)}


def title_of(chapter) -> str:
    return f"[HCRAWLER MARKER {chapter.marker}] {chapter.title}"


def compare(limit: int = 8) -> int:
    """Print both English renderings of the one chapter the two files share."""
    english = load_zh_en()
    if not english:
        print("run `python3 mt/translate.py --route zh-en` first")
        return 2
    chinese_english = english.get(SHARED["chinese"], "")
    burmese_dir = OUTPUT / "my-en" / "chapters"
    burmese_file = burmese_dir / f"m{SHARED['burmese_marker']:04d}.en.txt"
    if not burmese_file.is_file():
        print(f"no my-en output yet: {burmese_file}")
        print("run `python3 mt/pivot.py --run --legs my-en --engine azure` with "
              "AZURE_TRANSLATOR_KEY and AZURE_TRANSLATOR_REGION exported")
        print("\nzh-en side, first sentences:")
        for line in chinese_english.splitlines()[:limit]:
            print("  " + line)
        return 0

    burmese_english = burmese_file.read_text(encoding="utf-8")
    a = [line for line in chinese_english.splitlines() if line.strip()][:limit]
    b = [line for line in burmese_english.splitlines() if line.strip()][:limit]
    width = max(len(line) for line in a + b) if a + b else 0
    print(f"{'from Chinese':<{width}}  |  from Burmese")
    print("-" * (width * 2 + 6))
    for left, right in zip(a, b):
        print(f"{left:<{width}}  |  {right}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", action="store_true", help="report sizes and engine needs")
    parser.add_argument("--run", action="store_true", help="run the API legs")
    parser.add_argument("--legs", action="append", default=[], help="my-en (supported)")
    parser.add_argument("--engine", choices=["azure", "offline", "glossary"], default="azure")
    parser.add_argument("--limit", type=int, default=None, help="only the first N chapters")
    parser.add_argument("--compare", action="store_true",
                        help="compare zh-en and my-en on the shared chapter")
    args = parser.parse_args(argv)

    if args.plan:
        print(json.dumps(plan(), indent=2, ensure_ascii=False))
        return 0
    if args.compare:
        return compare()
    if args.run:
        legs = args.legs or ["my-en"]
        results = {}
        for leg in legs:
            print(f"[pivot] {leg} via {args.engine}")
            results[leg] = run_leg(leg, args.engine, args.limit)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
