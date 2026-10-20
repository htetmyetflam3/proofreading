# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Extract the supplied Burmese DOCX prose into a plain UTF-8 text file.

This reuses the DOCX ZIP/XML extractor from `tag_docx.py`: it keeps prose,
tabs and explicit breaks, removes only the observed PDF/export wrappers
(`# Source:`, `# Pages:`, `# Detection:`, `--- Page N ---`, separators), and
does not tag or normalize Burmese text.

Default output is the matching text beside the DOCX input:
    input/ယဲ့နင်1-200.docx -> input/ယဲ့နင်1-200.txt

The original DOCX is never modified. The text preserves the translator's
existing quotation characters; it is not a quote-repair pass. Trailing spaces
left by the PDF-to-DOCX export are trimmed; no other whitespace is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from tag_docx import digest, extract

ROOT = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", type=Path,
                        help="DOCX path; default: the single DOCX in input/")
    parser.add_argument("-o", "--output", type=Path,
                        help="Text path; default: input/<stem>.txt")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing text output")
    args = parser.parse_args(argv)

    temporary = None
    index_temporary = None
    try:
        docx = args.input
        if docx is None:
            candidates = list((ROOT / "input").glob("*.docx"))
            if len(candidates) != 1:
                raise ValueError("Specify a DOCX path (there is not exactly one DOCX in input/)")
            docx = candidates[0]
        docx = docx.resolve()
        if not docx.is_file():
            raise ValueError(f"Input DOCX does not exist: {docx}")
        destination = (args.output or (ROOT / "input" / (docx.stem + ".txt"))).resolve()
        if destination == docx:
            raise ValueError("Text output must not replace the DOCX")
        if destination.exists() and not args.force:
            raise ValueError(f"Output already exists: {destination}; use --force")
        destination.parent.mkdir(parents=True, exist_ok=True)

        original_hash = digest(docx)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".docx-text-", suffix=".txt",
                                                      dir=destination.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        descriptor, index_name = tempfile.mkstemp(prefix=".docx-index-", suffix=".jsonl",
                                                  dir=destination.parent)
        os.close(descriptor)
        index_temporary = Path(index_name)
        counts = extract(docx, temporary, index_temporary, None)
        if digest(docx) != original_hash:
            raise ValueError("Original DOCX was modified during extraction")

        text = temporary.read_text(encoding="utf-8")
        cleaned_lines = []
        trimmed_lines = 0
        for line in text.split("\n"):
            cleaned = line.rstrip(" \t\r")
            if cleaned != line:
                trimmed_lines += 1
            cleaned_lines.append(cleaned)
        cleaned = "\n".join(cleaned_lines)
        if cleaned != text:
            with temporary.open("w", encoding="utf-8", newline="") as stream:
                stream.write(cleaned)
        text = cleaned
        with temporary.open("r", encoding="utf-8", newline="") as stream:
            line_count = sum(1 for _ in stream)
        os.chmod(temporary, 0o644)
        os.replace(temporary, destination)
        temporary = None
        summary = {
            "input": str(docx),
            "output": str(destination),
            "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "output_bytes": destination.stat().st_size,
            "output_chars": len(text),
            "output_lines": line_count,
            "straight_quotes": text.count('"'),
            "curly_open_quotes": text.count("“"),
            "curly_close_quotes": text.count("”"),
            "trailing_whitespace_lines_trimmed": trimmed_lines,
            "docx_sha256": original_hash,
            "original_docx_unchanged": True,
            **counts,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if index_temporary is not None:
            index_temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
