# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Repair literal HTML quote entities in a Chinese UTF-8 text file.

The supplied HCrawler text contains `&quot;` (and possibly `&amp;quot;`) where
Chinese opening/closing quotation marks belong. This tool chooses `“` or `”`
from local context, preserves every other character and every line ending, and
can write an audit report. It is not a general HTML unescaper.

Default output is a new file next to the input:
    input/chinese-...txt -> input/chinese-...quotes-repaired.txt

Use --in-place explicitly to overwrite the input. The original remains recoverable
from Git in this repository.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

# `&quot;`, `&amp;quot;`, `&amp;amp;quot;`, `&#34;`, `&#x22;`.
# Each additional escaping turns the leading `&` into `&amp;`, giving
# `&amp;quot;` (not `&amp;&quot;`). Matching is case-insensitive.
ENTITY = re.compile(r"&(?:amp;)*(?:quot|#0*34|#x0*22);", re.IGNORECASE)
LINE_END = re.compile(r"(\r\n|\n|\r)$")
OPEN_QUOTE = "“"
CLOSE_QUOTE = "”"
COLONS = ":："
CLOSING_PUNCTUATION = "！？。，、；：!?.,;:"
SENTENCE_END = "。！？!?"


@dataclass(frozen=True)
class Change:
    line: int
    column: int
    choice: str
    reason: str
    ambiguous: bool
    context: str
    start: int
    end: int


def split_line_ending(line: str) -> tuple[str, str]:
    match = LINE_END.search(line)
    if match is None:
        return line, ""
    return line[:match.start()], match.group(1)


def scan_existing_quotes(chunk: str, inside: bool) -> bool:
    """Track already-correct curly quotes between entities."""
    for character in chunk:
        if character == OPEN_QUOTE:
            inside = True
        elif character == CLOSE_QUOTE:
            inside = False
    return inside


def repair_line(body: str, line_number: int) -> tuple[str, list[Change]]:
    matches = list(ENTITY.finditer(body))
    if not matches:
        return body, []
    decisions: list[Change] = []
    inside = False
    cursor = 0
    previous_end: int | None = None
    for match in matches:
        chunk = body[cursor:match.start()]
        inside = scan_existing_quotes(chunk, inside)

        prefix = body[:match.start()]
        suffix = body[match.end():]
        left = prefix.rstrip()[-1:] if prefix.rstrip() else ""
        right = suffix.lstrip()[:1] if suffix.lstrip() else ""
        bol = not prefix.lstrip("\ufeff").strip()
        eol = not suffix.strip()
        between_previous = body[previous_end:match.start()] if previous_end is not None else ""

        if inside and prefix.rstrip().endswith(OPEN_QUOTE):
            choice = "remove"
            reason = "duplicate-opening-after-open-quote"
            ambiguous = True
        elif inside:
            choice = "close"
            reason = "closes-open-quote"
            ambiguous = False
        elif bol:
            choice = "open"
            reason = "line-start"
            ambiguous = False
        elif eol:
            choice = "close"
            reason = "line-end"
            ambiguous = False
        elif left and left in COLONS:
            choice = "open"
            reason = "after-colon"
            ambiguous = False
        elif right and right in CLOSING_PUNCTUATION:
            choice = "close"
            reason = "before-closing-punctuation"
            ambiguous = False
        elif left == "。":
            # A quote after a full stop normally opens a new quotation, but a
            # fragment ending a previous quotation can also end with a marker.
            if previous_end is not None and "。" in between_previous:
                choice = "open"
                reason = "quote-after-narrative"
            else:
                choice = "close"
                reason = "after-period"
            ambiguous = True
        elif left and left in SENTENCE_END:
            choice = "close"
            reason = "after-sentence-end"
            ambiguous = True
        else:
            choice = "open"
            reason = "default-open"
            ambiguous = True

        context = (
            body[max(0, match.start() - 28):match.start()]
            + "⟦" + match.group(0) + "⟧"
            + body[match.end():match.end() + 28]
        ).replace("\t", " ")
        decisions.append(Change(line_number, match.start() + 1, choice, reason,
                                ambiguous, context, match.start(), match.end()))
        if choice == "close":
            inside = False
        else:
            inside = True
        previous_end = match.end()
        cursor = match.end()

    # `"outer ... "term" ...` has three entities on one line in this source.
    # Without this, the term's opening quote is mistaken for the outer closing
    # quote and the pair comes out reversed. Only a short, punctuation-free gap
    # is treated as a nested term.
    if (len(decisions) == 3
            and decisions[0].choice == "open" and decisions[0].reason == "line-start"
            and decisions[1].choice == "close" and decisions[1].reason == "closes-open-quote"
            and decisions[2].choice == "open" and decisions[2].reason == "default-open"):
        gap = body[decisions[1].end:decisions[2].start]
        if (0 < len(gap.strip()) <= 6
                and not re.search(r"[\s。！？!?，、；：:.,;]", gap)):
            decisions[1] = replace(decisions[1], choice="open",
                                   reason="nested-pair-open", ambiguous=True)
            decisions[2] = replace(decisions[2], choice="close",
                                   reason="nested-pair-close", ambiguous=True)

    output: list[str] = []
    cursor = 0
    for decision, match in zip(decisions, matches):
        output.append(body[cursor:decision.start])
        if decision.choice == "remove":
            output.append("")
        elif decision.choice == "open":
            output.append(OPEN_QUOTE)
        else:
            output.append(CLOSE_QUOTE)
        cursor = match.end()
    output.append(body[cursor:])
    return "".join(output), decisions


def repair_text(text: str) -> tuple[str, list[Change], dict]:
    lines = text.splitlines(keepends=True)
    repaired: list[str] = []
    changes: list[Change] = []
    for number, line in enumerate(lines, 1):
        body, ending = split_line_ending(line)
        fixed, line_changes = repair_line(body, number)
        repaired.append(fixed + ending)
        changes.extend(line_changes)
    counts = {"entities": len(changes), "open": 0, "close": 0, "removed": 0,
              "ambiguous": 0, "lines_changed": len({c.line for c in changes})}
    for change in changes:
        if change.choice == "open":
            counts["open"] += 1
        elif change.choice == "close":
            counts["close"] += 1
        else:
            counts["removed"] += 1
        if change.ambiguous:
            counts["ambiguous"] += 1
    result = "".join(repaired)
    counts["remaining_entities"] = len(ENTITY.findall(result))
    counts["input_chars"] = len(text)
    counts["output_chars"] = len(result)
    return result, changes, counts


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def atomic_write(path: Path, text: str, *, mode_from: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".quote-repair-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if mode_from is not None and mode_from.exists():
            os.chmod(temporary, stat.S_IMODE(mode_from.stat().st_mode))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_report(path: Path, changes: list[Change]) -> None:
    lines = ["line\tcolumn\tchoice\treason\tambiguous\tcontext"]
    for change in changes:
        lines.append(
            f"{change.line}\t{change.column}\t{change.choice}\t{change.reason}\t"
            f"{'yes' if change.ambiguous else 'no'}\t{change.context}"
        )
    atomic_write(path, "\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair &quot;/&amp;quot; HTML entities as Chinese opening/closing quotes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", type=Path, help="UTF-8 Chinese text file")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("-o", "--output", type=Path,
                        help="Write here; default: <input>.quotes-repaired.txt")
    output.add_argument("--in-place", action="store_true",
                        help="Overwrite the input atomically")
    parser.add_argument("--report", type=Path, help="Write a TSV audit of every change")
    parser.add_argument("--dry-run", action="store_true", help="Analyse but write no text output")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output")
    args = parser.parse_args(argv)

    try:
        if not args.input.is_file():
            raise ValueError(f"Input is not a file: {args.input}")
        if args.in_place:
            destination = args.input
        else:
            destination = args.output or args.input.with_name(
                f"{args.input.stem}.quotes-repaired{args.input.suffix or '.txt'}"
            )
        if not args.in_place and destination.resolve() == args.input.resolve():
            raise ValueError("Use --in-place to overwrite the input")
        if destination.exists() and not args.in_place and not args.force:
            raise ValueError(f"Output already exists: {destination}; use --force or --in-place")
        if args.report and args.report.resolve() in {args.input.resolve(), destination.resolve()}:
            raise ValueError("Report must be different from input and output")

        source = read_text(args.input)
        repaired, changes, counts = repair_text(source)
        if args.report:
            write_report(args.report, changes)
        if not args.dry_run:
            atomic_write(destination, repaired, mode_from=args.input)
        summary = {
            "input": str(args.input),
            "output": None if args.dry_run else str(destination),
            "dry_run": args.dry_run,
            "report": str(args.report) if args.report else None,
            **counts,
            "changed": repaired != source,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
