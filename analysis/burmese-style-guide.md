# Burmese translation style guide — for whoever edits next

This is the reference for the Burmese in `input/ယဲ့နင်.txt` and for any prose
written about it (the review, the notes). It records what the translator
actually does, where the habit breaks, and which "errors" are not the
translator's fault. Everything below was counted in the file; the command that
produced a number is next to it where the number is easy to misread.

Read in this order: §1 register → §6 damage-vs-error → §9 do-not list.

---

## 1. Register: two registers, one book

Narration is **formal literary Burmese**. Dialogue is **colloquial**.

Whole file: `ဖြစ်သည်` 2,891 / `ဖြစ်တယ်` 85 · `ခဲ့သည်` 1,480 / `ခဲ့တယ်` 204.

That ratio holds in every band, so it is a deliberate split, not drift:

    prose    သူ နန်းတော်သို့ ဝင်ရောက်လေသည်။ မည်သူမျှ မတားဆီးနိုင်ပေ။
    dialogue "မင်း ဘာလို့ ဒီလို လုပ်တာလဲ" သူ မေးလိုက်တယ်။

Rules that follow from it:

- When **quoting**, never "fix" the register. `ဖြစ်လေသည်` inside a quote stays.
- When **writing about** the book, match the narration: formal, third person,
  `သည်/ပြီး/သော`. Do not write the review in the dialogue register.
- The review's own voice uses `ကျွန်တော်`, not `ငါ`. `ငါ` belongs to characters.
  (Four slips of this kind were found and fixed in the review.)

Second register fact: narration is **old-fashioned**, not modern journalistic.
It uses `သို့သော်` (1,491), `ထို့ကြောင့်` (105, printed `ထို့ကောင့်`),
`သို့ဖြစ်ရာကား`, `ဤ`, `၎င်း`. A modern rewrite (`ဒါပေမဲ့` throughout) changes
the book's texture. If you must simplify, simplify only inside the review.

## 2. Line mechanics

- The text was lifted from a PDF, two columns, so lines break at a median of
  40 characters (p90 = 51). A paragraph is one long `\n`-separated run.
- Page furniture is inline: `--- Page 1234 ---`. Any script that counts
  sentences must strip these first, or every page boundary becomes a sentence.
- Sentence end: `။`. Clause break: `၊`. Ellipsis is the single glyph `…`
  (563 uses), never three dots.
- Quotation marks sit tight against the text: `"စကား"` with no space inside.
- Em dash `—` does not appear as punctuation in the source (0 uses); where the
  review uses `—`, that is the review's own mark, not the translator's.

## 3. Quote style is not stable — and that is evidence

Curly `“ ”` vs straight `" "` by band (counted per chapter range):

| band | curly | straight |
|---|---|---|
| 1–60 | 1,190 | 428 |
| 61–120 | 1,923 | 2,811 |
| 121–140 | 601 | 180 |
| 141–170 | 41 | 1,949 |
| 171–195 | 93 | 1,302 |

Two flips: around ch 61 and again around ch 141 (with a curly pocket at
121–140). The likeliest reading is that the translated text was assembled from
more than one source pass. **Do not normalise the quote marks.** They are the
cheapest evidence of where the seams are, and any bulk replace destroys it.
Single quotes `‘ ’` (1,237) are the translator's inner-quote / aside marker.

## 4. Names: adopt the dominant form, never invent one

The same character carries two to four spellings. The dominant form and the
stragglers, counted in the file:

| Chinese | use this | also appears | count |
|---|---|---|---|
| 姬明月 | `ကျီမင်းယွဲ့` | `ကျီမင်းယြွိုဲ့`, `ကျီမင်ယွဲ့` | 571 / 197 / 31 |
| 張承宗 | `ချိုက်ရှန်ကောင်း` | `ချိက်ရှန်ကောင်း`, `ချိက်ရန်ကောင်း` | 447 / 16 / 30 |
| 柳慎 | `လျိုရှမ်` | `လျိရမ်` (only ch 181+) | 99 / 19 |
| 柳倩 | `လျိုချင်း` | `လျိချင်း` (ch 181+) | 220 / 13 |
| 裴語涵 | `ဖေးယွီဟန်` | `ဖေးယွိဟန်`, `ဖေယွီဟန်` | 415 / 14 / 4 |
| 蕭淺淺 | `ရှောင်ချန်းချန်း` | `ရောင်ချန်းချန်း`, `ရှောင်ချင်းချင်း` | 224 / 23 / 21 |
| 賀元一 | `ဟဲရွမ်` | `ဟဲယွမ်` | 95 / 3 |

Working rules:

1. Use the dominant form. Note the variant in `analysis/open-items.md`; do not
   silently rewrite the body text.
2. If two characters share a variant (`လျိရမ်` covers both 柳慎 and, in one
   chapter, a different official), flag it — do not guess.
3. Never retransliterate from pinyin. The book's convention is Burmese-script
   approximation of the Chinese reading, not Mandarin romanisation.
4. New names introduced by the review keep the Chinese in parentheses on first
   use, then Burmese only.

## 5. Terminology: the rendering in use, and the ones that are wrong

The translator's fixed renderings (use them; they are consistent):

| Chinese | Burmese in this file |
|---|---|
| 監察院 | `ကြီးကြပ်ရေးရုံး` |
| 監正 | `ကြီးကြပ်ရေးမှူး` |
| 文膽 | `ပညာရှိသတ္တိ` |
| 煙雨樓 | `မြူမိုးစံအိမ်` |
| 玉簡 | `ကျောက်စည်းဆံထိုး` |
| 赤焰軍 | `မီးလျှံနီစစ်တပ်` |
| 四大神將 | `နတ်မင်းလေးပါး` |
| 不朽宗 | `အင်မော်တယ်ဂိုဏ်း` |
| 大理寺 | `တော်ဝင်တရားရုံးတော်` |
| 藏經塔 | `စာပေတာင်` |

**Wrong but entrenched** (fix the meaning, keep the wrong wording only when you
are quoting the translator verbatim):

- `聖院` → `တရားရုံး` / `တော်ဝင်တရားရုံးတော်` (227 / 174). It is the Academy of
  Sages, not a courthouse. The error changes the plot: ch 17 becomes a trial
  instead of an examination, so a reader expects the wrong scene.
- `五體投地` → `ဒြပ်စင်ငါးပါး` ("five elements"). It is a prostration idiom.
- `太監` is split across two renderings, `မိန်းမစိုး` (67) and `အထိန်းတော်` (97).
  Both are used for the same office; a reader can take them for two castes.

## 6. Damage vs translator error — decide before you edit

The file carries OCR substitution damage in five families. None of it is the
translator's mistake, and none of it should be "corrected" by reading.

    သ့    → သူ့      သတို့ → သူတို့     ဆကီး → ကြီး
    ိုံ   → ုံ        ငမွိ  → မြို့      ငက   → ကြ
    ကကီး  → ကြီး     မေပြာ → မပြော     တြွေ့ → တွေ့

Decision order:

1. Is the word in the damage list? → it is damage, repair it, do not discuss it
   as a translation choice.
2. Is it a real word that happens to look damaged (`ကိရိယာ`, `ပရိသတ်`,
   `ဆကိ`, `လျိချင်း`)? → leave it. See the trap list below.
3. Neither? → it may be a translator choice. Quote the Chinese before calling
   it an error.

Two traps, both already burned:

- `ရိ` → `ရှိ` must be suffix-anchored. Blanket replacement corrupts
  `ကိရိယာ`, `ပရိသတ်`.
- `ေကြာ` → `ကြော` must never fire after a medial. Blanket replacement turns
  `တွေကြား` into `တွကြေား`.

**Never run `analysis/normalise_spelling.py` on `output/review/burmese-overview.md`.**
The review quotes the damaged forms on purpose, as evidence. A test run
corrupted 15 lines before this rule was written down.

## 7. Known translator errors, by chapter

| ch | what | why it matters |
|---|---|---|
| 4 | 她 used for the emperor, then 他 | faithful to the twist, but reads as a typo; the review says so |
| 11, 17 | 聖院 rendered as a courthouse | scene misread (see §5) |
| 1–4 | 太監 as two different words | two names for one office |
| 123–137 | chapter headings left in English (`Chapter – 123`) | search fails; the review documented this and corrected an earlier claim of "no headings" |
| 86 | 572 recruits rounded to "over five hundred" | the number is a plot marker |
| 152 | `တစ်ဆယ့်သုံးခု` printed as `တစ်ဆယ့်သိုံးခို` | damage, then misread as sixteen |

## 8. Polish checklist for the next editor

1. Strip `--- Page N ---` before any sentence or word count.
2. Count `ဖြစ်သည်` against `ဖြစ်တယ်` in anything you write; if the ratio
   approaches 1:1 you have written the review in the wrong register.
3. Every quoted line: compare against the normalised file, not from memory.
   Paste; never recall.
4. Every "မူရင်းက …" claim: state which chapter can actually be checked against
   a Chinese text. In this repo only ch 193–195 overlap.
5. Names: dominant form only, variants into `open-items.md`.
6. Do not touch quote-mark style.
7. Keep `၊` and `။` as the translator uses them; do not re-punctuate quotes.
8. Numbers: keep Burmese numerals in Burmese prose, Arabic only inside a Chinese
   title or a file name.
9. If a term's meaning was wrong in the source, fix the review's explanation and
   leave the source wording alone.
10. New findings go to `analysis/open-items.md` with the chapter number.

## 9. Do not

- Do not segment Burmese into syllables. The review's units 1–8 arrived that
  way and read as if a machine typed them; it took a hand pass per unit to undo.
- Do not bulk-replace a Burmese string across the book. Two attempts (see §6)
  both corrupted correct words; `str.replace` fails silently.
- Do not "modernise" the narration. The formality is the translator's voice.
- Do not put English in the review body except when quoting a source heading.
- Do not treat `analysis/normalise-report.json` counts as a quality score; they
  count repairs, not remaining errors.

## 10. File map

    input/ယဲ့နင်.txt                     source, read-only, ch 1–195, 4414 pages
    input/ယဲ့နင်.normalised.txt          derived, damage repaired (gitignored)
    analysis/normalise_spelling.py       the repairer; --chain adds the ေ/ာ pass
    analysis/normalise-report.json      per-rule counts from the last run
    analysis/damage-scan.json           damage per chapter, the dirty bands
    analysis/open-items.md              unresolved questions, by unit
    analysis/review-self-audit.md       what is wrong with the review file
    output/review/burmese-overview.md   the review (source of truth)
    output/review/*.yaml, *.txt         rendered from it, regenerate, never edit
    analysis/glossary.json              machine-readable terms, names, damage
