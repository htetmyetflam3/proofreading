#!/usr/bin/env python3
"""Render the review from markdown into YAML (foldable) and plain text.

The markdown file `output/review/burmese-overview.md` stays the source of
truth: it is what gets edited. This script only re-renders it, so the two
derived files can be regenerated at any time and never drift by hand.

    python3 analysis/review_to_yaml.py
    python3 analysis/review_to_yaml.py --md output/review/burmese-overview.md

Outputs, beside the input:

    burmese-overview.yaml   nested mapping per unit / section / block, so every
                            level folds in an editor (VS Code, Obsidian, yq)
    burmese-overview.txt    plain text: rules, indented quotes, no markup

Block kinds in the YAML mirror the markdown:

    {type: heading, text: ...}    a `**...**` line on its own
    {type: para,    text: ...}    a paragraph, wrapped lines joined
    {type: quote,   text: ...}    a `>` block, joined
    {type: note,    text: ...}    an `*...*` aside
    {type: table,   columns: [...], rows: [[...], ...]}
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MD = ROOT / "output" / "review" / "burmese-overview.md"

BOLD_LINE = re.compile(r"^\*\*(.+?)\*\*$")
ITALIC_LINE = re.compile(r"^\*(.+)\*$")


def join_wrapped(lines: list[str]) -> str:
    """Markdown hard-wraps every ~78 columns; a paragraph is one line again."""
    out: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        out.append(line)
    return " ".join(out)


def strip_inline_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"\1", text)
    return text


def parse_blocks(lines: list[str]) -> list[dict]:
    """Turn a section's lines into typed blocks."""
    blocks: list[dict] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped == "---":
            i += 1
            continue
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append({"type": "quote", "text": strip_inline_md(join_wrapped(buf))})
            continue
        if stripped.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                blocks.append(
                    {"type": "table", "columns": rows[0], "rows": rows[1:]}
                )
            continue
        if BOLD_LINE.match(stripped):
            blocks.append({"type": "heading", "text": BOLD_LINE.match(stripped).group(1)})
            i += 1
            continue
        if stripped.startswith("*") and not stripped.startswith("**"):
            buf = []
            while i < n and lines[i].strip() and not lines[i].strip().startswith((">", "|", "**")):
                buf.append(lines[i].strip())
                i += 1
            text = join_wrapped(buf)
            text = strip_inline_md(text).strip()
            blocks.append({"type": "note", "text": text})
            continue
        buf = []
        while i < n:
            cur = lines[i].strip()
            if not cur or cur == "---" or cur.startswith((">", "|")):
                break
            buf.append(cur)
            i += 1
        blocks.append({"type": "para", "text": strip_inline_md(join_wrapped(buf))})
    return blocks


def split_sections(lines: list[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
    pre: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current = None
    for line in lines:
        if line.startswith("### "):
            current = (line[4:].strip(), [])
            sections.append(current)
            continue
        if current is None:
            pre.append(line)
        else:
            current[1].append(line)
    return pre, sections


def yaml_str(text: str, indent: int) -> str:
    """Literal block scalar; every line indented to the caller's level."""
    pad = " " * indent
    body = "\n".join(pad + ln if ln else "" for ln in text.split("\n"))
    return "|\n" + body


def block_yaml(block: dict, indent: int) -> list[str]:
    pad = " " * indent
    out: list[str] = []
    kind = block["type"]
    if kind == "table":
        out.append(f"{pad}- type: table")
        out.append(f"{pad}  columns:")
        for col in block["columns"]:
            out.append(f"{pad}    - {json.dumps(col, ensure_ascii=False)}")
        out.append(f"{pad}  rows:")
        for row in block["rows"]:
            rendered = ", ".join(json.dumps(c, ensure_ascii=False) for c in row)
            out.append(f"{pad}    - [{rendered}]")
        return out
    out.append(f"{pad}- type: {kind}")
    out.append(f"{pad}  text: " + yaml_str(block["text"], indent + 4))
    return out


def block_txt(block: dict) -> list[str]:
    kind = block["type"]
    if kind == "table":
        # Burmese combining marks make monospace padding lie, so the text
        # rendering uses one row per line with · separators.
        lines = ["  " + " · ".join(block["columns"])]
        lines.append("  " + "·" * 40)
        for row in block["rows"]:
            lines.append("  " + " · ".join(row))
        lines.append("")
        return lines
    text = block["text"]
    if kind == "heading":
        return ["  " + text, ""]
    if kind == "quote":
        return ["      │ " + text, ""]
    if kind == "note":
        return ["  " + text, ""]
    return ["  " + text, ""]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args(argv)

    raw = args.md.read_text(encoding="utf-8")
    lines = raw.split("\n")
    title = lines[0].lstrip("# ").strip()

    # split on level-2 headings
    chunks: list[tuple[str, list[str]]] = []
    current = ("", [])
    for line in lines[1:]:
        if line.startswith("## "):
            chunks.append(current)
            current = (line[3:].strip(), [])
        else:
            current[1].append(line)
    chunks.append(current)

    preface_lines = chunks[0][1]
    body = chunks[1:]

    units = []
    front = []
    for heading, seg in body:
        if "ပိုင်း" in heading and "အခန်း" in heading:
            pre, sections = split_sections(seg)
            subtitle = ""
            intro = parse_blocks(pre)
            # the unit's subtitle is its first `###` line; the numbered
            # sections follow (၁။ ဇာတ်လမ်း, ၂။ ...)
            if sections and not re.match(r"^[၀-၉]+။", sections[0][0]):
                subtitle = sections[0][0]
                intro = intro + parse_blocks(sections[0][1])
                sections = sections[1:]
            units.append(
                {
                    "heading": heading,
                    "subtitle": subtitle,
                    "intro": intro,
                    "sections": [
                        {"heading": sh, "blocks": parse_blocks(sl)} for sh, sl in sections
                    ],
                }
            )
        else:
            pre, sections = split_sections(seg)
            front.append(
                {
                    "heading": heading,
                    "blocks": parse_blocks(pre),
                    "sections": [
                        {"heading": sh, "blocks": parse_blocks(sl)} for sh, sl in sections
                    ],
                }
            )

    # chapter range per unit from the heading numerals
    digits = str.maketrans("၀၁၂၃၄၅၆၇၈၉", "0123456789")
    for idx, unit in enumerate(units, 1):
        nums = re.findall(r"[၀-၉]+", unit["heading"])
        unit["id"] = idx
        unit["chapters"] = [int(n.translate(digits)) for n in nums]
        # order keys for readability
        ordered = {
            "id": unit["id"],
            "heading": unit["heading"],
            "chapters": unit["chapters"],
            "subtitle": unit["subtitle"],
        }
        ordered.update({k: v for k, v in unit.items() if k not in ordered})
        units[idx - 1] = ordered

    quote_blocks = sum(
        1 for c in front for b in c["blocks"] if b["type"] == "quote"
    ) + sum(
        1
        for c in front
        for s in c["sections"]
        for b in s["blocks"]
        if b["type"] == "quote"
    )
    quote_blocks += sum(
        1
        for u in units
        for s in u["sections"]
        for b in s["blocks"]
        if b["type"] == "quote"
    )

    stats = {
        "characters": len(raw),
        "bytes": len(raw.encode("utf-8")),
        "lines": raw.count("\n") + 1,
        "non_empty_lines": len([l for l in lines if l.strip()]),
        "space_separated_tokens": len(raw.split()),
        "units": len(units),
        "quote_blocks": quote_blocks,
    }

    # ---- YAML ----------------------------------------------------------
    out: list[str] = []
    out.append("# Generated from output/review/burmese-overview.md — do not edit.")
    out.append("# Regenerate: python3 analysis/review_to_yaml.py")
    out.append("meta:")
    out.append(f"  title: {json.dumps(title, ensure_ascii=False)}")
    out.append('  source: "input/ယဲ့နင်.txt"')
    out.append('  normalised: "input/ယဲ့နင်.normalised.txt"')
    out.append("  chapters: {from: 1, to: 195}")
    out.append("  pages: 4414")
    out.append("  language: my")
    out.append("  generated: 2026-10-21")
    out.append("  stats:")
    for key, value in stats.items():
        out.append(f"    {key}: {value}")
    out.append("  note: >-")
    out.append(
        "    Book ends mid-scene at p4414; the review covers ch 1-195 and does"
    )
    out.append("    not claim an ending.")
    out.append("preface:")
    for block in parse_blocks(preface_lines):
        out.extend(block_yaml(block, 2))
    out.append("front_matter:")
    for chunk in front:
        out.append(f"  - heading: {json.dumps(chunk['heading'], ensure_ascii=False)}")
        if chunk["blocks"]:
            out.append("    blocks:")
            for block in chunk["blocks"]:
                out.extend(block_yaml(block, 6))
        if chunk["sections"]:
            out.append("    sections:")
            for sec in chunk["sections"]:
                out.append(
                    f"      - heading: {json.dumps(sec['heading'], ensure_ascii=False)}"
                )
                out.append("        blocks:")
                for block in sec["blocks"]:
                    out.extend(block_yaml(block, 10))
    out.append("units:")
    for unit in units:
        out.append(f"  - id: {unit['id']}")
        out.append(f"    heading: {json.dumps(unit['heading'], ensure_ascii=False)}")
        out.append(
            "    chapters: [" + ", ".join(str(c) for c in unit["chapters"]) + "]"
        )
        out.append(f"    subtitle: {json.dumps(unit['subtitle'], ensure_ascii=False)}")
        if unit["intro"]:
            out.append("    intro:")
            for block in unit["intro"]:
                out.extend(block_yaml(block, 6))
        out.append("    sections:")
        for sec in unit["sections"]:
            out.append(
                f"      - heading: {json.dumps(sec['heading'], ensure_ascii=False)}"
            )
            out.append("        blocks:")
            for block in sec["blocks"]:
                out.extend(block_yaml(block, 10))
    yaml_path = args.md.with_suffix(".yaml")
    yaml_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    # ---- plain text ----------------------------------------------------
    txt: list[str] = []
    rule = "─" * 74
    txt.append(rule)
    txt.append(title)
    txt.append(rule)
    txt.append("")
    for block in parse_blocks(preface_lines):
        txt.extend(block_txt(block))
    for chunk in front:
        txt.append("")
        txt.append(rule)
        txt.append(chunk["heading"])
        txt.append(rule)
        txt.append("")
        for block in chunk["blocks"]:
            txt.extend(block_txt(block))
        for sec in chunk["sections"]:
            txt.append("")
            txt.append(chunk["heading"] and "  " + sec["heading"])
            txt.append("  " + "·" * max(4, len(sec["heading"]) // 2))
            txt.append("")
            for block in sec["blocks"]:
                txt.extend(block_txt(block))
    for unit in units:
        txt.append("")
        txt.append("")
        txt.append("=" * 74)
        txt.append(unit["heading"])
        txt.append("=" * 74)
        if unit["subtitle"]:
            txt.append("  " + unit["subtitle"])
        txt.append("")
        for block in unit["intro"]:
            txt.extend(block_txt(block))
        for sec in unit["sections"]:
            txt.append("")
            txt.append("── " + sec["heading"])
            txt.append("")
            for block in sec["blocks"]:
                txt.extend(block_txt(block))
    txt_path = args.md.with_suffix(".txt")
    txt_path.write_text("\n".join(txt).rstrip() + "\n", encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False))
    print("wrote", yaml_path)
    print("wrote", txt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
