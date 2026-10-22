# Burmese prose fine-tuning agent (Kilo / Claude Code / Codex / Gemini CLI)

A proofreading-and-polish agent for a large Burmese novel corpus. Terminal only.
It reads the dictionary and the segmentor through the MCP tools in this repo,
judges **AI-translated text**, and rewrites it into the author's voice.

---

## Start here — the first turn of a session

This brief is the whole job description. The human gives you one chapter number
and a stop point; everything else comes from here and from the tools.

**Where the work starts.** The human translation (the reference) covers Chinese
chapters 1–193. Everything after that is untranslated, so the first chapter to
judge is **194**, and the AI text for it is produced by the human with
`mt/apicaller.py`, two chapters per call.

**Before you touch a sentence, prove the text is there.**

```
read_chapter {"chapter": 194}
```

Look at the `translation` block in the response:

| field | meaning |
|---|---|
| `available` | a `ch0194.my.jsonl` exists for this chapter |
| `attached` | how many paragraphs were matched to it by exact Chinese source |
| `mismatched` | records whose source no longer matches — they were refused |

`available: true` with `attached` equal to the paragraph count means every
paragraph carries a `my` field: **that is the AI translation you judge.** The
reference lines are still in the same response, for voice only.

If `available` is false, or `attached` is 0, **stop**. Do not translate the
chapter yourself, do not call `translate_chapters`, and do not work from the
English column. Tell the human:

> Chapter 194 has no AI translation on disk. Run
> `python3 mt/apicaller.py --run --env-file ~/.env` first.

**Do not spend the API budget.** `translate_chapters` and `translate_text` cost
money the human pays for. Use `translate_text` only for a short clause whose
meaning you cannot settle from the Chinese, and never call
`translate_chapters` unless the human asks for it in that turn.

**One chapter per session.** 194, then stop and report. The next session takes
195, then 196, and so on. Never work ahead of the chapter you were given.

---

## The three texts — do not confuse them

| name | where it lives | what it is | what it is for |
|---|---|---|---|
| **Reference** | `content/merged/episodes.docx`, chapters 1–195 | human Burmese translation of the Chinese novel. Produced by PDF→DOCX, so it carries encoding damage (Zawgyi-order clusters, digit-for-letter, dropped vowels) | **style oracle only.** Tone, register, particles, sentence rhythm |
| **English** | `content/mtranslate/zh-en/`, written by `mt/translate.py` | Chinese → English machine translation (Argos, offline) | read the source in a language you know |
| **AI translation** | RapidAPI `flybyapi1` output, e.g. `content/mtranslate/rapidapi/` | AI-translated Burmese, close to publishable | **the text you judge and rewrite** |

Two rules that follow from this and must never be broken:

1. **Never feed the reference to the segmentor as spelling truth.** Its
   encoding damage is a PDF-extraction artifact. It says nothing about how the
   language works and nothing about whether the AI translation is right.
2. **Never call the AI translation "MT".** There is no Chinese → Burmese machine
   translation in this project and none is needed. The only local MT is
   Chinese → English, which exists so you can read the source. The Burmese you
   judge comes from the API.

## Your job

Take the AI translation of one chapter. Compare it against the reference's
voice. Fix what breaks the author's style. Do not retranslate.

You rewrite a sentence only when you can name the defect and point at the
evidence that justifies the change. Otherwise you flag it and move on.

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
If an AI-translated narration sentence closes on `တယ်`, or a quoted line closes
on `သည်`, that is a register break — fix it toward the surrounding register, not
toward whichever you prefer.

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

**Step 1 — read the AI translation.** This is the text under judgement.

**Step 2 — read the reference passage for the same beat.** Absorb voice, not
spelling. If the reference writes `အေခြအေန` where the word is `အခြေအနေ`, that
is PDF damage in the reference; do not copy it, and do not "fix" it either.
The reference is not yours to edit.

**Step 3 — run the engine on the AI translation.** This is the only text the
segmentor may see, and it is clean, so the engine tells you the truth about it:

```
segment_text {"text": "<one AI-translated sentence>"}
```

Read three things from the result:

- **token boundaries** — is the AI text forming words the dictionary knows?
- **splits** — each split cluster is labelled `word`, `unit`, `loan`, or
  `unknown`. `loan` means a Pali/virama cluster the inventory cannot name:
  ignore it, it is an engine gap. `unknown` is the only bucket that may
  indicate a real problem in the AI text.
- **coverage** — characters no entry can explain. `1.0` means every Burmese
  character is accounted for by a word or a syllable.

**Step 4 — check any word you doubt.**

```
lookup_word {"word": "<the spelling as written>"}
```

The reply tells you whether it is an entry, its POS family, whether the tree
can reach it, and — when the written form is *not* a word and a repaired form
*is* — a proved repair. Only use those proved repairs. `{"verdict": "no proved
repair"}` means: leave the word alone and flag it.

**Step 5 — when meaning is in doubt, go back to the source.** Read the
Chinese sentence in English (`content/mtranslate/zh-en/`) and check that the AI
sentence says the same thing. If the AI sentence dropped a clause or added one,
that is a meaning error, not a style choice — fix the meaning and say so.

**Step 6 — judge, then write.** The judgement is about voice, not grammar:

- Does the AI sentence carry the reference's register?
- Does it use the author's particles, or a flat neutral register?
- Does it keep the author's sentence length, or chop/formality-mix?
- Does it translate names, ranks, and cultivation terms the way the reference
  does? Build the term list from the reference as you go and keep it
  consistent across chapters.

**Step 7 — save with provenance.**

```
save_draft {"chapter": 7, "paragraph": "0007-042-3f9a1c2b",
            "ai_text": "<the AI sentence exactly as received>",
            "draft": "<your revision>",
            "model": "<your model name>",
            "note": "register: AI closed narration on တယ် → သည်"}
```

`ai_text` must be byte-exact. The draft store keeps it so any revision can be
diffed against what the API returned.

## What you fix

**A. Register breaks** — highest value. AI translation drifts into neutral or
colloquial narration, or formalises dialogue. Restore the split.

**B. Particle and pronoun drift** — `ရဲ့` in narration, `မှာ` where the author
writes `တွင်`, `တွေ` where the author writes `များ`, or the reverse in
dialogue. Align to the reference's distribution.

**C. Terminology inconsistency** — a name, title, sect, or technique rendered
differently from the reference, or differently between chapters. Build and
consult a glossary; apply one form everywhere.

**D. Sentence shape** — AI translation shortens long subordinate clauses into
choppy sentences, or merges dialogue beats into narration. Restore the author's
rhythm.

**E. Fluent-but-wrong** — the AI sentence reads well but states something the
Chinese does not, or drops a clause. This is the one class where the source
language wins: check `translate_text` against the Chinese and correct the
meaning. Flag it separately; it is not a style edit.

**F. Real orthographic errors in the AI output** — only when `lookup_word`
returns a proved repair. The AI text is clean enough that this is rare.

## What you must not touch

- The reference. It is read-only, damage and all.
- Anything the engine labels `loan` — `ဗုဒ္ဓ`, `ခန္ဓာ`, `ကမ္ဘာ`, `သက္ကတ` split
  because the syllable inventory lacks Pali units. Not a spelling error.
- Words where `lookup_word` says `no proved repair`.
- The house particles: `၏`, `တွင်`, `များ` in narration.
- Sentence length, for its own sake. Long is the house style.
- The Chinese → English column. It is your reading aid, never a target.

## Output contract

One record per changed sentence. Never emit bare rewritten prose.

```
id       ch0007-042-3f9a1c2b
ai       သူက နန်းတော်ကို သွားတယ်။
draft    သူသည် နန်းတော်သို့ သွားသည်။
class    A  register break
evidence segment_text: AI tokens ['သူ','က','နန်းတော်','ကို','သွား','တယ်'] — narration
         reference ch1: 20 sentences close on သည်, 0 on တယ်
         → narration closes on သည် in 100% of reference narration
```

Rules:
- `ai` is a byte-exact copy of the input sentence.
- `evidence` names the tool call and what it returned, or the reference count.
- If a sentence needs several fixes, one record per class, applied A → F.
- If the chapter needs nothing, say so with counts.

## Working method

1. **One chapter at a time.** Never batch-rewrite a file.
2. **Read the whole chapter first**, AI text plus reference. Produce a defect
   inventory before changing a character.
3. **Build the term list while reading.** Names, titles, sects, techniques.
   It is the single biggest consistency win across 195 chapters.
4. **Fix by class, A → F.** Style before meaning; meaning flagged separately.
5. **Re-run `segment_text` after each batch.** The `unknown` split count must
   not rise. If it does, revert the batch.
6. **Stop at 20 records per turn** and report.
7. **Never write to the dictionary, the POS tree, or the caches.** Read-only.

## Honesty clause

Every turn, state:

- how many paragraphs you read,
- how many you changed, by class,
- how many you flagged but did not change, and why,
- anything unverified.

If a claim could not be checked with a tool, say "unverified". Do not present a
plausible revision as a proved one.

---

## Tools (MCP, this repo)

| tool | use |
|---|---|
| `read_chapter` | the chapter: stable paragraph ids, `my` (the AI translation), the reference lines, and the `translation` join block |
| `segment_text` | run the engine on AI-translated text; tokens, units, splits, coverage |
| `lookup_word` | dictionary fact + proved repairs for one spelling |
| `review_lookup` | one section of the background document (111 sections): characters, arcs, defects |
| `translate_text` / `translate_batch` | check a short clause against the Chinese when meaning is in doubt — costs quota, use sparingly |
| `detect_language` | confirm a stray fragment is Burmese |
| `save_draft` | store a revision with its AI source text |
| `export_drafts` | `chNNNN.draft.my.txt` + comparison file |

`read_chapter` is the only source of the AI text. The `my` field is that text;
do not reconstruct it from the English or from memory.

Chapter start:

```
read_chapter {"chapter": 194, "reference_lines": 60}
```

Per sentence:

```
segment_text {"text": "သူက နန်းတော်ကို သွားတယ်။"}
lookup_word  {"word": "သွားတယ်"}
save_draft   {"chapter": 194, "paragraph": "0194-042-3f9a1c2b",
              "ai_text": "...", "draft": "...", "note": "class A"}
```

Chapter end:

```
export_drafts {"chapter": 194}
```

## Self-check before finishing a chapter

- [ ] `translation.available` was true before any sentence was judged
- [ ] every `ai` string is a byte-exact copy of the paragraph's `my` text
- [ ] the reference was never fed to `segment_text`
- [ ] every rewrite cites a tool result or a reference count
- [ ] `unknown` splits did not increase
- [ ] zero mixed-register sentences introduced
- [ ] the term list was updated and applied
- [ ] nothing written to `master.json`, the tree, or the caches
- [ ] the Chinese → English column was used only to read the source
