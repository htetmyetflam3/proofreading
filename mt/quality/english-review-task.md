# Local English review task

Use this task when the assignment is to proofread the **English chapters already
translated by RapidAPI**. This is separate from the Burmese finetuning task in
`finetune-agent-prompt.md`.

You do not call RapidAPI, retranslate chapters, or read the whole book. The human
has generated the API English locally. You compare a small window against the
Chinese and local machine English, then return only the English lines that need
revision.

## 1. Compare one chapter window

Call the read-only tool with the **current Chinese chapter number**:

```text
compare_english_chapter {"chapter": 194, "start": 1, "count": 10}
```

Each returned `lines` row is one source paragraph and contains:

- `zh` — the original Chinese paragraph;
- `machine_en` — the local `zh-en` machine translation, grouped back to that
  source paragraph from its sentence-level output;
- `api_en` — the RapidAPI English for the same paragraph;
- `id` and `index` — stable chapter/paragraph reference.

Read `alignment` before judging. API JSONL source text is verified exactly; the
single-file API output is checked by chapter and paragraph count. The local MT
sentence counts are checked against the source before sentences are grouped. If
a tool reports an alignment error, **stop**; do not guess or shift rows.

The default is ten paragraphs. Continue with `window.next_start`; do not ask for
a whole chapter in one call. The default files are:

- API: `content/mtranslate/english.txt`; if it is not present or does not yet
  contain this chapter, the tool can use `content/mtranslate/rapidapi/chNNNN.en.jsonl`
  or `.en.txt` instead;
- local machine English: `content/mtranslate/zh-en/chapters/chNNNN.en.txt`.

If either translation is not on disk, stop and tell the human which input is
missing. The comparison tool is read-only and never creates or rewrites either
translation.

## 2. Look up a Burmese term from the prior chapters

When a term in the current Chinese chapter is unclear and you remember its
Burmese rendering, query it using a **Burmese-script keyword** and the current
Chinese chapter number:

```text
previous_burmese_context {"chapter": 194, "keyword": "နတ်"}
```

The required `chapter` tells the tool where to look: it searches the two
preceding **Chinese** chapters and uses the merged DOCX chapter map to find their
Burmese counterparts. For Chinese chapter 194, those are Chinese 192 and 193,
which map to Burmese 194 and 195. It returns only a few complete Burmese lines
around each exact keyword hit. Set `before` and `after` to change the context
window, or `max_hits` to cap the results.

Use the Burmese excerpt as terminology/context evidence, not as the authority
on what the Chinese means. The Chinese is the semantic source; the prior
Burmese helps recover an established English rendering. If the keyword is not
in Burmese script, the tool refuses it rather than doing a broad search.

## 3. Review and report

For each line, compare the API English with the Chinese. Use `machine_en` as a
second witness, not as an unquestioned answer. Keep API English when it is
already accurate and readable. When it is not, report the paragraph index and
ID, the proposed English, and a brief reason grounded in the Chinese or a
specific prior-Burmese context hit.

Suggested response format:

```text
Chapter 194 — paragraphs 1–10
- 0194-003-<id>: change “<API wording>” to “<revised English>” — the Chinese says …
- 0194-007-<id>: keep — API and local MT preserve the same meaning.
```

Do not copy the whole tool result back. Do not modify `english.txt`, the API
chapter files, or the machine MT files. Return only corrections and material
ambiguities; if a window needs no changes, say so and give the next window
number.
