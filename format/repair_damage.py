# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Repair PDF->DOCX encoding damage in Burmese text, using the dictionary as judge.

The supplied DOCX was converted from a PDF and the Burmese vowel signs have
migrated one consonant to the left. The word `သဘော` is never printed; the file
contains `သေဘာ` instead, 254 times:

    correct  သ ဘ ေ ာ      (U+101E U+1018 U+1031 U+102C)
    damaged  သ ေ ဘ ာ      (U+101E U+1031 U+1018 U+102C)

The same shape also occurs in correct Burmese, because `စေ` + `ကာ` is a normal
causative followed by a normal syllable. `ဖြစ်စေကာမူ` is correct text, and
`စေ ကာ မူ` is a real dictionary entry (CONJUNCTION / SPLIT). A blind shape rule
would rewrite it to `စကောမူ` and destroy the sentence.

So the repair is anchored on the whole word, never on the four-character window:

  * the damaged text at this position must NOT already be a dictionary word
    (`စေကာမူ` is, so nothing is touched -- this is the user's rule: when both
    the damaged word and the repaired word are present, do not repair);
  * the repaired text at this position MUST be a dictionary word
    (`အတော်`, `သလောက်`, `အဖော်`, `သဘော` all are);
  * otherwise the occurrence is left alone and counted in the report.

Only the four-character window is replaced, so the rest of the word is kept:
`သေဘာထား` -> `သဘောထား`, `အေတာ်` -> `အတော်`.

Default output is a new file next to the input:
    input/ယဲ့နင်1-200.txt -> input/ယဲ့နင်1-200.damage-repaired.txt

Use --in-place explicitly to overwrite. --dry-run writes nothing and prints the
same report. Every line ending and every byte outside a repair is preserved.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "Engine" / "knowledge" / "isTreasure" / "master.json"

# Burmese base characters that can carry the displaced vowel signs.
_BASE = r"[\u1000-\u1021\u103F]"
# C1 ေ C2 ာ  -- the `ေ` (U+1031) and `ာ` (U+102C) pair belongs to C2 but has
# been attached to C1 by the PDF conversion. Captured so the window can be
# rebuilt in the correct order: C1 C2 ေ ာ.
_DAMAGE = re.compile("(" + _BASE + r")(\u1031)(" + _BASE + r")(\u102C)")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def write_text(path: Path, text: str) -> None:
    handle, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class Dictionary:
    """Flattened surface forms from the hand-made dictionary.

    Entries are stored with double spaces between syllables (`သ  ဘော`), so the
    whitespace has to be removed before a word can be compared with running
    text.
    """

    def __init__(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.forms: set[str] = set()
        self.pos: dict[str, str] = {}
        for part, entries in data["dictionary"].items():
            for entry in entries:
                form = re.sub(r"\s+", "", entry)
                if not form:
                    continue
                self.forms.add(form)
                self.pos.setdefault(form, part)
        self.maxlen = max(len(form) for form in self.forms)
        self._attested_cache: dict[str, bool] = {}
        self._by_first: dict[str, set[str]] = {}
        for form in self.forms:
            self._by_first.setdefault(form[0], set()).add(form)

    def attested(self, window: str) -> bool:
        """True when `window` occurs inside a real dictionary entry.

        `စေကာ` is not an entry, but it sits inside `စေ ကာ မူ` (CONJUNCTION and
        SPLIT). The shape is therefore attested Burmese -- `စေ` is a causative
        and `ကာ` is an ordinary syllable -- so every `စေကာ` in the text is
        correct and must not be touched, even where the whole word `စေကာမူ`
        does not follow.
        """
        if window not in self._attested_cache:
            self._attested_cache[window] = any(window in form for form in self.forms)
        return self._attested_cache[window]

    def longest(self, text: str, index: int) -> str:
        """Longest dictionary form starting exactly at `index` (empty if none)."""
        limit = min(self.maxlen, len(text) - index)
        bucket = self._by_first.get(text[index]) if index < len(text) else None
        if not bucket:
            return ""
        for size in range(limit, 0, -1):
            candidate = text[index:index + size]
            if candidate in bucket:
                return candidate
        return ""


def repair(text: str, dictionary: Dictionary) -> tuple[str, list[dict], dict]:
    spans: list[tuple[int, int, str, str]] = []
    skipped = {"shape_is_attested": 0, "damaged_is_word": 0, "no_dictionary_anchor": 0, "overlap": 0}
    changed: dict[str, int] = {}
    last_end = -1

    for match in _DAMAGE.finditer(text):
        start, end = match.span()
        if start < last_end:
            skipped["overlap"] += 1
            continue
        damaged = match.group(0)
        repaired = damaged[0] + damaged[2] + damaged[1] + damaged[3]

        # Rule 0: if this exact shape occurs inside a real word anywhere in the
        # dictionary, the shape itself is legitimate Burmese. `စေကာ` is inside
        # `စေ ကာ မူ`, while `သေဘာ` occurs in no entry at all.
        if dictionary.attested(damaged):
            skipped["shape_is_attested"] += 1
            continue

        # Rule 1: if the text already says a real word here, leave it alone.
        # `စေကာမူ` is a dictionary entry, so `ဖြစ်စေကာမူ` is never rewritten.
        # A match shorter than the window does not count (`သေ` alone is a word,
        # but it does not explain `သေဘာ`).
        if len(dictionary.longest(text, start)) >= len(damaged):
            skipped["damaged_is_word"] += 1
            continue

        # Rule 2: only rewrite when the repaired form really is a word.
        probe = repaired + text[end:end + dictionary.maxlen]
        if len(dictionary.longest(probe, 0)) < len(damaged):
            skipped["no_dictionary_anchor"] += 1
            continue

        spans.append((start, end, damaged, repaired))
        changed[damaged + " -> " + repaired] = changed.get(damaged + " -> " + repaired, 0) + 1
        last_end = end

    if not spans:
        return text, [], skipped

    pieces: list[str] = []
    cursor = 0
    for start, end, _damaged, repaired in spans:
        pieces.append(text[cursor:start])
        pieces.append(repaired)
        cursor = end
    pieces.append(text[cursor:])

    details = [
        {"offset": start, "damaged": damaged, "repaired": repaired}
        for start, _end, damaged, repaired in spans
    ]
    summary = {
        "repairs": len(spans),
        "changed": dict(sorted(changed.items(), key=lambda item: -item[1])),
        "skipped": skipped,
    }
    return "".join(pieces), details, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="UTF-8 text extracted from the DOCX")
    parser.add_argument("-o", "--output", type=Path, help="output path")
    parser.add_argument("--in-place", action="store_true", help="overwrite the input")
    parser.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    parser.add_argument("--report", type=Path, help="write the JSON report here")
    parser.add_argument("--master", type=Path, default=MASTER, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.in_place and args.output:
        parser.error("--in-place and --output are mutually exclusive")
    if args.in_place and args.dry_run:
        parser.error("--in-place and --dry-run are mutually exclusive")

    source = args.input.resolve()
    text = read_text(source)
    dictionary = Dictionary(args.master)
    repaired_text, details, summary = repair(text, dictionary)

    print(f"[damage] dictionary forms: {len(dictionary.forms)}")
    print(f"[damage] repairs: {summary['repairs']}")
    for change, count in summary["changed"].items():
        print(f"         {count:>4}  {change}")
    print(f"[damage] skipped: {summary['skipped']}")
    if args.dry_run:
        print("[damage] dry run: nothing written")
    else:
        target = source if args.in_place else (
            args.output or source.with_name(source.stem + ".damage-repaired.txt")
        )
        write_text(target, repaired_text)
        print(f"[damage] wrote {target} ({len(repaired_text)} chars)")

    if args.report:
        args.report.write_text(
            json.dumps({"source": str(source), "summary": summary, "details": details},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[damage] report {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
