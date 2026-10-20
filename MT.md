# MT pilot: direct Burmese, English-pivot Burmese, and approved phrase memory

## Exactly three routes

For each selected Chinese source unit, `mt.py` runs:

1. Chinese → Burmese (`zh_my`): the direct candidate.
2. Chinese → English (`zh_en`): the actual intermediate English.
3. That English → Burmese (`en_my`): the pivot candidate.

There are no Chinese back-translation calls. The output keeps all three texts,
chapter metadata, exact Chinese source spans and optional raw provider alignment.
A shared provider may itself use internal pivots: these routes are not claimed
to be independent models, and disagreement/agreement is not an accuracy verdict.
An approved local phrase-memory entry can replace a leg exactly; machine output is
never approved automatically.

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
  one record per source unit containing `zh_my`, `zh_en`, `en_my`, each leg's
  `origin`, plus the `memory` review block.
- `output/mt/memory.sqlite3` — approved/pending phrase and glossary entries.

A successful Chinese→English leg is reused as the English→Burmese input; the
pivot does not translate an invented or separately edited English sentence.
Successful legs survive interruption. There is no automatic retry of billable
POSTs: a timed-out request may already have been processed. Final JSONL replaces
an earlier final file only after all selected units finish successfully.

Source text, line endings and Chinese script are preserved. Chapter headers are
metadata, not translated prose. The source limit is measured in UTF-16 units;
recorded source offsets are Python Unicode code points, not provider UTF-16
alignment offsets. No OCR repair or Traditional/Simplified conversion is applied.

## Approved phrase memory (backend only)

`mt_memory.py` is a local SQLite translation memory. There is **no GUI** and no
automatic promotion of machine output. An entry is either `suggested` (draft) or
`approved` (may be reused), and either a normal `phrase` or a glossary `term`.
Entries are route-specific: a Chinese→English entry is not a Chinese→Burmese hit.

```sh
# Draft, then approve explicitly:
uv run mt_memory.py add --source '你們在幹什麼？' --target "YOUR_APPROVED_BURMESE" \
  --from zh-Hant --to my
uv run mt_memory.py approve 1

# A reviewed glossary term (still needs approval to be a glossary hit):
uv run mt_memory.py add --source '葉寧' --target "YOUR_APPROVED_NAME" \
  --from zh-Hant --to my --kind term
uv run mt_memory.py approve 2

uv run mt_memory.py list --status approved
uv run mt_memory.py suggest '你們在幹什麼' --from zh-Hant --to my
uv run mt_memory.py glossary --from zh-Hant --to my
uv run mt_memory.py stats
```

Default store: `output/mt/memory.sqlite3` (ignored in Git). Export reviewed JSONL
when you want a durable copy; copy a reviewed export somewhere tracked if you want it
versioned. Import validates every line before writing and will not downgrade an
approved entry to `suggested`:

```sh
uv run mt_memory.py export --output output/mt/memory-export.jsonl
uv run mt_memory.py import --input output/mt/memory-export.jsonl
```

Matching normalizes NFKC and whitespace **for lookup only**; the approved text is
stored and reused exactly as entered. Only an approved exact match short-circuits a
billed leg. Similar entries are shown with a similarity score but are never applied.
Approved phrases and glossary terms that occur inside a larger unit are reported as
`direct_phrase_hits` / `glossary_hits`; they are context, not automatic replacement.

`mt.py --run` writes a `memory` block per unit with suggestions, phrase hits and
glossary hits. Every leg records `origin`: `provider`, `provider_cache` or
`translation_memory`. `--suggestions 0` disables similar-phrase suggestions but
keeps phrase/glossary reporting. There is no verified inline glossary parameter in
Azure Translator v3 `translate`, so glossary terms are not silently injected into a
paid request; they remain approved reference data for review and the later AI stage.

Repeated source phrases can be ranked without any Burmese tokenizer. This report
does not create or approve entries:

```sh
uv run mt_memory.py frequent --input input/chinese-0511241012-from-8011_93.txt --top 30
```

It splits on Chinese sentence/dialogue punctuation, ignores literal HTML-entity
fragments, and shows a translation only when an approved exact entry already exists.
The source text is not modified.

### Quote repair script

`repair_quotes.py` repairs the literal quote entities without changing any other
character. It understands `&quot;`, `&amp;quot;`, `&amp;amp;quot;`, `&#34;` and
`&#x22;`, chooses `“`/`”` from local context, preserves CRLF/BOM/line count, and
can write a TSV audit:

```sh
# Safe default: writes <input>.quotes-repaired.txt
uv run repair_quotes.py input/chinese-0511241012-from-8011_93.txt \
  --report /tmp/quote-report.tsv

# Explicit in-place rewrite:
uv run repair_quotes.py input/chinese-0511241012-from-8011_93.txt --in-place
```

The conversion is context-aware rather than a blind alternating replace: it handles
existing `“`/`”`, a closing quote before a narrative tag, a new quote after narrative
ending in `。`, and short nested term pairs. It flags uncertain choices in the report;
it does not repair the substituted characters described below.

The supplied Chinese file **originally** contained 2,824 literal `&quot;` sequences.
The repair converted them to **2,486 opening quotes** and **336 closing quotes**,
removed 2 duplicate openings, and flagged 116 conversions for review. The pre-repair
text remains recoverable from commit `61b4b86`.

### Remaining source-quality caveat

The file still contains repeated substituted characters. For example, the recurring
`實不讓教死，教就點無教了` appears 53 times, where the novel's title is
《再不讓我死，我就真無敵了》. The same characters appeared on the sampled
corresponding live page, so this is **not introduced by HCrawler or by this tool**.
The supplied DOCX is a Burmese translation, so it was not used to rewrite the
Chinese. No glyph remapping or OCR cleanup is applied. The corruption affects both
phrase counts and any paid translation; validate or obtain a correct Chinese source
before a full-book MT run.

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
