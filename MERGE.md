# What goes into the merge, and which MT to feed the translator

## The translator's actual chain

The published Burmese was produced like this:

```
Chinese original  ->  machine English  ->  human rewrite/restyle into Burmese
```

The middle step is the one that carries the tone. That means the useful machine
column is **Chinese → English**, not English → Burmese: it reconstructs the
intermediate the translator actually read. Machine English → Burmese would
rebuild the *final* product by machine and compete with the human text.

## Columns, and what each one is for

| column | what it is | include in the prompt? | why |
|---|---|---|---|
| Chinese original | source | **yes** | the text being translated |
| `zh-en` machine English | the translator's own intermediate, regenerated (offline model) | **yes** | tone and sentence-splitting decisions live here |
| published Burmese | the target the human actually wrote | **yes** | the only ground truth for voice |
| `my-en` Burmese → English | back-translation of the human text | **no** — drift report only | it is derived from the reference; showing it lets the model copy its errors |
| `my-zh` Burmese → Chinese | back-translation into the source language | **no** — weakest column | it invites the model to "correct" the Chinese original to match a back-translation |
| `en-my` English → Burmese | a competing machine hypothesis | **no** | it would teach the model to imitate weak MT instead of the human voice |

So: **`zh-en` is the pivot. `my-en` is a measuring stick. `my-zh` is not worth
carrying.**

## Why not Chinese ↔ Burmese directly

| route | model available offline | note |
|---|---|---|
| `zh-en` | **yes**, 83 MB Marian/OPUS checkpoint | runs here, ~30 sentences/s on CPU |
| `en-my` | no | Argos has no Burmese package; no `translate-en_my` exists on GitHub |
| `my-en` | no | same |
| `zh-my` | no | direct model absent, pivot blocked by `en-my` |

So the Burmese legs need an API key (Azure Translator v3 supports `my` both ways).
`mt/translate.py --engine azure` is wired and reads the key from the environment
only.

## Cost, measured (`python3 mt/pivot.py --plan`)

```
zh-en   210 chapters   47,189 sentences    893,770 Chinese characters   free (local)
my-en   197 chapters   59,828 sentences  2,222,348 Burmese characters   Azure per character
en-my                  input is the zh-en output (English characters)   Azure per character
zh-my   210 chapters   47,189 sentences    893,770 Chinese characters   two calls if pivoted
```

## The drift question

If the goal is "did the Burmese drift from the Chinese?", the honest measurement
is:

```
my-en  vs  zh-en      both in English, compared on the same chapter
```

Both sides then live in the same language, and the only difference is which text
they came from. Comparing `my-zh` against the original Chinese instead puts two
machine systems between the two texts and mixes the Chinese output style into the
result, so a low score cannot be attributed to the Burmese.

Only **one chapter** exists in both files, so drift can only be measured there:

```
Chinese 193  ==  Burmese marker 197   (title အခန်း ၁၉၅)
opens  這些人口，可都是大周的底子   /  ဤလူများသည် မဟာကျိုးပြည်ထောင်၏
ends   你們在幹什麼？                /  ခဗျားတို့ ဘာလိုပ်နေကတာဟာလဲ
```

`python3 mt/pivot.py --compare` prints the two English renderings side by side
once `my-en` exists.

## What is committed

| file | contents |
|---|---|
| `output/merged/episodes.txt` | all 210 episodes, Chinese + Burmese only, positional pairing (clearly labelled in the header) |
| `output/merged/episodes-verified.txt` | the one verified pair, Chinese + Burmese only |
| `output/merged/style-sample.txt` | the verified pair with the `zh-en` column added — the reference pack for a translation agent |

Regenerate any of them:

```sh
python3 format/merge_episodes.py                                   # episodes.txt
python3 format/merge_episodes.py --pair map --map pairs.json --only-matched
python3 format/merge_episodes.py --pair map --map pairs.json --only-matched --with zh-en
```

`--with` accepts `zh-en`, `my-en`, `my-zh`; a column that has not been produced is
printed as `(not run: …)` and never guessed.
