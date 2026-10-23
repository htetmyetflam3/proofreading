# Start card — Chinese → Burmese translation, with an English quality gate

## Active task and final target

The final translation target is **Burmese**. Before drafting Burmese, use the retained
API English and local Argos English as intermediate witnesses and check both against
the original Chinese. If the API English is already faithful enough, use it as a
bridge into Burmese. If it is not, correct it in the working context first, then
translate that corrected meaning into Burmese. In either case, verify the Burmese
against Chinese. Do not stop after the English check: it is Phase 1 of the Burmese
task, not a separate deliverable.

There is no API-generated Burmese baseline in this checkout. Do not call an API,
recreate API Burmese, or modify `content/mtranslate/english.txt`, `zh-en.txt`, or
`en-zh.txt`. The existing English is an intermediate only; Burmese is the final
output.

## Ensure the MCP tools are actually advertised

The task needs `read_chapter`, `compare_english_chapter`, `review_brief`,
`review_lookup`, `lookup_name`, `check_names`, `register_name`, `previous_burmese_context`,
`segment_text`, `lookup_word`, `save_draft`, `export_drafts`, `save_verse`, and
`export_verse`. Start the MCP server with `--tools burmese-translation` (or without a
`--tools` filter). This preset includes the workflow tools but excludes the API
translation tools. The smaller `lean` preset omits `register_name`; the
`english-review` preset omits the chapter reader, draft, and verse tools. If a tool
is missing from the agent's tool list, check the MCP server's `--tools` setting and
restart with the right preset; the tool is not absent from the repository.

The direct CLI can also invoke local tools, for example:

```sh
python3 mcp.py --register-name --key "Shen Ji" --burmese "ရှန်းကျီ" --note "ch194"
```

## First-turn calibration

Read the chapter-specific review and terminology before translating:

```text
review_brief {}
review_lookup {"chapter": 194}
lookup_name {}
```

Use the relevant review section for each chapter. The review describes the novel;
its conversational voice is not the novel's narration register. Follow the detailed
Burmese register, terminology, draft, and verse guidance in
`mt/quality/finetune-agent-prompt.md`, subject to this start card's fresh-translation
workflow. That file's old requirements for an existing API Burmese `my` field do
not apply.

## Phase 1 — verify the English bridge against Chinese

Use ten-paragraph windows for the current Chinese chapter. The comparison is
read-only and returns the original Chinese (`zh`), retained API English (`api_en`),
and local Argos English (`machine_en`):

```text
compare_english_chapter {"chapter": 194, "start": 1, "count": 10}
```

Read alignment metadata first, then continue only at `window.next_start`. The local
Argos output is a fallible witness, not an authority. If English is accurate enough,
carry its meaning forward. If it is materially wrong or incomplete, make a corrected
English working version for that passage before translating it into Burmese. Never
write those corrections back to `english.txt`.

If the tool reports missing inputs or alignment errors, stop and report the exact
problem; do not shift paragraphs or guess. `read_chapter` may be used for bounded
Chinese source paragraphs and stable IDs. For chapters 194 onward it is expected that
`translation.available` is false and the `my` field is absent: that means there is no
API Burmese baseline, not that Chinese is unavailable and not that the task should
stop.

## Phase 2 — translate into Burmese

Translate the Chinese meaning, using the verified English bridge only as support.
Chinese remains the semantic authority; never translate Burmese from a mistaken
English sentence. Apply the house style from the Burmese task: formal written
narration, colloquial dialogue in quotation marks, and no register mixing inside a
sentence. Preserve paragraph order and all story content.

The human Burmese source (`content/source/ယဲ့နင်.txt` and
`content/merged/episodes.docx`) is retained for prior terminology/context, but has
known encoding damage. For chapters 194–195 there is no same-chapter human Burmese
reference. Use bounded prior-context lookups when a recurring term needs precedent:

```text
previous_burmese_context {"chapter": 194, "keyword": "နတ်"}
```

Treat damaged Burmese only as an uncertain clue; verify meaning against Chinese.

Use `content/reference/EtoBnames.txt` as the canonical spelling list. Check each
Burmese paragraph with `check_names`; use `register_name` for a genuinely new
recurring name or term only. Never edit or replace an existing entry. Use
`segment_text` and `lookup_word` to check the Burmese draft where useful; do not feed
the damaged human reference or review quotations to the segmentor.

Save fresh translations with `save_draft` and export with `export_drafts`. Do not
invent an API-Burmese `ai_text` source: omit that field and note that the draft was
translated from Chinese with the verified English bridge. Drafts are unapproved
until the human reviews them.

## Verse and scope

Poems, songs, maxims, couplets, inscriptions, and philosophical lines get a separate
verse-focused session/pass; do not flatten them into ordinary prose or silently omit
them. Keep their Chinese paragraph IDs, translate them into Burmese in that separate
pass, and record/export the separate verse review with `save_verse` and
`export_verse`. Any English recorded there is only a review aid, never the final
translation.

Work one chapter at a time: chapter 194, then stop and report; chapter 195 belongs in
a separate session. Do not continue beyond 195 unless asked. Save Burmese verse text
as a draft too; `save_verse` stores its separate English review aid. No API calls, no
recreation of API Burmese, and no edits to source, DOCX, English, or local MT files.

## Required final report

For each chapter, report the paragraph range read, whether API English needed
correction against Chinese, Burmese paragraphs drafted, names registered, verse lines
handled separately, and anything uncertain or unverified. Return Burmese as the
translation deliverable; include only a concise note on English-bridge corrections.
