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

## 6. Part 10 (ch. 92-101) — what the Burmese file cannot answer

- **煙雨樓 capital branch leader.** In ch. 92 沈三變 reports to 木先生, but
  the decisions are made by a second, older voice in the same room whom
  沈三變 calls `အုပ်ချုပ်သူ` (the chief). No name, no second appearance in
  this unit. Either a character the Chinese names and the Burmese drops,
  or a deliberate anonymity. Cannot be settled from the Burmese alone.
- **`နယ်စားရုန်` (ch. 101).** A marquis whose family has just been killed,
  addressed by a name that appears nowhere else in the file. Almost
  certainly the same man the Burmese elsewhere calls `ဝေ့ဝူဟွေ့`
  (威武侯), but "ရုန်" has no source in anything visible here.
- **`မူဖုချင်` / 沐倫 — resolved as a name collision, not a fix.** Ch. 87
  establishes that the duke (開國公) is *not* 木先生 of 煙雨樓: the duke
  returns to the 沐 mansion under the 開國公 plaque, while 木先生 receives
  沈三變 in the ruined 煙雨樓 courtyard in the same chapter. The Burmese
  still spells both "မူ", so the two men stay fused for a Myanmar reader.
- **Chapter headings are unreliable as an index** (this supersedes the
  earlier note about missing titles for 中.84/87/88/89/90): chapters 84
  and 186 have no heading at all; 51-57, 66, 68, 100, 101, 117 and 162
  are headed `အပိုင်း` instead of `အခန်း`; ch. 94 uses Latin digits
  (`အခန်း94`); 59 and 60 appear twice. **Correction (part 13): 123-137
  were never missing** — all fifteen are headed in English (`Chapter –
  123` … `Chapter 137`), with the dash varying between en dash, hyphen
  and nothing at all (131 and 135 have no dash). The earlier "missing"
  claim came from a regex that only accepted one dash form.

## 7. Part 11-12 (ch. 112-121) — open and closed

- **冷十七 → `အေးစက်ခြင်း ၁၇`** (closed as a finding, open as a fix):
  the assassin's code-name is rendered as a phrase meaning "coldness
  seventeen" and repeated as such in ch. 121. Ch. 110's reveal — the
  killer recognises his own teacher — depends on the reader hearing a
  *name*, so the rendering does real damage there.
- **`ဘုရင်ဟွေ့` (ch. 118)** — a mad royal who used to be crown prince,
  now inviting Ye Ning. Cannot be tied to anyone in the Burmese cast:
  the ruler in this book is `ကျီမင်းယွဲ့`, and the only other `ဟွေ့` is
  the marquis `ဝေ့ဝူဟွေ့`. Whether the Burmese has flattened two
  different characters (献/侯) into one syllable, or the Chinese
  introduces a separate mad prince, needs the Chinese.
- **`ချွေးပေါက်ပေါင်း ၄၈,၀၀၀` (ch. 120)** — the standard Buddhist
  figure is 84,000 (八萬四千). The Burmese says 48,000, i.e. the digits
  transposed. No Chinese for this chapter in the repo, so recorded as
  probable, not proven.
- **`ကောင်းကင်နတ်ဆိုးကျင့်စဉ်` (ch. 119-120)** — 天魔功. Written
  consistently, and the comparison to 北冥神功 (`ပေမိန်နတ်သိုင်း`) is
  preserved, so this one is working.

## 8. Part 13-14 (ch. 122-141) — open and closed

- **`[[HCRAWLER MARKER n]]` is a boundary, not a chapter number.** From
  marker 102 onward the marker index runs two ahead of the chapter
  heading (marker 124 = ch. 122, marker 143 = ch. 141). Cause: chapters
  59 and 60 are each split in two in the file ("အခန်း (၅၉) ၁", "(၅၉) ၂",
  "(၆၀)", "(၆၀) ၂"). Read boundaries off the headings, or subtract 2.
  Part 13 was first drafted from marker numbers as if they were chapter
  numbers and had to be thrown away and rewritten from the right
  offsets — don't repeat that.
- **The file has glyph-level corruption independent of the translator.**
  A regular `ကြ`/`ကြီ` ligature failure turns up as `ဆကီး` for `ကြီး`
  and `ငကား` for `ကြား`, plus `ငြွေ်` for `မြွေ` and similar. So
  `မယ်တော်ဘုရင်မကြီး` counts as 0 in a raw grep for that string over
  ch. 122-131 while `မယ်တော်ဘုရင်မဆကီး` counts 113. Treat all such
  forms as one word, and normalise them when quoting in the review (done
  for parts 13-14; said so once in the text).
- **`方清雪` / `ဖန်ကျင်းရွယ်` — continuity collision with part 9.** In
  part 9 she is placed with 魏武侯's household (群玉閣 faction). Ch. 138
  brings her out as the person who can say "if I say I did it", and ch.
  140 states outright that the body of the empress-dowager now holds
  `ဖန်ကျင်းရွယ်`. Same name, same spelling family (`ဖန်ချင်းရွှယ်` 3×
  in these ten chapters), so either part 9's household note was wrong or
  she has moved. Not settled from the Burmese; flagged in the review.
- **皇翷's kinship is still open.** Ch. 124 says the dowager is childless
  and not the reigning sovereign's birth mother; ch. 131 has 皇翷 at her
  birthday as her son in all but name; ch. 141 says the late emperor's
  death made her 姬明月's nominal mother. The review records this as
  unresolved rather than guessing.
- **`သားတော်` (ch. 140)** — 姬明月 refers to herself this way to the
  dowager while the narration calls her `သူမ`. If the Chinese is 兒臣
  the Burmese is defensible but reads male; if it is 兒/兒子 it is an
  error. Needs the Chinese.
- **`萬初` has three renderings inside ch. 129**: `ဝမ်းချူရှင်း` (1),
  `ဝမ်ချူရှင်း` (3), and `ရှင်းကွမ်းယဲ့ယွဲ့` (1, glossed in brackets
  as "ကြယ်ရောင်လသစ်ရွက်"). Written up in part 13 §3.4.
- **冷十七 / `လန်ရှီချီ` — downgraded from a finding.** Ch. 110 glosses
  the two as one person in the text itself:
  `လန်ရှီချီ(အေးစက်ခြင်း ၁၇)`. So the reader is not meant to see two
  people; the damage is only that `အေးစက်ခြင်း` reads as a mood. Part
  12 §3.1 was corrected to say this. Which Chinese name sits behind
  `လန်ရှီချီ` (冷十七 vs 藍十七) cannot be checked — no Chinese below 193.
- **Translator's footnote in the body (ch. 141)**: `(မှတ်ချက်:
  တော်ဝင်တရားရုံးတော်အကြောင်း အခန်း ၁၀၅ တွင် ရှု)`. First and only
  such note in 141 chapters; worth keeping, and evidence that the
  translator tracks the book's own continuity.
- **Palace-office vocabulary is unstable**: `အထိန်းတော်ကြီး` (王世海,
  head of the 內侍), `မိန်းမစိုး` (柳青), `အထိန်းတော်`. Ch. 136's whole
  tension is about who may question whom, and the Burmese gives no
  ranking between the three terms.
- **`柳青` spelling**: `လျိုချင်း` 111× vs `လျှိုချင်း` 33× in ch.
  132-141, plus one `ညီအစ်ကိုလျှို`. He dies in this stretch, so the
  split falls on the worst possible chapters. **Corrected after reading
  ch. 142-145: he is not killed.** He is poisoned at the banquet, is
  stabilised by 裴語涵's pills, and has a seven-day window (ch. 141);
  ch. 142 says outright that his being alive is luck, and ch. 144 has
  the dowager shouting that he is still alive. Part 14 §3.1 and part 15
  ch. 145 were wrong to call this a death; both are fixed in the file. `ဝမ်သဲ့ဟိုင်` 58× vs
  `ဝမ်ဒဲ့ဟိုင်` 2×; `ပိုင်ဖန်ဥယျာဉ်` 16× vs `ဘိုင်ဖန်ဥယျာဉ်` 3×.
- **`၄၈,၀၀၀` pores (ch. 120) and `ဘုရင်ဟွေ့`** stay open from §7 —
  nothing in 122-141 resolves either.

## 9. Part 15-16 (ch. 142-161) — open and closed

- **Closed: `柳倩` is alive.** See §8. Part 14 and part 15 both said he
  died; the file now says poisoned and stabilised. No death scene exists
  in 141-161.
- **The tower and the court share one Burmese name.** `တော်ဝင်တရားရုံးတော်`
  is 大理寺 in part 15 (ch. 149), the place one goes to fetch the
  `သူခိုးတွင်း` water in ch. 141, and an entire world in ch. 158
  (`တော်ဝင်တရားရုံးတော်လောကကေ ထွက်နိုင်တယ်`). Container and contained
  carry the same string; nothing in the text marks the switch. Written
  up in part 16 §3.1. Not fixable without the Chinese.
- **`ခွေးဧကရာဇ်` (dog emperor), ch. 156 and 158, is never identified.**
  In the trial world 葉寧 is himself the emperor, so the phrase may be
  self-mockery or may point at 皇翷. The review leaves it open. If it is
  皇翷, it is the only posthumous reference to him in these chapters.
- **`姬明月`'s sex.** Ch. 156 has the two dead sages *deduce* from the
  trial's construction that she must be a woman in male dress. The
  narration never confirms it, but ch. 159-160 give her `ငါကိုယ်တော်`
  (the imperial plural) as a reigning sovereign. Flagged in the review
  as "twist or translation error". Note this is the second time the
  book dangles a sex reveal without paying it (the first was the
  dowager's body in ch. 132-147).
- **`ကျီမင်းယွဲ့` / `ချီမင်းယွဲ့` in a single chapter.** Ch. 160: 6 vs 2.
  The `ချီ` forms land on her angry lines. Same pattern as `ဖန်ကျင်းရွယ်`
  and `လျိုချင်း`: the variant appears when the character is emotional.
- **Quote convention flips per chapter, not per arc.** Ch. 152 uses
  `' '` 59 times and `" "` zero times; ch. 155-156 use `' '` zero times.
  Part 15 recorded a switch at ch. 147 from `" "` to `' '`; that is true
  for 147-154 only. It is a per-chapter artefact, not a house style.
- **Numbers are written two ways in one chapter.** Ch. 154 gives
  16,650 as `၁၆၆၅၀` and again as `တစ်သောင်းခြောင့်ခြောက်ရာ့ငါးဆယ်`
  ("ခြောင့်" for "ခြောက်"), and the tower total as
  `သုံးသောင်းသုံးထောင့်သုံးရာသုံးဆယ့်သုံး` (33,333). The step count is
  the only number the tower arc turns on.
- **Sect names first appear in ch. 152-161 without a glossary**: `陳` and
  `王` are only `အကိုချန်း` / `ဝမ်အစ်ကို` in ch. 152 and only become
  `ဆရာသခင်ချန်` / `ဆရာသခင်ဝမ်` in ch. 161. A reader who skims 152 will
  not connect the two bickering ghosts to the two blank pillars.
- **`ညီမဖေး` (ch. 156)** — 葉寧 calls 裴語涵 "sister 裴" when he comes out
  of the trial. Not attested earlier in the Burmese. Left as an open
  question in the review; could be a kinship term of address, could be
  the translator's slip.
