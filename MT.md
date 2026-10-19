# MT pilot: direct Burmese versus English-pivot Burmese

## Exactly three routes

For each selected Chinese source unit, `mt.py` runs:

1. Chinese → Burmese (`zh_my`): the direct candidate.
2. Chinese → English (`zh_en`): the actual intermediate English.
3. That English → Burmese (`en_my`): the pivot candidate.

There are no Chinese back-translation calls. The output keeps all three texts,
chapter metadata, exact Chinese source spans and optional raw provider alignment.
A shared provider may itself use internal pivots: these routes are not claimed
to be independent models, and disagreement/agreement is not an accuracy verdict.

Azure Translator v3/general is the configured **baseline candidate**, not a
proven accuracy winner for this novel. Official documentation lists `my`, `en`,
`zh-Hant` and `zh-Hans` text translation and documents this API's request format:

- https://learn.microsoft.com/en-us/azure/ai-services/translator/language-support
- https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/v3/translate

No live authenticated MT call or translation-quality benchmark has been run by
this setup. Paid requests require an explicit `--run` and your locally configured
credentials. The default is an offline plan.

## Run from the repository root

```sh
# No MT API call, key, output file or cache creation:
uv run mt.py --input input/chinese-0511241012-from-8011_93.txt --max-units 3 --plan

# After configuring your credentials locally:
uv run mt.py --input input/chinese-0511241012-from-8011_93.txt --max-units 3 --run
```

The three-unit uncached plan has an upper bound of **nine requests**. The default
is at most ten units. Whole-input processing requires explicit `--all`.
`uv` may download its declared Python dependency on first use; an offline plan
itself makes no translation request. No third-party Burmese NLP is installed.

## API configuration — guidance only

Use your own Azure Translator resource. Follow its key/region instructions:
https://learn.microsoft.com/en-us/azure/ai-services/translator/text-translation/reference/authentication

Configure these in your own terminal, not in chat or Git:

- `AZURE_TRANSLATOR_KEY` — your subscription key.
- `AZURE_TRANSLATOR_REGION` — the resource region when required by that resource.
- `AZURE_TRANSLATOR_ENDPOINT` — optional HTTPS base; defaults to
  `https://api.cognitive.microsofttranslator.com`.

For Bash, you can read the key without echoing it or putting its value in a command:

```sh
read -rsp 'Azure Translator key: ' AZURE_TRANSLATOR_KEY; echo
export AZURE_TRANSLATOR_KEY
```

The program only reads environment variables. It does not provision anything,
load/write `.env`, save credentials, or follow HTTP redirects with the key.
Set the region according to your resource rather than guessing one.

## Cache, source protection and output

Default local artifacts, ignored in Git:

- `output/mt/cache.sqlite3` — successful translations cached independently by
  exact text, language pair, endpoint and API options, never by key.
- `output/mt/chinese-0511241012-from-8011_93-zh-Hant-azure-candidates.jsonl` —
  one record per source unit containing `zh_my`, `zh_en`, `en_my`.

A successful Chinese→English leg is reused as the English→Burmese input; the
pivot does not translate an invented or separately edited English sentence.
Successful legs survive interruption. There is no automatic retry of billable
POSTs: a timed-out request may already have been processed. Final JSONL replaces
an earlier final file only after all selected units finish successfully.

Source text, line endings and Chinese script are preserved. Chapter headers are
metadata, not translated prose. The source limit is measured in UTF-16 units;
recorded source offsets are Python Unicode code points, not provider UTF-16
alignment offsets. No OCR repair or Traditional/Simplified conversion is applied.

## Comparison design agreed with the owner

This is the next stage, **not an already implemented grammar resolver**:

1. Dictionary output supplies component lexical tags. A whole compound such as
   `ရေတွင်း` need not be a dictionary entry: `ရေ{n} + တွင်း{n}` can produce a
   compound noun under the supplied compound rule, retaining both children/spans.
2. Build compound candidates before interpreting outer sentence/clause roles.
   Do not mistake flat POS windows for composed words or resolved grammar.
3. Default prose to **LSE (literature style in essay)**. Quoted character speech
   uses **LSN (narration style)**. The owner's examples are `နေကောင်းပါသည်`
   versus `နေကောင်းတယ်၊၊`; style is not inferred from a global particle majority.
4. Use `master.json.top` and `resolution` with sentence style and grammatical
   role to resolve particles. Do not globally replace a surface that has several
   possible roles. Use the supplied rule data for noun/verb/adjective/adverb
   overlap and the grammatical job of composed units; do not mutate raw tags.
5. Only after validated phrase alignment may exposed/differing 1:1 phrases be
   offered to AI, with small context and relevant rules/glossary/tone examples.
   No full-chapter AI call or automatic rewriting is enabled here.

The actual rule data is in `engine/knowledge/isTreasure/mainrules.js` (JSON),
with the data-only sequence/compound table in root `mainrules.js`. `top` and
`resolution` belong to comparison, not the pass-through POS kernel.

## Optional raw evidence (not grammar resolution)

```sh
uv run mt_compare.py --profile
uv run mt_compare.py --input output/mt/chinese-0511241012-from-8011_93-zh-Hant-azure-candidates.jsonl
```

This audits the supplied catalog and can tag **both** Burmese candidates through
the existing guarded scraper WASM, showing literal differences and lexical
observations. It does not apply the unfinished compound/sentence/style resolver.
The reference audit is `analysis/reference-data-audit.json`; old flat sequence
window counts are not used as grammar decisions. JSON5 reads only the declared
rule-data array; it does not execute JavaScript. The four protected map algorithms
remain WASM-only in production.

Translation, raw annotation and comparison-data identities are separate, so
comparison-rule edits do not cause paid retranslations. POS inputs depend on the
dictionary/map data; `top`/`resolution` remain comparison data. The code verifies
that normalizer tables match the built WASM. AI eligibility stays false and exact
1:1 phrase alignment is explicitly not established.
