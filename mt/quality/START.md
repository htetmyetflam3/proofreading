# Start card — the first turn, cheap

This repo proofreads Burmese. You judge the **AI translation** (RapidAPI,
`content/mtranslate/rapidapi/`) against the **reference** (the human Burmese in
`episodes.docx`) and rewrite it into the author's voice. You never translate a
chapter yourself.

**Read this card, not the manual.** `mt/quality/finetune-agent-prompt.md` is 490
lines / ~8k tokens; it is the full procedure and you read it once, later, when
you actually start drafting. Every turn that re-reads it is a turn Groq bills.

## Turn one — three calls, nothing else

```
review_brief {"chars_per_arc": 60}
review_lookup {"chapter": 194}
read_chapter {"chapter": 194, "start": 1, "count": 10}
```

`review_brief` is the whole 7,279-line review in one digest: 15 characters, the
three known defects, the verdict, every arc's opening. Always pass
`{"chars_per_arc": 60}` — the default size is 8–13k tokens, the trimmed one
4–6.5k, and the difference is a third of a free day.

Then answer in this shape and stop:

1. **Register you will enforce** — one or two lines. Narration closes on
   သည် / မည် / ၏ / ခြင်း and keeps တွင်, များ; dialogue inside “…”, closes on
   တယ် / ပဲ / မယ်. The two never mix in one sentence.
2. **What `translation` says** — `available`, `attached`, `mismatched`.
3. **What `window` says** — `total`, and whether anything is left.

If `available` is false or `attached` is 0, stop and say:
`python3 mt/apicaller.py --run --env-file ~/.env` must run first.

## The four rules that keep a session alive

Every card-free lane is thin — about 10k tokens a minute or a few thousand
tokens a turn, whichever provider you are on (`mt/SETUP.md`, *Which one to
actually use*, has the numbers and how to check yours). Groq's 250k-per-minute
plan needs a card. A request costs its whole input, so the way a session dies is
by re-sending big things, and one `review_brief` at the default size is 8–13k
tokens on its own: the review is mostly Myanmar script, and Myanmar tokenizes
badly.

1. **Never re-read a file you already read.** If you need one section, say which.
2. **Never pull a whole chapter.** `read_chapter` takes `start` and `count`;
   ten paragraphs is ~1.5k tokens, all 166 is ~13k, and it is re-sent on every
   later turn. `window.next_start` tells you where to continue.
3. **Never paste a tool result back.** Quote the one field that decided it.
4. **Never open** `content/review/burmese-overview.md` (673 KB),
   `content/source/*.txt` (6 MB) or `Engine/knowledge/isTreasure/master.json`
   (1.4 MB). The tools exist so you do not have to.

## Before you open a big file, use `tools/`

The crawl (4.1 MB), the review (673 KB) and `master.json` (1.4 MB) each have a
script that answers the question without reading them. Run these instead:

```sh
python3 tools/audit_source.py --check 194-408     # which chapters exist
python3 tools/audit_source.py --titles --from 194 # what they are called
```

Exit 1 from `--check` means holes in the range — say which, do not paper over it.

## The two things that are not tools

- **Finding names.** You notice a term while reading; `register_name` writes it.
  No scanner, and a term is not only a person — a weapon, a martial art, a
  bloodline ability, a pill, a rank, a place. Left side is the English of the
  zh-en column, right side the AI's Burmese, corrected if wrong.
- **Finding verse.** Poems, songs, maxims and philosophy lines are your
  judgement; `save_verse` records one with an English version, `export_verse`
  writes the section the human reviews. `kind: none` means "checked, nothing".

## When you start drafting

Read `mt/quality/finetune-agent-prompt.md` **once**, then work in windows of ten
paragraphs. The manual has the procedure, the classes A–F, the output contract
and the honesty clause. This card has only the order and the budget.

## Facts you must not get wrong

- The list `content/reference/EtoBnames.txt` outranks the API, always.
- The reference's encoding damage is not yours to repair; it is a tone oracle.
- Never call the API translation "MT". MT is the zh-en column.
- `{?}` tags are not errors by themselves.
- `save_draft` needs `ai_text`, byte-exact, plus `draft`.
