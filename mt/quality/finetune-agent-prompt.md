# Burmese translation and prose-review rules (Kilo / Claude Code / Codex / Gemini CLI)

> **Active workflow:** the final target is Burmese. First verify the retained API
> English and local Argos English against Chinese; correct an inaccurate English
> passage in working context, then translate/adapt into Burmese and verify Burmese
> against Chinese. The English gate and Burmese translation are one task, not
> separate assignments. No API calls and no recreated API Burmese.
>
> The procedure below was originally written to revise API-generated Burmese. That
> Burmese output has been removed. For chapters 194 onward, do not require an API
> Burmese `my` field, do not stop because it is absent, and do not follow old
> instructions that say not to translate the chapter. Follow the active workflow in
> `mt/quality/START.md`; retain the style, review, name, dictionary, segmentation,
> draft, and separate verse-session rules below. The human Burmese reference has
> known encoding damage; it is context only, never an authority for spelling,
> grammar, style, or meaning.

This file supplies the detailed Burmese house-style and tool rules for a novel
translation workflow. The retained API English and the local Chinese→English
Argos file are intermediate witnesses; neither is the final target. The Chinese
source controls meaning.

---

## Start here — the first turn of a session

Read `mt/quality/START.md` for the active unified workflow. It covers the English
quality gate and the fresh Burmese translation procedure. Use this file for the
detailed register, terminology, name registration, segmentation, draft, and verse
rules; where an older API-post-edit instruction below conflicts with START.md,
follow START.md.

Five steps, in this order. The human gives you one chapter number and a stop
point; everything else comes from this brief, the review, and the tools.

### 1. Read the review once, in one round

```
review_brief {}
```

That is the whole background document in one bounded digest: the 15 characters
and how they relate, the three known translation defects, the reviewer's
verdict, and every story arc's title with its opening. Do not try to read
`content/review/burmese-overview.md` itself — it is 7,279 lines and 673 KB, and
it would spend the context before your first paragraph.

Pull a part in full only when the chapter you were given lands inside it:

```
review_lookup {"chapter": 194}
```

**Two traps in that document, both real.**

- **Its voice is not the author's.** The reviewer writes chatty first person on
  purpose — `တယ်`, `ပဲ`, `လို့`, `ဘူး` — and says in its header (line 6) that
  the novel's register does not apply to the document. The author writes formal
  narration with colloquial dialogue inside `“…”`. Never import the reviewer's
  register into a draft, no matter how many of its sentences sound like fun.
- **Its Burmese quotes carry the same damage as the reference.** They were
  copied out of the PDF→DOCX text. Read them for what they mean. Never copy a
  spelling out of the review, and never feed a quote to `segment_text`.

Write one or two lines before you start judging, stating the register you are
about to enforce, e.g.:

> Narration closes on သည် / ၏ / ခြင်း and keeps တွင်, များ; dialogue inside
> “…”, closes on တယ် / ပဲ / မယ်. The two never mix in one sentence.

That statement is your calibration; the reference is the evidence for it. If the
review's verdict and the reference disagree about how the book should read, the
reference wins — the review describes it, it does not overrule it.

### 2. Load the terminology before the prose

Names and titles are settled by `content/reference/EtoBnames.txt`, not by you:

```
lookup_name {"term": "Liu Jin"}
lookup_name {}                 # every entry
```

Read the "Names and terms" section below before the first draft. Terminology
first, style second: a paragraph with the right voice and the wrong name is
still wrong.

### 3. Get the Chinese paragraphs and prove alignment

```text
read_chapter {"chapter": 194, "start": 1, "count": 10}
compare_english_chapter {"chapter": 194, "start": 1, "count": 10}
```

Use the Chinese `zh` paragraphs and stable IDs. The `translation` block describes
legacy API Burmese files; for 194 and later `available: false` and no `my` text are
expected. Do not stop for that reason and do not run `api_translate.py` or
`translate_chapters`. Verify the English bridge with `compare_english_chapter`,
then continue to the Burmese draft as described in `START.md`.

The `reference` block may contain bounded Burmese from earlier mapped chapters.
For Chinese 194 and later there is no same-chapter Burmese reference; calibrate
voice from the review and earlier style evidence. Never treat an empty reference
as a bug or fill it with API Burmese.

### 4. Check the names in the Burmese draft

```
check_names {"text": "<one Burmese draft paragraph>"}
```

Rewrite reported variants to their canonical form. This check is per paragraph,
not per chapter. Register a genuinely new recurring term only after checking that
it has no existing canonical entry.

### 5. Translate one chapter at a time

Follow the unified procedure and output contract below. The first session is
chapter 194; report and stop at its boundary. Chapter 195 is handled in a separate
session. No API budget is to be spent: all translator API tools are off limits.

---

## Names and terms — the list wins

`content/reference/EtoBnames.txt` is the authority for how a name, title, sect,
place or technical term is written in Burmese. It predates this pipeline and the
human translation was written against it.

**The rule, in one line:** if the list has a spelling, the text is rewritten to
that spelling — even when the API's spelling is also correct Burmese, and even
when the AI translation got the meaning right. Correctness is not a licence to
diverge.

Order of authority:

1. **the list**, for how a thing is written — `Ye Nin = ယဲ့နင်` means ယဲ့နင်,
   always, including in a sentence you would otherwise leave alone;
2. **the review**, for a term a human has already ruled on — the ruling is
   applied, not re-argued (the 太監 case below);
3. the Chinese source, for what the thing *is*;
4. your judgement — never, on spelling. You do not get a vote.

What that means in practice:

- **Before every `save_draft`**, run `check_names` on the Burmese draft paragraph.
  Rewrite a reported variant to `canonical`, and note the entry used:
  `check_names: လျိုကျင်း → လျိုချင်း (entry line 10)`.
- **Existing entries are never edited, and never re-derived.** If the list says
  လျိုချင်း, write လျိုချင်း. Do not improve it, modernise it, or replace it with
  another spelling because it seems preferable.
- **Two spellings for one concept is the defect this file exists to prevent.**
  The list is not innocent here: for `eunuch` it carries *both* lines 93
  `အထိန်းတော် = eunuch` and 94 `မိန်းမစိုး = eunuch`, and line 95 gives
  `မိန်းမစိုး` to `court lady` as well. The review's ruling on it: one term for
  the character, and the customary one is **`မိန်းမစိုး`**. `အထိန်းတော်` is not
  wrong Burmese, it is the wrong *person* — a woman who nurses princes — which
  is why it may stay wherever a genuine palace lady appears (ch 134,
  `အထိန်းတော်ကြီး` ဝမ်သဲ့ဟိုင်) and must not be used for 劉瑾. Apply that
  everywhere, report the duplicate in your honesty section, and invent no third
  form.
- **A list entry whose gloss is the mistranslation itself.** Line 35 is
  `holy court = တော်ဝင်တရားရုံး`, and the review's defect 2 is that 聖院 — an
  academy of saints, not a courthouse — came out as a court in ch 11 and ch 17.
  The ch 11 text reads ပြည်သူ့တရားရုံး and ch 17 တော်ဝင်တရားရုံး; the list is
  quoting that mistake, not licensing it. `Justic hall = တရားရုံး` (line 84)
  is the word for an actual court and is fine in an actual court scene. The
  list's only "school" words are temple names (lines 88, 92), so there is no
  academy term to fall back on. For 聖院: **do not coin**, do not "fix" the
  review, and do not enforce `တော်ဝင်တရားရုံး` just because the line exists.
  Flag it:

  > ⚑ 聖院 reads ပြည်သူ့တရားရုံး (ch11) and တော်ဝင်တရားရုံး (ch17). Line 35
  > glosses it `holy court = တော်ဝင်တရားရုံး`, the same mistake, and the list
  > has no academy term. I did not coin one. Needs a human ruling.

  That flag is a first-class output. A silent rename is worse than no rename,
  because it makes the next chapter inconsistent with this one.
- **A term the review settles, you apply.** You do not split the difference by
  using the right term in one paragraph and the old one in the next, and you do
  not "improve" a ruling whose reasoning you dislike.
- **Genuinely new entity, no entry anywhere?** Look first in the review's
  character table and in the reference chapter; if the human already wrote it,
  reuse that form byte-exactly. Only if it truly does not exist:

  ```
  register_name {"key": "Shen Ji", "burmese": "ရှန်းကျီ", "note": "ch194, 錦衣衛 commander"}
  ```

  Register once, at first appearance, then use that form for the rest of the
  book. Do not register a second spelling of something already listed — the
  tool will refuse, and the refusal is correct.
- **A term is not only a person.** A weapon, a martial art, a bloodline ability,
  a pill, a rank, a sect, a place — anything the reader will meet again — is
  registered the same way. `Golden Eagle Saber` is the example to keep in mind:
  it translates cleanly on its own this week, and next week the API calls it
  ရွှေလင်းတဓား, then ရွှေလင်းတ ဓား, then something else. Straightforward means
  *easy to translate*, not *safe to leave to chance*. Register it and the
  question never comes up again.
- **The entry has two sides and no category.** Use a stable English key for the
  Chinese concept (cross-check the local zh-en spelling, but do not trust a bad
  gloss) and the chosen canonical Burmese form. That pair is the record: one
  line, `Key = Value`, the same shape as the existing list.
- **Do not register terms blindly.** Notice recurring names, titles, sects,
  weapons, techniques, and places while reading the aligned Chinese and English;
  search the existing list and review first. Register only a genuinely new term
  with `register_name`.
- **A rendering the review flags but does not replace** — ch 38 uses လောင်လျို
  for `老劉`, which turns an affectionate "Old Liu" into a proper name. The
  review explains the loss and proposes nothing; the list has no entry. Keep
  the existing form, do not coin an address form, and flag it. The same goes
  for every rendering the review diagnoses without prescribing.

The only allowed persistent writes are `register_name` for a genuinely new
term, `save_draft`/`export_drafts` for Burmese drafts, and `save_verse`/
`export_verse` for the separate verse review. Do not edit `master.json`, the POS
tree, caches, Chinese source, human Burmese source, DOCX, review, English, or local
MT outputs.

---

## The source languages — do not confuse their roles

| source | where it lives | role in this task |
|---|---|---|
| **Chinese** | `content/source/chinese-0511241012-from-8011_1.txt` | semantic authority; verify both the English bridge and final Burmese against it |
| **API English** | `content/mtranslate/english.txt` | intermediate translation to assess and, if needed, correct in working context before Burmese |
| **Local English** | `content/mtranslate/zh-en.txt` | fallible Argos witness for the English quality gate; never an authority |
| **Human Burmese** | `content/source/ယဲ့နင်.txt` and `content/merged/episodes.docx`, Chinese chapters 1–193 | uncertain prior-context evidence; encoding damage includes Zawgyi-order clusters, substitutions, and dropped vowels |
| **API Burmese** | removed from this checkout | no baseline; do not recreate or call an API |

The task is Chinese → checked English bridge → **Burmese final draft**. English
comparison is a required first phase, not a separate assignment. For chapters 194
and later there is no same-chapter human Burmese reference; use the review, style
rules, canonical names, and Chinese source. Never use the damaged human Burmese as
a spelling, grammar, style, or meaning authority.

## Your job

For one chapter at a time, compare API English and local Argos English with the
Chinese. If the API English is faithful enough, use it as a bridge into Burmese. If
it is materially wrong or incomplete, correct a working English version against
the Chinese first, then translate the corrected meaning into Burmese. Recheck the
Burmese against Chinese so an English error does not propagate. Do not write
English corrections into `english.txt`; the final target remains Burmese.

The human translation stops at Chinese chapter **193**. From **194** on there is
no same-chapter Burmese reference, so calibrate voice from the review and earlier
style evidence, and use `EtoBnames.txt` for established forms. A name may never be
improvised when the list already settles it.

A translation choice should be grounded in the Chinese, the English quality gate,
the review, or a named tool result. If evidence is insufficient, flag the
uncertainty instead of inventing certainty.

## Register: the house style you are preserving

Measured across chapters 1–2 of the reference. It is consistent and deliberate.

**Narration — formal written Burmese.**
Ends on `သည်`, `မည်`, `၏`, `ခြင်း`, `ပါသည်`.
Keeps formal particles: possessive `၏`, locative `တွင်`, plural `များ`.
Connectives used sparingly: `သို့သော်`, `ထို့ကြောင့်`, `ပြီးနောက်`, `ထိုအခါ`.
Median sentence 18–27 words, up to 58. Long, subordinate, unhurried.

**Dialogue — colloquial Burmese, inside `“…”`.**
Ends on `တယ်`, `ပေါ့`, `မယ်`, `လား`, `ဘူး`, `ပဲ`, `ပါပြီ`.
May use `ရဲ့`, `တွေ`, `မှာ`.

**The two never mix inside one sentence.** Zero of 155 measured sentences do.
If a drafted narration sentence closes on `တယ်`, or a quoted line closes on
`သည်`, that is a register break — revise it toward the surrounding register,
not toward whichever form you prefer.

Do not modernise. `၏` does not become `ရဲ့`. `တွင်` does not become `မှာ`.
`များ` does not become `တွေ`. Formal sentences do not get shortened.

Reference particle counts, chapters 1 / 2 — the target distribution:

| marker | ch1 | ch2 | register |
|---|---|---|---|
| `၏` | 21 | 33 | formal possessive |
| `ရဲ့` | 0 | 0 | colloquial possessive — narration never uses it |
| `ကို` | 38 | 47 | object |
| `တွင်` | 17 | 24 | formal locative |
| `မှာ` | 7 | 6 | colloquial locative |
| `များ` | 34 | 36 | formal plural |
| `တွေ` | 6 | 4 | colloquial plural |

## The procedure, per paragraph

**Step 1 — pass the English quality gate.** Compare API English and local Argos
English against the Chinese, using `compare_english_chapter` in bounded windows.
Keep an accurate English sentence as the bridge; correct an inaccurate one in
working context before translating. Do not write corrections into `english.txt`.

**Step 2 — read prior reference context for voice and terminology.** Absorb voice,
not damaged spelling. For Chinese 194 and later there is no same-chapter Burmese
reference. Use the review and earlier style evidence; do not invent a reference.
The human Burmese may contain Zawgyi-order clusters, substitutions, or dropped
vowels. Do not copy or silently "repair" those forms; verify meaning against
Chinese.

**Step 3 — draft the Burmese from the verified meaning.** Chinese controls meaning;
the English bridge is support, not authority. Preserve the paragraph's content and
structure, apply the narration/dialogue register split, and do not omit or add
story content.

**Step 4 — run the engine on your Burmese draft.** Never feed the damaged human
reference to the segmentor. Use the tool to inspect the draft and look up only
specific uncertain spellings:

```
segment_text {"text": "<one Burmese draft sentence>"}
```

Read three things from the result:

- **token boundaries** — is the Burmese draft forming words the dictionary knows?
- **splits** — each split cluster is labelled `word`, `unit`, `loan`, or
  `unknown`. The inventory now holds all 3,215 units, Pali included, so
  `ဗုဒ္ဓ`, `ခန္ဓာ`, `ဒုက္ခ`, `သဒ္ဒါ` and `ဝိပဿနာ` come back as single tokens; a
  `loan` verdict is now rare and means a virama stack the inventory still
  cannot name. `unknown` is the only bucket that may indicate a real problem
  in the Burmese draft.
- **coverage** — characters no entry can explain. `1.0` means every Burmese
  character is accounted for by a word or a syllable.

**Step 5 — check any Burmese word you doubt.**

```
lookup_word {"word": "<the spelling as written>"}
```

The reply tells you whether it is an entry, its POS family, whether the tree
can reach it, and — when the written form is *not* a word and a repaired form
*is* — a proved repair. Only use those proved repairs. `{"verdict": "no proved
repair"}` means: leave the word alone and flag it.

**Step 6 — resolve meaning against Chinese.** When meaning is in doubt, compare
the Chinese source with the English bridge and your Burmese draft. Fix dropped,
added, or reversed meaning in the Burmese. Do not call `translate_text` or any
translator API; use the available aligned text and report unresolved ambiguity.

**Step 7 — review the Burmese, then write.** Check the author's register and
sentence shape using the review and earlier style evidence:

- Is narration formal and dialogue colloquial, without mixing the registers?
- Does the draft preserve the source's clauses, emphasis, and paragraph order?
- Are names, ranks, and cultivation terms consistent with `EtoBnames.txt`?
- Does the Burmese read naturally without flattening the author's cadence?

**Step 8 — check the names, then save.**

```
check_names {"text": "<your Burmese draft paragraph>"}
```

Rewrite every suspected variant to its `canonical` form. If the paragraph needs
a term the list lacks, register it now (once) before saving, so the next
chapter inherits it.

**Step 9 — separate verse session/pass.** Mark any poem, song, maxim,
inscription, philosophical line, or closing couplet by its stable paragraph ID.
Do not flatten it into ordinary prose. Handle those lines in a distinct
verse-focused session/pass so their imagery, parallelism, and cadence receive
separate attention. Keep the Burmese as the final target; `save_verse` records an
English review aid, not a replacement for the Burmese translation.

For each one, store an English version so the human can check the Burmese
against something readable without opening the Chinese:

```
save_verse {"chapter": 194, "paragraph": "0194-161-256fe6df", "kind": "poem",
            "english": "Even the wind has grown weary of blowing.",
            "english_source": "own",
            "note": "closes the elegy, four parallel lines"}
```

Two ways to get the English, and you say which:

- **`english_source: "mt"`** — the zh-en column, quoted as it stands. It is flat
  but literal. `python3 mt/verse.py mt 194` prints it numbered, or read
  the relevant `Chapter 194` block in `content/mtranslate/zh-en.txt`.
- **`english_source: "own"`** — your own rendering. Use it when the zh-en line
  is unreadable (poetry is exactly where a sentence-at-a-time model falls
  apart) or when the line carries a metaphor the flat version destroys.
  `"mixed"` means you quoted it and rewrote it.

Rules for this section:

- The English stored by `save_verse` is a **review aid**, not the final draft.
  Translate the verse into Burmese in the separate verse pass, save that Burmese
  with `save_draft`, and verify it against Chinese; do not use an inaccurate
  English line as semantic authority.
- Set `mt_english` whenever you used or overrode a zh-en line, so the human sees
  both the raw aid and the chosen rendering.
- Read and interpret the Chinese verse before drafting Burmese: a couplet has a
  rhythm the Burmese should preserve, and a philosophy line has a cadence a
  normal narrative sentence does not.
- If the chapter genuinely has none, say so once: `save_verse {"chapter": 194,
  "kind": "none"}`. That is different from never looking, and the section says
  which one it was.
- At the end of the chapter: `export_verse {"chapter": 194}` writes
  `content/mtranslate/verse/ch0194.verse.md` — the separate section the human
  reviews.

**Step 10 — save the fresh Burmese draft with honest provenance.**

```
save_draft {"chapter": 194, "paragraph": "0194-042-3f9a1c2b",
            "draft": "<your Burmese translation>",
            "model": "<your model name>",
            "note": "fresh Chinese-to-Burmese draft; API English checked against Chinese first"}
```

Do not invent or copy an API Burmese source into `ai_text`. Omit `ai_text` for
fresh translation. The Chinese paragraph is already stored by the draft tool; the
note records that English was used only as a checked intermediate.

## What the quality passes address

**A. English fidelity gate.** Check API English against Chinese using local Argos
as a second witness. Correct omissions, additions, reversed relations, or mistranslated
names in working context before carrying that passage into Burmese.

**B. Burmese meaning and completeness.** Translate the checked meaning faithfully;
verify the Burmese against Chinese so errors do not compound through English.

**C. Register and cadence.** Keep formal narration distinct from colloquial dialogue;
preserve clauses and rhythm instead of flattening long sentences.

**D. Terminology.** Follow `EtoBnames.txt` for names, titles, sects, and techniques.
Use `check_names`; register only a genuinely new recurring term.

**E. Orthography and segmentation.** Use `lookup_word` only for proved repairs;
`unknown` or `loan` output alone is not proof that Burmese is wrong.

## What you must not touch

- The human reference, Chinese source, DOCX, review, API English, or local MT files.
- Existing `EtoBnames.txt` entries. Append a genuinely new term only with
  `register_name`; never edit or replace an existing entry.
- `master.json`, the POS tree, or caches.
- Any English or Burmese phrase whose meaning is uncertain: flag it for the human
  rather than inventing certainty.
- The formal narration particles `၏`, `တွင်`, `များ`, or the dialogue register.

## Output contract

The final translation is Burmese. Save one Burmese draft per source paragraph with
`save_draft`; omit `ai_text` because there is no API-Burmese source. Keep stable
paragraph IDs and export the chapter draft with `export_drafts`. In the response,
return the Burmese translation (or its exported draft location), a concise note on
any corrected English bridge passages, registered names, verse handled separately,
and unresolved questions. Do not return an English-only report as the final result.

## Working method

1. Work one chapter per prose session; use bounded source and comparison windows.
2. Read `review_brief`, the chapter's `review_lookup`, and the names list before
   drafting.
3. Complete the English quality gate against Chinese; keep any correction only in
   working context.
4. Draft Burmese from the checked meaning; verify each passage against Chinese.
5. Run `check_names`; use `segment_text` and `lookup_word` for Burmese draft QA.
6. Save with `save_draft` without a fabricated `ai_text`; export with
   `export_drafts`.
7. Handle poems, songs, maxims, and philosophical lines in a separate verse
   session/pass. Use `save_verse`/`export_verse` for the separate review aid.
8. Stop at the requested chapter boundary. Report any unverified choice explicitly.

## Honesty clause

Every turn, state how many paragraphs were compared and translated, whether any
English bridge corrections were needed, how many names were registered, which
verse lines were reserved or completed separately, and anything unresolved. If a
claim could not be checked with a tool, say "unverified".

---

## Tools (MCP, this repo)

| tool | use |
|---|---|
| `review_brief` / `review_lookup` | read the novel review and chapter-specific context |
| `compare_english_chapter` | aligned windows of Chinese, local Argos English, and retained API English |
| `read_chapter` | bounded Chinese paragraphs, stable IDs, prior Burmese reference, and translation status; missing API `my` is expected |
| `previous_burmese_context` | bounded prior Burmese keyword hits, with encoding caution |
| `lookup_name` / `check_names` / `register_name` | canonical Burmese terms and controlled additions |
| `segment_text` / `lookup_word` | Burmese draft QA and proved spelling repairs |
| `save_draft` / `export_drafts` | store and export fresh Burmese drafts; omit `ai_text` |
| `save_verse` / `export_verse` | separate verse review aids for poems, songs, maxims, and philosophy |

Do not call `translate_text`, `translate_batch`, or `translate_chapters`: this
workflow uses the retained English files and local read-only tools, not an API.

Chapter/source window:

```
read_chapter {"chapter": 194, "start": 1, "count": 10}
compare_english_chapter {"chapter": 194, "start": 1, "count": 10}
```

Fresh Burmese draft (no false API source):

```
save_draft {"chapter": 194, "paragraph": "0194-042-3f9a1c2b",
            "draft": "<Burmese translation>", "model": "<agent>",
            "note": "Chinese checked; API English used as corrected intermediate"}
export_drafts {"chapter": 194}
```

## Self-check before finishing a chapter

- [ ] `review_brief` and the relevant `review_lookup` were read
- [ ] API English and local Argos English were compared against Chinese in aligned windows
- [ ] any English correction stayed in working context; no file was overwritten
- [ ] Burmese was drafted from checked meaning and verified against Chinese
- [ ] absence of API Burmese `my` was not treated as a blocker
- [ ] every name follows `EtoBnames.txt`; new terms alone were registered
- [ ] the damaged human reference was not fed to `segment_text` or treated as authority
- [ ] Burmese narration/dialogue registers remain distinct
- [ ] verse lines were handled in their separate pass and exported separately
- [ ] drafts were saved without fabricating `ai_text`
- [ ] no API, source, English, MT, dictionary, POS tree, or cache files were modified
