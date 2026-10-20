# TXT tagging — owner Engine, mandatory WASM

From the repository root, with Python 3.10+ and Node 22+:

```sh
uv run format/tag_docx.py
# Or select a text explicitly:
uv run format/tag_docx.py --input "input/ယဲ့နင်1-200.txt"
```

The default reads `input/ယဲ့နင်1-200.txt`. The tagger reads UTF-8 text line by
line and does not read or write DOCX. Lines matching `[[HCRAWLER MARKER N]]`
are skipped before the engine, so the markers stay in the source text for
chapter-by-chapter automation but are not tagged. No translation API, API key, Burmese NLP
package or network request is part of tagging. The tagger directly reuses `scraper/wasm/box/host.mjs` (`getBox()`) and
`scraper/wasm/box/box.wasm`; there is no Engine-local host or box. The rebuilt WASM
artifact is committed; rebuilding it is documented in
`scraper/wasm/box/README.md`. Missing/tampered WASM fails instead of falling back.
The four `Engine/MonoSyllabism/mapbuilder/base/` files are build/stage-test inputs
only, never Node runtime implementations.

The production command preloads `scraper/wasm/box/runtime-guard.mjs` before
loading the Engine. It rejects imports and file reads of the four plain map
modules and rejects JSC/bytenode. The internal worker refuses to start without
that guard and boots the shared WASM box before tagging. Build and explicitly
separate stage-test processes do not preload this production guard.

## What runs

1. Read the UTF-8 prose text directly, preserving characters, tabs and line
   breaks. One input line is one paragraph; the tagger no longer parses a DOCX.
2. Reuse the original scraper syllable cache. Its 2,525 reference rows were
   verified against the supplied builder using the real master's 2,483 Burmese
   syllables (including its 37 injected roots and 5 standalones).
3. Rebuild POS with the owner's `runBuildPos`. Its cleanup operates on a work
   copy; the original master and input text are not changed.
4. Encode through the complete WASM `mapperNormalize` entrypoint, then run the
   owner's segmentor, POS walker, pass-through kernel and raw-POS formatter.
   Using raw `normalize` followed by `mapperStr` did not protect English from
   the internal symbol alphabet; the input adapter now uses the complete encoder.

## Outputs

Under `output/tagger/`:

- `ယဲ့နင်1-200.raw_pos.txt` — the tagged text, one tagger unit per line.
- `ယဲ့နင်1-200.report.json` — counts, input/runtime hashes and limitations.
- `ယဲ့နင်1-200.pos-rejected.txt` — dictionary entries rejected by the supplied builder.

The tagger writes **no DOCX**. The prose part of the input is copied to ignored
`.work/` for the engine; chapter-marker lines are skipped. Work copies and logs
stay there. An explicit
`--max-paragraphs 20` produces a separately named pilot, not the full output.
Output layout is not the source layout: the supplied holder groups the 59,681
prose paragraphs into 12,096 tagger units. The 197 chapter markers are omitted
from the tagged text. The text output is the engine's direct result, not a DOCX
round-trip.

## Plain Burmese text copy

The one-time DOCX-to-text conversion is a separate tool; the tagger does not call
it:

```sh
uv run format/docx_text.py          # first run, or --force to regenerate
```

Default: `input/ယဲ့နင်1-200.docx` → `input/ယဲ့နင်1-200.txt`. It reads the DOCX
ZIP/XML directly, removes only the observed export wrappers and page labels, and
preserves the translator's existing quote characters. It does
not add tags or normalize Burmese text, and trims only trailing spaces left by the
PDF-to-DOCX export. The original DOCX remains unchanged.
Current extraction: **59,681 prose paragraphs** plus **197 chapter markers**,
6,358,707 bytes, 59,878 lines; 59,425 lines had trailing spaces trimmed. Each
marker is `[[HCRAWLER MARKER N]]` immediately above the detected chapter title;
`N` is sequential and independent of the printed chapter number. The text is a
working copy, not a replacement of the original DOCX.

## PDF-export damage repair

The DOCX came out of a PDF conversion with the vowel pair `ေ` + `ာ` attached one
consonant to the left. `သဘော` never appears in the file; `သေဘာ` appears 254
times, and the same shape hits `အတော်` (99), `သဘောထား` (67), `သလောက်` (40) and
`အဖော်` (13). The dictionary is not missing these words: `သ  ဘော`,
`သ  ဘော  ထား`, `သ  ဘော  တ  ရား` and `အ  တော်` are all entries.

```sh
uv run format/repair_damage.py input/ယဲ့နင်1-200.txt --dry-run
uv run format/repair_damage.py input/ယဲ့နင်1-200.txt   # -> <stem>.damage-repaired.txt
uv run format/docx_text.py --force --repair-damage       # repair during extraction
node format/repair_damage.mjs input/ယဲ့နင်1-200.txt      # same rules, same bytes
```

The repair never trusts the shape. Three passes run in order: reviewed
corrections from `format/damage_ledger.json` (`ငေကာ` -> `ကြော` 261 times,
`မေကာက်` -> `မကြောက်` 9), the digit `၀` restored to the letter `ဝ` where the
letter makes a real word (161), and the vowel window itself (1,940) only when

1. the shape does not occur inside any dictionary entry — this is what protects
   `စေကာ`: it sits inside `စေ  ကာ  မူ` (CONJUNCTION and SPLIT), so
   `ဖြစ်စေကာမူ` is left alone even where `စေကာမူ` does not follow;
2. the text at that position is not already a dictionary word;
3. the repaired text is a dictionary word, or a prefix of one that ends on a
   syllable boundary (`မေကာင်း` -> `မကောင်း` from `မ  ကောင်း  မှု`).

Words that look damaged but are correct are protected by name: `ကေလာင်`
(pen, 9), `စေတာ`/`စေရာ` (causative), `သေလား` (dead or alive), `စာပေရောင်`.
Everything else is counted and skipped. On the 59,879-line file: **2,375
repairs**, 34 protected, 2,613 occurrences skipped because the shape is
attested, 1,292 because no dictionary word backed the repair; `စေကာမူ` stays at
43. The second pass repairs nothing, and the Python and JavaScript builds produce
byte-identical output. The tagger on the repaired copy drops `{?}` from 106,612
to 103,995, removes all 254 `သေ{n}  ဘာ{aj,pn}` pairs and emits `သဘော{...}`
instead. The 1,214 POS rejections do not change: those are Pali and
stacked-consonant syllables absent from the syllable map, which is a different
fault from this damage.

## These are candidates, not resolved grammar

The current supplied kernel is pass-through. Raw ambiguity (`{n,v,...}`) and
unknowns (`{?}`) are retained; English can remain `{?}` without changing its
surface. No tags are invented and no third-party classifier is substituted.
The completed full run processed 59,681 prose lines (197 markers skipped) into 12,096 units,
with 625,428 tag occurrences, 106,612 unknown-tag occurrences and 270,880
ambiguous-tag occurrences. These counts are **not an accuracy score**.
The POS builder rejected 1,214 dictionary entries; the originals remain intact.
Exact phrase alignment and grammatical disambiguation are not established
by this tagging step. The three-route MT pilot is described in `MT.md`;
compound-first sentence/style resolution remains a later comparison stage.

`top` and `resolution` belong to comparison. Normalizer preflight checks the
actual `mapData` tables in WASM, rather than treating comparison-only edits as
normalizer changes. The POS builder uses a work copy of the dictionary.
