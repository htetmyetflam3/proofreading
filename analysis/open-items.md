# Open items — review of `input/ယဲ့နင်1-200.txt`

Kept here so none of these get lost in chat. Nothing in this file is a
verdict on the translation; it is a list of things that are still open, plus
one flag I am withdrawing.

Status: written during part 9 of `output/review/burmese-overview.md`
(Burmese chapters ၈၁–၉၁, Chinese 80–90). Updated after part 9 was
written, so that nothing here contradicts the review.

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
《再不讓我死，我就真無敵了》, author 勤奮碼字人. It is readable from here —
I opened the index, the 目錄, and one chapter page.

**But the page number is not the chapter number.** I checked, and it is
easy to get this wrong:

- `8011_81.html` does **not** open chapter 81. It opens 第一百五十二章 to
  第一百五十四章 (ch. 152–154).
- Each page carries two to four chapters, and some pages split into
  `_2` continuations (`8011_81_2.html`).
- The 目錄 labels the pages by the chapter they *end* on. The run in our
  range is: page 66 → 81, 67 → 85, 68 → 87, 69 → 89, 70 → 91.

So to get the Chinese behind Burmese ၈၁–၉၀ (Chinese 80–89 under the +1
offset established in part 8), the pages to pull are roughly **65–69**,
and the chapters have to be located by their headings inside the page, not
by the URL.

**One more thing worth knowing.** The 目錄 jumps from 第五十八章 straight
to a page labelled `61`, with no 59 or 60. The site itself is missing
chapters there. Since our input is likewise one chapter ahead of the
Chinese, it is worth keeping in mind that the offset may partly come from
a dropped chapter rather than from the translation — I am not asserting
that, only noting that both texts have a gap in the same region.

**Consequence for the review — updated.** This section used to say that
nothing in the review for chapters ၈၁–၉၀ claimed anything about the
Chinese. That is no longer true, and it should not be left standing:
the pages for 中.78–90 have since been pulled, so part 9 does quote the
Chinese where it matters (十二個時辰, 升仙丹, 孤忠劍, 玉簡, 都頭, the
武戰 → 武三思 pun).

What that means in practice, so the two files agree:

- Where part 9 quotes Chinese, the quote came from page text pulled for
  this unit, not from memory of an earlier part.
- Where part 9 does *not* quote Chinese, it is because the point is
  visible in the Burmese alone (name drift, the chapter headers, the
  玉簡 → hairpin substitution at the object level).
- The 目錄 offset is still a live trap. `8011_81.html` opens 中.152–154.
  Never locate a chapter by the number in the URL.

**One thing I can no longer check.** The pages pulled for 中.80–90 name
the 開國公 沐倫. The Burmese is `မူဖုချင်`, which reads much closer to a
「沐甫清」-type name than to 沐倫. Either the page text I recorded has the
wrong characters, or the Burmese transliteration is loose. The review
refers to him only as `မူဖုချင်` for that reason. Recorded here so it is
not silently "settled" later.

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

## 4. Part 9 questions that the Chinese has now answered

These were listed as unanswerable without the Chinese. Three of the four
are now settled, and the answers are in part 9:

- `တော်ဝင်သစ်တော စစ်တပ်` (ch. 81) — 御林軍. It is a palace guard corps,
  not a forest corps. 林 here is part of the guard unit's name, and the
  passage around it says plainly that these men are the emperor's
  bodyguard and the keepers of palace discipline. So the Burmese reads
  "royal forest army" where the text means the household guard.
  Plot effect: none — backstory only — but it is the kind of name a
  reader carries forward, because the same corps dismisses 武三思.
- `ချင်းယွီနန်းတော်` / `ကျောက်စိမ်းနန်းတော်` (ch. 87) — 群玉閣. The
  women-only sect from part 7, under a second and then a third Burmese
  name. The chapter's own parenthesis `ချင်းယွီ(ကျောက်စိမ်း)နန်းတော်` is
  the only thing that lets a reader tie the three together.
- `တည်ထောင်သူဖခင်မျိုးဆက်` (開國公) — the Burmese does use one phrase for
  the living duke and for the first-generation ancestor. The father–son
  scene leans on exactly that ambiguity: the title is inherited, and the
  son's argument is that inheriting it is not the same as deserving it.
  So the ambiguity is load-bearing, not damage.
- `မူဖုချင်` / 沐倫 — still open; see the note at the end of section 2.

## 5. Not open, just noted so it is not re-opened

- Paragraph-level encoding damage (`သားအဖြကား`, `ဉပေဒေ`, `မြေပါ်ပစ်`,
  `အေဖ`) — same class as item 1. Not scored.
- `ဝူစန်းစစ်` / `ဝူဆန်းစစ်` inside one chapter — same class. Not scored.
