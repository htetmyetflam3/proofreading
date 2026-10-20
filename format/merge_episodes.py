# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Merge the Chinese original and the Burmese version episode by episode.

Output shape:

    [episode 1]

    Chinese original
    ----------------
    這些人口，可都是大周的底子。

    Burmese version
    ---------------
    ဤလူများသည် မဟာကျိုးပြည်ထောင်၏ အေခြခံဖြစ်သည်။

Pairing modes (`--pair`):

    order  (default) pair in file order: episode N is Chinese chapter N of the
           Chinese file and Burmese chapter N of the Burmese file.
    map    pair with an explicit JSON list: [{"chinese": 193, "burmese": 197}].
           Use this when the two files are known to line up.

What the two supplied files actually contain, measured:

    Chinese  input/chinese-0511241012-from-8011_93.txt   210 chapters, 193 .. 408
    Burmese  input/ယဲ့နင်1-200.txt                          197 markers, titles 1 .. 195

They are not the same run of chapters. One pair is confirmed by identical
content: Chinese 193 (`這些人口，可都是大周的底子`) is Burmese marker 197
(`ဤလူများသည် မဟာကျိုးပြည်ထောင်၏ အေခြခံဖြစ်သည်`). No automatic matcher is offered
here because the two files barely overlap -- pairing is either positional
(`order`) or explicit (`map`), and the report always states which was used.

    uv run format/merge_episodes.py                      # order, all episodes
    uv run format/merge_episodes.py --pair map --map pairs.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHINESE = ROOT / "input" / "chinese-0511241012-from-8011_93.txt"
BURMESE = ROOT / "input" / "ယဲ့နင်1-200.txt"
OUTPUT = ROOT / "output" / "merged"

_DIGITS = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_BURMESE_DIGITS = {chr(0x1040 + index): str(index) for index in range(10)}


def chinese_number(text: str) -> int:
    total = digit = 0
    for char in text:
        if char in _DIGITS:
            digit = _DIGITS[char]
        elif char == "十":
            total, digit = total + (digit or 1) * 10, 0
        elif char == "百":
            total, digit = total + (digit or 1) * 100, 0
        elif char == "千":
            total, digit = total + (digit or 1) * 1000, 0
    return total + digit


def burmese_number(text: str) -> int | None:
    digits = "".join(_BURMESE_DIGITS.get(char, char) for char in text)
    match = re.search(r"\d+", digits)
    return int(match.group(0)) if match else None


@dataclass
class Episode:
    order: int
    label: int | None
    title: str
    body: str


def chinese_episodes(path: Path = CHINESE) -> list[Episode]:
    lines = path.read_text(encoding="utf-8").split("\n")
    heads = [index for index, line in enumerate(lines) if line.startswith("===== ")]
    episodes = []
    for order, index in enumerate(heads, 1):
        end = heads[order] if order < len(heads) else len(lines)
        title = lines[index].strip("= ").strip()
        match = re.match(r"^第([一二三四五六七八九十百千零〇]+)章", title)
        episodes.append(Episode(order, chinese_number(match.group(1)) if match else None,
                                title, "\n".join(lines[index + 1:end]).strip()))
    return episodes


def burmese_episodes(path: Path = BURMESE) -> list[Episode]:
    lines = path.read_text(encoding="utf-8").split("\n")
    marks = [index for index, line in enumerate(lines) if line.startswith("[[HCRAWLER MARKER")]
    episodes = []
    for order, index in enumerate(marks, 1):
        end = marks[order] if order < len(marks) else len(lines)
        title = lines[index + 1].strip() if index + 1 < len(lines) else ""
        episodes.append(Episode(order, burmese_number(title), title,
                                "\n".join(lines[index + 2:end]).strip()))
    return episodes


def render(pairs: list[tuple[int | None, int | None]], chinese: list[Episode],
           burmese: list[Episode], mode: str, caution: str) -> str:
    chunks = [f"# Bilingual episode merge\n# pairing: {mode}\n# {caution}\n"]
    for number, (c_index, b_index) in enumerate(pairs, 1):
        c_episode = chinese[c_index] if c_index is not None else None
        b_episode = burmese[b_index] if b_index is not None else None
        bits = []
        if c_episode:
            bits.append(f"Chinese {c_episode.title}")
        if b_episode:
            bits.append(f"Burmese {b_episode.title}")
        chunks.append(f"\n[episode {number}]\n")
        if bits:
            chunks.append("(" + " | ".join(bits) + ")\n")
        chunks.append("\nChinese original\n----------------\n")
        chunks.append((c_episode.body if c_episode else "(no counterpart)") + "\n")
        chunks.append("\nBurmese version\n---------------\n")
        chunks.append((b_episode.body if b_episode else "(no counterpart)") + "\n")
    return "".join(chunks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pair", choices=["order", "map"], default="order")
    parser.add_argument("--map", type=Path, help="JSON list of {chinese, burmese} chapter numbers")
    parser.add_argument("--chinese", type=Path, default=CHINESE)
    parser.add_argument("--burmese", type=Path, default=BURMESE)
    parser.add_argument("-o", "--output", type=Path, default=OUTPUT / "episodes.txt")
    parser.add_argument("--report", type=Path, default=OUTPUT / "pairs.json")
    parser.add_argument("--first", type=int, default=None, help="write only the first N episodes")
    parser.add_argument("--only-matched", action="store_true",
                        help="omit chapters that have no counterpart")
    args = parser.parse_args(argv)

    chinese = chinese_episodes(args.chinese)
    burmese = burmese_episodes(args.burmese)
    print(f"[merge] Chinese chapters: {len(chinese)} ({chinese[0].label}..{chinese[-1].label})")
    print(f"[merge] Burmese chapters: {len(burmese)} ({burmese[0].label}..{burmese[-1].label})")

    if args.pair == "order":
        count = min(len(chinese), len(burmese))
        pairs: list[tuple[int | None, int | None]] = [(index, index) for index in range(count)]
        pairs += [(index, None) for index in range(count, len(chinese))]
        pairs += [(None, index) for index in range(count, len(burmese))]
        caution = ("positional pairing: episode N is Chinese chapter N of the Chinese file and "
                   "Burmese chapter N of the Burmese file -- not verified as a translation pair")
    else:
        if not args.map:
            parser.error("--pair map needs --map")
        mapping = json.loads(args.map.read_text(encoding="utf-8"))
        by_chinese = {episode.label: index for index, episode in enumerate(chinese)}
        by_burmese = {episode.label: index for index, episode in enumerate(burmese)}
        pairs = []
        for item in mapping:
            c_index = by_chinese.get(item["chinese"])
            b_index = by_burmese.get(item["burmese"])
            if c_index is None or b_index is None:
                print(f"[merge] skipped {item}: chapter not found", file=sys.stderr)
                continue
            pairs.append((c_index, b_index))
        used_c = {index for index, _ in pairs}
        used_b = {index for _, index in pairs}
        pairs += [(index, None) for index in range(len(chinese)) if index not in used_c]
        pairs += [(None, index) for index in range(len(burmese)) if index not in used_b]
        pairs.sort(key=lambda pair: (pair[0] if pair[0] is not None else 10 ** 6,
                                     pair[1] if pair[1] is not None else 10 ** 6))
        caution = "explicit map supplied by --map"

    if args.only_matched:
        pairs = [(c, b) for c, b in pairs if c is not None and b is not None]
    if args.first:
        pairs = pairs[:args.first]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(pairs, chinese, burmese, args.pair, caution), encoding="utf-8")

    matched = sum(1 for c, b in pairs if c is not None and b is not None)
    report = {
        "pairing": args.pair,
        "caution": caution,
        "output": str(args.output),
        "chinese_chapters": len(chinese),
        "burmese_chapters": len(burmese),
        "episodes_written": len(pairs),
        "matched_pairs": matched,
        "unmatched_chinese": sum(1 for c, b in pairs if b is None),
        "unmatched_burmese": sum(1 for c, b in pairs if c is None),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[merge] {len(pairs)} episodes written, {matched} paired -> {args.output}")
    print(f"[merge] report -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
