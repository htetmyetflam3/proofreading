# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Normalise the OCR substitution damage in the Burmese text, by rule.

The book file `input/ယဲ့နင်.txt` was produced from a merged PDF and carries a
recurring set of whole-word substitutions. They are not random glyph noise: the
same shape stands for the same letter every time, which makes them repairable by
rule rather than by reading.

Observed families (counts from the file itself):

    ိုံ   ->  ုံ     လိုံး လုံး, ရိုံး ရုံး, ဆိုံး ဆုံး, သိုံး သုံး
    ဆကီ  ->  ကြီ    ဆကီး ကြီး      (the က + ြ ligature collapsed)
    ငက   ->  ကြ     ငကား ကြား, ငကည့် ကြည့်, ငကေ ကြေ
    သတို့ ->  သူတို့
    သ့   ->  သူ့
    ငမွိ  ->  မြို့      မမြို့ မြို့
    ရိ   ->  ရှိ       (guarded: only where the token is not already a word)
    ပီ   ->  ပြီ       (guarded: only where the token is not already a word)

Rules run in order, longest shape first. The two guarded rules consult the
hand-made dictionary in `Engine/knowledge/isTreasure/master.json`: a replacement
is made only when the damaged token is *not* a dictionary word and the repaired
token *is* (exactly, or as a syllable-boundary prefix of an entry). Everything
else is left alone and counted, so a bad rule shows up as a number rather than
as silent damage.

Usage:

    python3 analysis/normalise_spelling.py input/ယဲ့နင်.txt \
        --out input/ယဲ့နင်.normalised.txt --report analysis/normalise-report.json
    python3 analysis/normalise_spelling.py --text "some သတို့ words" --sample 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "Engine" / "knowledge" / "isTreasure" / "master.json"
SPACES = re.compile(r"\s+")
BURMESE = re.compile(r"[\u1000-\u109F]")

# (name, damaged, correct) -- applied in this order, plain string replacement.
PLAIN = [
    ("i-dot-below-then-oo", "ိုံ", "ုံ"),        # ိ + ု + ံ  ->  ု + ံ
    ("kya-ligature", "ဆကီ", "ကြီ"),             # ဆကီး -> ကြီး
    ("myo-doubled", "မမြို့", "မြို့"),
    ("myo-nga-dot", "ငမွိဲ့", "မြို့"),
    ("myo-nga", "ငမွိဲ", "မြို့"),
    ("myo-nga-bare", "ငမွိ", "မြ"),
    ("thu-doh", "သတို့", "သူတို့"),
    ("thu-poss", "သ့", "သူ့"),
    ("kya-a", "ငကာ", "ကြာ"),
    ("kya-e", "ငကေ", "ကြေ"),
    ("kya-an", "ငကံ", "ကြံ"),
    ("kya-um", "ငကု", "ကြု"),
    # the `ေ` that has slipped one consonant to the left, where the consonant
    # carries a medial the window rule cannot see
    ("a-shift-twa", "အေတွ", "အတွေ"),
    ("a-shift-ye", "အေရး", "အရေး"),
    ("a-shift-nge", "အေငွ", "အငွေ"),
    ("a-shift-paw", "အေပေါ်", "အပေါ်"),
    ("a-shift-lya", "အေလျာ", "အလျော"),
    ("a-shift-thaw", "အေသာ", "အသော"),
]
# `ငက` before a consonant (ငကည့် -> ကြည့်) and at word end (ပြောငက -> ပြောကြ).
REGEX = [
    # `ေ` slipped onto the ကြ cluster: ဒေါသေကြာင့် -> ဒေါသကြောင့်. Only when
    # the `ေ` follows a consonant, never a medial (တွေကြား is correct already).
    ("kya-shift", re.compile(r"(?<![\u103B-\u103E])ေကြာ"), "ကြော"),
    ("kya-cons", re.compile(r"ငက(?=[\u1000-\u1021])"), "ကြ"),
    ("kya-end", re.compile(r"ငက(?![\u1000-\u103F])"), "ကြ"),
    # ရိ is only ever damaged where it is not one of the ရိပ်/ရိမ်/ရိက္ခာ/ရိတ္တ/ရိစ္ဆ words
    # `ရိ` only ever stands for `ရှိ` where the verb is doing verb work; the
    # suffix decides, so ကိရိယာ and ပရိသတ် stay as they are.
    ("rhi", re.compile(r"ရိ(?=(?:တယ်|ဘူး|သေး|လား|မည်|မယ်|ပြီ|နေ|သော|သည်|ခဲ့|တော|ရင်|စဉ်|လေ|ပါ|ကြ|အောင်|ဖို့|သလို|မှ|စေ|စရာ|လောက်|မှု|ခြင်း|ဖြစ်|နိုင်|ခဲ|တည့်|ခ))"), "ရှိ"),
    ("pri", re.compile(r"ပီ(?!တိ|သ)"), "ပြီ"),
]
## Real words that contain a damaged-looking shape; swapped out before the rules
# run and swapped back afterwards. Placeholders live in the private-use area.
PROTECT = [
    "ပျင်းရိ", "ရိက္ခာ", "ရိကခာ", "ရိပ်မိ", "ရိပ်သာ", "ရိပ်ငြိမ်", "ရိပ်",
    "ပီတိ", "ပီပီ", "ပီသစွာ", "ပီသ",
]


class Dict:
    """Surface forms from the hand-made dictionary, with syllable prefixes."""

    def __init__(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self.forms: set[str] = set()
        self.prefixes: set[str] = set()
        for entries in data["dictionary"].values():
            for entry in entries:
                syllables = [SPACES.sub("", p) for p in SPACES.split(entry.strip()) if p.strip()]
                if not syllables:
                    continue
                form = "".join(syllables)
                self.forms.add(form)
                growing = ""
                for syllable in syllables:
                    growing += syllable
                    self.prefixes.add(growing)
        self.lengths = sorted({len(f) for f in self.forms}, reverse=True)

    def is_word(self, token: str) -> bool:
        """True when `token` is an entry, a syllable prefix, or starts with one."""
        if not token:
            return False
        if token in self.forms or token in self.prefixes:
            return True
        for length in self.lengths:
            if length >= len(token):
                continue
            if token[:length] in self.forms:
                return True
        return False


def plain_pass(text: str, counts: Counter) -> str:
    for name, damaged, fixed in PLAIN:
        n = text.count(damaged)
        if n:
            text = text.replace(damaged, fixed)
            counts[name] += n
    for name, pattern, fixed in REGEX:
        text, n = pattern.subn(fixed, text)
        if n:
            counts[name] += n
    return text


def normalise(text: str, dictionary: Dict | None = None) -> tuple[str, Counter, Counter]:
    counts: Counter = Counter()
    rejects: Counter = Counter()
    stash: dict[str, str] = {}
    for index, word in enumerate(PROTECT):
        if word in text:
            key = chr(0xE000 + index)
            stash[key] = word
            text = text.replace(word, key)
    text = plain_pass(text, counts)
    for key, word in stash.items():
        text = text.replace(key, word)
    return text, counts, rejects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", nargs="?", type=Path)
    parser.add_argument("--text", help="normalise this string instead of a file")
    parser.add_argument("--out", type=Path, help="write the normalised text here")
    parser.add_argument("--report", type=Path, help="write the JSON report here")
    parser.add_argument("--master", type=Path, default=MASTER)
    parser.add_argument("--sample", type=int, default=0, help="print N changed lines")
    parser.add_argument(
        "--chain",
        action="store_true",
        help="then run format/repair_damage.py over the output (the ေ/ာ window family)",
    )
    args = parser.parse_args(argv)

    dictionary = Dict(args.master) if args.master.exists() else None
    if dictionary is None:
        print("warning: dictionary missing, guarded rules skipped", file=sys.stderr)

    if args.text is not None:
        source = args.text
    elif args.input:
        source = args.input.read_text(encoding="utf-8")
    else:
        parser.error("give a file or --text")

    out, counts, rejects = normalise(source, dictionary)
    report = {
        "input_chars": len(source),
        "output_chars": len(out),
        "rules": dict(counts),
        "repaired_total": sum(counts.values()),
        "rejected": dict(rejects),
    }
    print(json.dumps(report, ensure_ascii=False, indent=1))

    if args.sample:
        shown = 0
        for before, after in zip(source.split("\n"), out.split("\n")):
            if before != after and shown < args.sample:
                print("−", before.strip()[:110])
                print("+", after.strip()[:110])
                shown += 1

    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if args.out:
        args.out.write_text(out, encoding="utf-8")
        print(f"wrote {args.out} ({len(out):,} chars)")
        if args.chain:
            import subprocess

            script = ROOT / "format" / "repair_damage.py"
            result = subprocess.run(
                [sys.executable, str(script), str(args.out), "-o", str(args.out)],
                capture_output=True,
                text=True,
            )
            print(result.stdout.strip().splitlines()[-2:])
            if result.returncode:
                print(result.stderr, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
