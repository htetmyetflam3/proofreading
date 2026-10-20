# The five-column merge

## What goes into each episode

```
[episode N]

Chinese original              the source, as downloaded
Chinese to English (machine)  offline Marian/OPUS-MT checkpoint (zh-en)
English to Chinese (machine back-translation)
                              the Chinese output re-translated back (en-zh)
Chinese to Burmese            dictionary glosses -- see the warning below
Burmese version               the published human translation
```

Every episode is the same five columns, in that order, for as long as the
Burmese translation exists: **197 episodes** (the Chinese file has 210 chapters,
the Burmese 197, so the merge stops where the Burmese stops).

## The Chinese → Burmese column is a dictionary gloss, not MT

There is no downloadable Chinese-Burmese translation model. Argos publishes 100
packages and none contains `my`; no `translate-zh_my` or `translate-en_my` file
exists on GitHub; Hugging Face is unreachable from this machine. The column is
therefore CC-CEDICT word lookup mapped through the English-Myanmar dictionary:

```
这些→∅ 人口→လူဦးရေ/ဦးရေ 底子→အောက်ခြေ/အခံ 若是→လျှင် 流民→ဒုက္ခသည် …
```

Coverage over the whole book: **143,364 of 213,334 terms resolved (67.2 %)**,
69,970 left as `∅`. It is a crib for a translation agent, not Burmese prose. The
column heading and a caveat line inside the file both say so.

A real Chinese → Burmese column needs an API engine:

```sh
export AZURE_TRANSLATOR_KEY=...      # your key, never committed
export AZURE_TRANSLATOR_REGION=...
python3 mt/translate.py --route zh-my --engine azure
python3 format/merge_episodes.py --pair order --only-matched \
        --with zh-en --with en-zh --with zh-my
```

The merge picks up whatever exists; a column that has not been produced prints
`(not run: …)` and is never faked.

## Generating the three machine columns

One command, in dependency order (`en-zh` reads the `zh-en` output):

```sh
python3 mt/translate.py --cascade            # zh-en -> en-zh -> zh-my
python3 mt/translate.py --cascade --resume   # continue an interrupted run
```

| route | model | chapters | time |
|---|---|---|---|
| `zh-en` | `translate-zh_en-1_0` (83 MB) | 210 | ~13 min ×2 processes |
| `en-zh` | `translate-en_zh-1_0` (82 MB) | 210 | ~13 min ×2 processes |
| `zh-my` | none — dictionary gloss | 210 | 24 s |

Outputs: `output/mt/<route>/chapters/chNNNN.<ext>.txt`, `book.<ext>.txt`,
`report.json`.

## Why the back-translation is useful despite being machine-made

`en-zh` closes the loop: Chinese → English → Chinese. Where the round trip returns
something close to the original, the English leg preserved the meaning. Where it
returns nonsense, the English leg lost it. Examples from chapter 193:

| Chinese | zh-en | en-zh |
|---|---|---|
| 這些人口，可都是大周的底子 | These people, they're the bottom of the week. | 这些人,他们是下星期。 |
| 所以蔡向高几乎毫不猶豫 | That's why Tsai was almost unsuspecting | 所以蔡<unk>几乎毫不怀疑, |

`底子` became "bottom of the week" and survived as 下星期; the name 蔡向高 collapsed
to `<unk>`. That is exactly the drift a translation agent should be told about.

## Pairing

`--pair order` maps episode N to Chinese chapter N and Burmese chapter N. The two
files are **not** the same run of chapters — one pair is confirmed by content
(Chinese 193 = Burmese marker 197) — so the header of every generated file states
that positional pairing is unverified. Use `--pair map --map pairs.json` when you
have a real mapping; `output/merged/episodes-verified.txt` is that file for the
one confirmed pair.

## Files

| file | contents |
|---|---|
| `output/merged/episodes-5col.txt` | 197 episodes × 5 columns, 9.7 MB |
| `output/merged/pairs-5col.json` | how each episode was paired, which columns were present |
| `output/merged/episodes.txt` | Chinese + Burmese only, all 210 episodes |
| `output/merged/episodes-verified.txt` | the single content-verified pair |
| `output/mt/zh-en/book.en.txt` | Chinese → English, 210 chapters |
| `output/mt/en-zh/book.zh.txt` | English → Chinese back-translation, 210 chapters |
| `output/mt/zh-my/book.my.txt` | Chinese → Burmese dictionary gloss, 210 chapters |

