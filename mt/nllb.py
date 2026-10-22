#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["ctranslate2>=4", "sentencepiece>=0.1.99"]
# ///
"""Chinese -> Burmese (and back) with a local NLLB-200 model.

Argos has no Burmese package, so this is the offline fallback: NLLB-200 in a
CTranslate2 conversion, run on CPU. It is the only engine in this repository
that produces actual Burmese prose for the zh-my / en-my / my-en routes.

    python3 mt/nllb.py --check
    python3 mt/nllb.py --download --repo <ct2-nllb-repo>
    python3 mt/nllb.py --from zh --to my --text "天下太平"
    cat chinese.txt | python3 mt/nllb.py --from zh --to my > burmese.txt

Reads stdin, writes stdout, one output line per input line — empty lines pass
through untouched, so the line count always matches and a downstream compare
never desynchronises.

Wire it into the route runner:

    python3 mt/translate.py --route zh-my --engine cmd \
        --cmd-template "python3 mt/nllb.py --from {source} --to {target}" \
        --engine-note "nllb-200-distilled-600M int8" --only 1 --only 2

Nothing here is committed: the weights are ~600 MB and live outside the repo.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# FLORES-200 codes NLLB expects. Accept the short codes the routes use.
LANGUAGES = {
    "zh": "zho_Hans", "zh-hans": "zho_Hans", "zh-cn": "zho_Hans",
    "zh-hant": "zho_Hant", "zh-tw": "zho_Hant",
    "my": "mya_MM", "mm": "mya_MM", "burmese": "mya_MM",
    "en": "eng_Latn", "english": "eng_Latn",
    "auto": "zho_Hans",
}
DEFAULT_MODEL = (Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
                 / "proofreading" / "nllb-200-distilled-600M-ct2-int8")
TOKENIZER = "sentencepiece.bpe.model"


def flores(code: str) -> str:
    key = code.strip().lower()
    if key in LANGUAGES:
        return LANGUAGES[key]
    if "_" in key and len(key) > 4:  # already a FLORES code, e.g. mya_MM
        return code.strip()
    raise ValueError(f"unknown language {code!r}; known: {', '.join(sorted(LANGUAGES))}")


def model_ready(directory: Path) -> tuple[bool, str]:
    if not directory.is_dir():
        return False, f"no model at {directory} (--download, or --model DIR)"
    missing = [name for name in ("model.bin", TOKENIZER)
               if not (directory / name).is_file()]
    if missing:
        return False, f"{directory} is incomplete, missing: {', '.join(missing)}"
    return True, str(directory)


def detokenize(tokens: list[str]) -> str:
    """Join pieces without dropping unknown ones.

    `SentencePieceProcessor.decode` leaves the `▁` marker in place for pieces it
    cannot map back — verified against a real OPUS-MT checkpoint, which returned
    `It's a▁peaceful▁world.`. Joining directly is what mt/translate.py does too.
    """
    text = "".join(tokens).replace("\u2581", " ")
    return " ".join(text.split())


def load(directory: Path):
    import ctranslate2  # noqa: PLC0415
    import sentencepiece as spm  # noqa: PLC0415
    translator = ctranslate2.Translator(str(directory), device="cpu", compute_type="int8")
    tokenizer = spm.SentencePieceProcessor(model_file=str(directory / TOKENIZER))
    return translator, tokenizer


def translate_lines(lines: list[str], translator, tokenizer, source: str, target: str,
                    batch_size: int = 16, beam_size: int = 4) -> list[str]:
    """One output line per input line; blanks are preserved."""
    output = [""] * len(lines)
    pending: list[int] = []

    def flush() -> None:
        if not pending:
            return
        batch = [tokenizer.encode(lines[index], out_type=str) for index in pending]
        batch = [[source] + tokens + ["</s>"] for tokens in batch]
        results = translator.translate_batch(batch, target_prefix=[[target]] * len(batch),
                                             beam_size=beam_size,
                                             max_batch_size=batch_size)
        for index, result in zip(pending, results):
            tokens = result.hypotheses[0]
            if tokens and tokens[0] == target:
                tokens = tokens[1:]
            output[index] = detokenize(tokens)
        pending.clear()

    for index, line in enumerate(lines):
        if not line.strip():
            flush()
            output[index] = ""
            continue
        pending.append(index)
        if len(pending) >= batch_size:
            flush()
    flush()
    return output


def candidates(query: str = "nllb-200 ctranslate2 int8", limit: int = 15) -> list[dict]:
    """Ask HuggingFace which converted NLLB models exist; the machine that can reach
    the Hub is the one that should answer, not this file."""
    try:
        from huggingface_hub import HfApi  # noqa: PLC0415
    except ImportError:
        raise SystemExit("pip install huggingface_hub  (needed to search or download)")
    api = HfApi()
    found = []
    for model in api.list_models(search=query, limit=limit * 3, sort="downloads",
                                 direction=-1):
        model_id = getattr(model, "modelId", getattr(model, "id", ""))
        if not model_id:
            continue
        found.append({"repo": model_id,
                      "downloads": getattr(model, "downloads", 0),
                      "likes": getattr(model, "likes", 0)})
        if len(found) >= limit:
            break
    return found


def download(repo: str, directory: Path) -> Path:
    try:
        from huggingface_hub import snapshot_download  # noqa: PLC0415
    except ImportError:
        raise SystemExit("pip install huggingface_hub  (needed only for --download)")
    directory.parent.mkdir(parents=True, exist_ok=True)
    snapshot_download(repo_id=repo, local_dir=str(directory))
    ready, detail = model_ready(directory)
    if not ready:
        raise SystemExit(f"downloaded, but {detail}")
    return directory


def check(directory: Path) -> int:
    report = {"model": str(directory), "ctranslate2": None, "sentencepiece": None,
              "ready": False, "detail": ""}
    for name in ("ctranslate2", "sentencepiece"):
        try:
            module = __import__(name)
            report[name] = getattr(module, "__version__", "installed")
        except ImportError:
            report[name] = "missing"
    ready, detail = model_ready(directory)
    report["ready"] = ready
    report["detail"] = detail
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if ready else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--from", dest="source", default="zh")
    parser.add_argument("--to", dest="target", default="my")
    parser.add_argument("--text", help="translate this instead of stdin")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--search", nargs="?", const="nllb-200 ctranslate2 int8",
                        metavar="QUERY", help="list HuggingFace CT2-NLLB models")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--repo", help="HuggingFace repo holding a CTranslate2 NLLB model")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--beam-size", type=int, default=4)
    args = parser.parse_args(argv)

    if args.check:
        return check(args.model)
    if args.search is not None:
        rows = candidates(args.search)
        if not rows:
            print("nothing found; try --search 'nllb ctranslate2'", file=sys.stderr)
            return 2
        for row in rows:
            print(f"{row['repo']:<60} ↓{row['downloads']:<9} ♥{row['likes']}")
        print("\nAny of these works if it contains model.bin and " + TOKENIZER +
              ".\nThen: python3 mt/nllb.py --download --repo <the one you picked>")
        return 0
    if args.download:
        if not args.repo:
            raise SystemExit("--download needs --repo. Find one with:\n"
                             "  python3 mt/nllb.py --search")
        print(download(args.repo, args.model))
        return 0

    ready, detail = model_ready(args.model)
    if not ready:
        raise SystemExit(f"{detail}\nRun: python3 mt/nllb.py --check")

    source = flores(args.source)
    target = flores(args.target)
    translator, tokenizer = load(args.model)

    if args.text is not None:
        print(translate_lines([args.text], translator, tokenizer, source, target)[0])
        return 0

    lines = sys.stdin.read().splitlines()
    for line in translate_lines(lines, translator, tokenizer, source, target,
                                batch_size=args.batch_size, beam_size=args.beam_size):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
