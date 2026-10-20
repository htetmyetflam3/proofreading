# Self-audit — `output/review/burmese-overview.md`

Read end to end as a reader, then measured. Findings ordered by how much they hurt.
Line numbers are 1-based against the file at commit `3a5f7ff` (265,656 chars / 7,758 lines).

---

## A. Syllable segmentation in units 1–8 and in the front matter (critical)

The text in ch 1–80 is spaced one syllable at a time — `ရုံး တစ်ခု ကို ပြန်ဖွင့်တယ်`
instead of `ရုံးတစ်ခုကို ပြန်ဖွင့်တယ်`. Units 9–20 are written normally.

Metric: short joins (Myanmar letter + space + 1–2 character token + space) per 1,000 chars.

| unit | per 1k | | unit | per 1k |
|---|---|---|---|---|
| front matter | 7.8 | | 11 (102–111) | 1.4 |
| 1 | 4.0 | | 12 (112–121) | 2.5 |
| 2 | 3.0 | | 13 (122–131) | 2.3 |
| 3 | 2.0 | | 14 (132–141) | 2.2 |
| **4** | **11.0** | | 15 (142–151) | 2.3 |
| **5** | **17.0** | | 16 (152–161) | 2.1 |
| **6** | **18.8** | | 17 (162–171) | 3.6 |
| **7** | **16.4** | | 18 (172–181) | 1.9 |
| **8** | **18.8** | | 19 (182–191) | 1.5 |
| 9 (81–91) | 1.7 | | 20 (192–195) | 1.4 |
| 10 (92–101) | 1.9 | | | |

A 10× step between unit 8 and unit 9. A reader hits it at ch 81 and again backwards
at ch 31. Every line has to be re-spaced by hand; no rule can do it safely
(Burmese has no word delimiter to restore).

## B. Template drift (high)

| | units | problem |
|---|---|---|
| required 4th section | 9–20 (12) | `### မသဲကွဲမရှင်းလင်းသည့်အပိုင်းများ` — correct |
| old 3rd section | 1, 2 | `၃။ ဒီပိုင်းရဲ့ မရှင်းတာ` — no translation section |
| no 3rd/4th section | 3–8 (6) | stop after `၂။ ကျွန်တော် ဘာထင်လဲ` |
| spacing variant | 4–8, 13–20 | `၃။ ဒီပိုင်း ရဲ့ ဘာသာပြန်` vs `၃။ ဒီပိုင်းရဲ့ ဘာသာပြန်` |

Unit 3 (ch 21–30) has the weakest structure of the twenty: two sections, no
translation note, no unclear-items note.

## C. Chapter coverage is not 10 per unit everywhere (high)

Chapter headings (`**အခန်း …**`) counted per unit: 10 for most, but

- unit 6 (51–60): **9**
- unit 7 (61–70): **5** — chapters paired, 61–62, 63–64, 65–66, 67–68, 69–70
- unit 2 (11–20): **12** — 59/60 split is real, but the extra heading is unlabelled
- unit 9 (81–91): **11**, unit 10 (92–101): **11** — eleven for ten chapters

## D. The xianxia reader's three questions have no standing answers (high)

1. **Entry** — answered once, in unit 1 (bonus + the no-self-kill rule). Fine.
2. **Power level** — never stated as a standing datum. `အဆင့်` appears 0–12 times
   per unit, only where the plot needs it; no unit says "he is now at X, the ceiling
   here is Y".
3. **Who is the villain of this arc** — implicit in the prose, never named as such.
   A reader tracking a 20-unit ladder cannot see the antagonist chain.

Also: the mechanic is never called what it is. The file says `အပိုဆု` and `စနစ်`
(where `စနစ်` means the in-world marking rubric, not the transmigration cheat), so a
reader looking for "does it have a system, and what type" gets no sentence to hold.

## E. The preface misstates the reviewer's position (high, integrity)

Lines 3–9: *"ပြောတဲ့လူက ဘာသာပြန်ကို ဖတ်ပြီးတဲ့ စာဖတ်သူတစ်ယောက်"* — a reader of the
translation. That is not the position the file now needs (proofreader who can check
against the Chinese). It also never says **which chapters can be checked**:

    Chinese corpus in repo   ch 193–408   (213 chapters)
    Burmese translation      ch 1–195
    overlap where a Chinese check is possible   ch 193–195 only

So every "မူရင်းက …" claim for ch 1–192 rests on a source that is not in the
workspace. Units 1–3 quote ~2,100 Chinese characters; none of it is in
`input/chinese-*.txt`. Either those quotations get a stated source, or they get
labelled as recalled.

## F. English leaks and vocabulary (medium)

`tune title` (715), `legacy encoding` (2598), `encoding` (3387, 4016, 4417, 4761,
5070), `quote` (6435), `Chapter – 123` (5461, inside a quoted heading — acceptable).
The standing rule is no English in the file.

## G. Narrator voice leaks (medium)

The file's voice is `ကျွန်တော်`. Four places slip into first-person `ငါ` outside
quotation: 842 (`**၆။ ငါ အကြိုက်ဆုံး။**`), 5367, 5715, 5730.

## H. Evaluative vocabulary is thin and therefore repetitive (medium)

`အကောင်းဆုံး` 63×, `အားနည်းချက်` 22×, and the uncertainty label
`ဒါက လှည့်ကွက် လား၊ ဘာသာပြန် ရွေးချယ်မှု လား — မသေချာဘူး။` 6× verbatim.
The judgement is usually right; the words carrying it are not varied, and the
evidence is often a sentence away from the verdict instead of beside it.

## I. Title (medium)

`# ယဲ့နင် — ဆယ်ခန်းတစ်ပိုင်း ပြန်ပြောချက်` → should be
`# ယဲ့နင် — ဆယ်ခန်းတစ်ဖြတ် review`.

## J. Character table (low)

- one row still prints raw Chinese (`威武候`, line 37) while the rest of the table
  uses Burmese names;
- no "first seen / last seen" column, which is what a reader tracking 195 chapters
  actually needs;
- the table has no villain marking, so it does not answer D3.

## K. Heading collision (low, mechanical)

`## မသဲကွဲမရှင်းလင်းသည့်အပိုင်းများ` (global, line 81) and
`### မသဲကွဲမရှင်းလင်းသည့်အပိုင်းများ` (per unit, 12×) share a name. Folded YAML
and any TOC show 13 identical labels with no unit tag.

## L. What is genuinely good (protect it)

- Quote discipline: 170 blockquote blocks, the damaged forms are repaired on the
  way in, and the file is explicit when a quotation is left verbatim because it is
  the evidence (`နှုတ်ဆက်ပွဲ` kept as printed).
- The global unclear-items list admits its own earlier errors (line 96: *"ကျွန်တော့်
  အမှား"*) — that is the right habit and should survive the rewrite.
- Per-unit section 3 (translation) is the strongest writing in the file: it names
  the mechanism (聖院 → တရားရုံး, 五體投地 → ဒြပ်စင်ငါးပါး, Chapter 123–137 in
  English) instead of asserting "the translation is bad".

---

## Fix plan, in order

1. De-segment units 1–8 and the front matter by hand (no script — the risk of
   joining two real words is higher than the cost of reading).
2. Rebuild the preface: reviewer position, the 193–195 verification boundary, and
   what is quoted from where.
3. Standardise the four sections in all 20 units; restore unit 3's missing two.
4. Add the three standing lines to every unit: entry/cheat, power level, this arc's
   villain — one sentence each, at the top of section 1.
5. Re-space unit 7 to ten chapters; re-label the 11/12-heading units.
6. Kill the English leaks and the four `ငါ`s; vary the uncertainty label.
7. Title, table row, heading collision.
