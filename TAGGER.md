# DOCX tagging — owner Engine, mandatory WASM

From the repository root, with Python 3.10+ and Node 22+:

```sh
uv run tag_docx.py
# Or select a document explicitly:
uv run tag_docx.py --input "input/ယဲ့နင်1-200.docx"
```

The default selects the sole DOCX under `input/`. No translation API, API key,
Burmese NLP package or network request is part of tagging. The tagger directly reuses `scraper/wasm/box/host.mjs` (`getBox()`) and
`scraper/wasm/box/box.wasm`; there is no Engine-local host or box. The rebuilt WASM
artifact is committed; rebuilding it is documented in
`scraper/wasm/box/README.md`. Missing/tampered WASM fails instead of falling back.
The four `engine/MonoSyllabism/mapbuilder/base/` files are build/stage-test inputs
only, never Node runtime implementations.

The production command preloads `scraper/wasm/box/runtime-guard.mjs` before
loading the Engine. It rejects imports and file reads of the four plain map
modules and rejects JSC/bytenode. The internal worker refuses to start without
that guard and boots the shared WASM box before tagging. Build and explicitly
separate stage-test processes do not preload this production guard.

## What runs

1. Read the hand-built DOCX directly as ZIP/XML, preserving prose characters,
   tabs, explicit breaks and chapter headings. Remove only the observed export
   wrappers: source/pages/detection headers, page labels and separator-only lines.
2. Reuse the original scraper syllable cache. Its 2,525 reference rows were
   verified against the supplied builder using the real master's 2,483 Burmese
   syllables (including its 37 injected roots and 5 standalones).
3. Rebuild POS with the owner's `runBuildPos`. Its cleanup operates on a work
   copy; the original master and DOCX are not changed.
4. Encode through the complete WASM `mapperNormalize` entrypoint, then run the
   owner's segmentor, POS walker, pass-through kernel and raw-POS formatter.
   Using raw `normalize` followed by `mapperStr` did not protect English from
   the internal symbol alphabet; the input adapter now uses the complete encoder.

## Outputs

Under `output/tagger/`:

- `ယဲ့နင်1-200.tagged.docx` — tagged Word companion, one paragraph per tagger unit.
- `ယဲ့နင်1-200.raw_pos.txt` — the same tagged text for downstream processing.
- `ယဲ့နင်1-200.report.json` — counts, input/runtime hashes and limitations.
- `ယဲ့နင်1-200.pos-rejected.txt` — dictionary entries rejected by the supplied builder.

Extraction text (`.source.txt`) and its paragraph index (`.paragraphs.jsonl`)
are generated locally and ignored in Git; the command regenerates them.
Offsets reference that extracted text **before WASM normalization**, not the
normalized/tagged output. Work copies and logs stay under ignored `.work/`.
An explicit `--max-paragraphs 20` produces a separately named pilot, not the full
output. Source layout is not reproduced: the supplied holder groups text into
its tagger units. The tagged DOCX's ZIP/XML and exact text round-trip are checked;
rendering in Microsoft Word has not been tested.

## Plain Burmese text copy

The DOCX can be read as plain UTF-8 text without running the tagger:

```sh
uv run docx_text.py          # first run, or --force to regenerate
```

Default: `input/ယဲ့နင်1-200.docx` → `input/ယဲ့နင်1-200.txt`. It reuses the
same ZIP/XML extractor as `tag_docx.py`, removes only the observed export wrappers
and page labels, and preserves the translator's existing quote characters. It does
not add tags or normalize Burmese text, and trims only trailing spaces left by the
PDF-to-DOCX export. The original DOCX remains unchanged.
Current extraction: **59,681 prose paragraphs**, 6,354,087 bytes, 59,681 lines;
59,425 lines had trailing spaces trimmed. The text is a working copy, not a
replacement of the original DOCX.

## These are candidates, not resolved grammar

The current supplied kernel is pass-through. Raw ambiguity (`{n,v,...}`) and
unknowns (`{?}`) are retained; English can remain `{?}` without changing its
surface. No tags are invented and no third-party classifier is substituted.
The completed full run processed 59,681 prose paragraphs into 12,096 units,
with 625,428 tag occurrences, 106,612 unknown-tag occurrences and 270,880
ambiguous-tag occurrences. These counts are **not an accuracy score**.
The POS builder rejected 1,214 dictionary entries; the originals remain intact.
Exact phrase alignment and grammatical disambiguation are not established
by this tagging step. The three-route MT pilot is described in `MT.md`;
compound-first sentence/style resolution remains a later comparison stage.

`top` and `resolution` belong to comparison. Normalizer preflight checks the
actual `mapData` tables in WASM, rather than treating comparison-only edits as
normalizer changes. The POS builder uses a work copy of the dictionary.
