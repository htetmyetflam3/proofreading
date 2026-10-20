# Open items — review of `input/ယဲ့နင်1-200.txt`

Kept here so none of these get lost in chat. Nothing in this file is a
verdict on the translation; it is a list of things that are still open, plus
one flag I am withdrawing.

Status: written during part 9 of `output/review/burmese-overview.md`
(Burmese chapters ၈၁–၉၀).

---

## 1. The `311fc21` encoding note was never answered

Commit `311fc21` added a paragraph to the review saying that the odd
spellings in the input — `ဇကရာဇ်`, `အေစခံ`, `အေတွ်း`, `ဖြောင့်မတ်`,
`ကျီမင်ယွဲ့`, `၄၄၃`, `ဝေ့၀ူဟွေ့` — are artefacts of the file's encoding,
not the translator's choices, and that they are therefore not scored as
errors anywhere in the review.

That paragraph has not been confirmed or rejected by you. It stays as
written, and every part after it is written on that assumption. If the
assumption is wrong, say so once and I will re-read the affected lines.

## 2. The Chinese side was missing — now we have a source

**What was missing.** The repo only ever contained
`input/chinese-0511241012-from-8011_93.txt`, i.e. Chinese from chapter 193
onward. There is no Chinese for chapters 1–192 in any commit, in
`refs/pull/3/head`, or in `output/merged/*` (those files pair Chinese 193
with Burmese chapter 1, so their Chinese column is unusable as evidence).
The full Chinese text used for the earlier parts is gone; it lived in a
temporary file that no longer exists.

**The source you gave.** `https://www.novel543.com/0511241012/`
《再不讓我死，我就真無敵了》, author 勤奮碼字人 — 408 chapters + 大結局.
Chapter URL pattern:

    https://www.novel543.com/0511241012/8011_<chapter>.html

e.g. `8011_81.html` is chapter 81. This matches the name of the file
already in the repo (`...from-8011_93.txt` = chapter 93), so numbering is
one-to-one with Chinese chapter numbers.

**Consequence for the review.** Parts 1–8 were written with the Chinese in
front of me; part 9 onward can be too, once chapters 81–90 are pulled from
that site. Until then, any statement about the Chinese in this file or in
the review is marked as unavailable rather than guessed.

## 3. Withdrawn: the "duplicated passages" flag

Earlier I flagged apparent duplication between the chunks for Burmese
chapters ၈၅/၈၆ and ၈၇/၈၈ and put it down to PDF page overlap in the
pre-fix parser.

**It is not there.** Checked directly: exact paragraph comparison between
consecutive chunks (080→081, 081→082, 082→083, 083→084, 084→085, 085→086,
086→087) returns zero repeated paragraphs, and the ၈၇→၈၈ boundary is one
continuous scene (ch. 87 ends on 木甫清's son drawing the family sword;
ch. 88 opens with 木甫清 shouting "တော်လောက်ပြီ"). The two halves are the
same quarrel continuing, not the same text twice.

So there is nothing here for the parser to fix, and nothing to score. The
flag is withdrawn.

## 4. Still needs the Chinese before part 9 is written

These are questions that only the Chinese can settle. Listed so they are
not answered by guessing:

- `တော်ဝင်သစ်တော စစ်တပ်` (ch. 81) — the name reads "royal forest army",
  but the same passage describes the corps as palace guards and the
  emperor's personal bodyguard. Is the original name a guard unit whose
  characters were taken literally, or is it a forest corps? Plot effect:
  none (backstory only).
- `တည်ထောင်သူဖခင်မျိုးဆက်` (開國公, ch. 87–88) — the Burmese uses the same
  phrase for the living duke and for his first-generation ancestor
  (`ပထမမျိုးဆက်၏ တည်ထောင်သူဖခင်သည်`). Whether that ambiguity is in the
  Chinese or introduced by the translation changes how the father–son
  scene reads, and that scene is the strongest thing in the unit.
- `ချင်းယွီနန်းတော်` / `ချွင်းယီ` / `ကျောက်စိမ်းနန်းတော်` (ch. 87) — the
  women-only sect from part 7 appears under another name. This chapter
  does gloss it (`ချင်းယွီ(ကျောက်စိမ်း)နန်းတော်`) and restates the
  women-only rule, which is the only thing that lets a reader tie it back
  to 群玉閣. Worth confirming the characters.

## 5. Not open, just noted so it is not re-opened

- Paragraph-level encoding damage (`သားအဖြကား`, `ဉပေဒေ`, `မြေပါ်ပစ်`,
  `အေဖ`) — same class as item 1. Not scored.
- `ဝူစန်းစစ်` / `ဝူဆန်းစစ်` inside one chapter — same class. Not scored.
