# Machine translation (`mt/`)

Four routes, one runner. Engine availability is checked before anything runs, and
the output directory records which engine actually produced the text.

```
zh-en   Chinese -> English   offline model installed          RUNS HERE
en-my   English -> Burmese   via mt/nllb.py (CTranslate2)       RUNS OFFLINE
my-en   Burmese -> English   via mt/nllb.py (CTranslate2)       RUNS OFFLINE
zh-my   Chinese -> Burmese   via mt/nllb.py (CTranslate2)       RUNS OFFLINE
```

## Why three routes have no offline model

Argos Translate publishes 100 packages; its index (`argospm-index`) contains no
`my` (Burmese) entry in either direction, and a search of GitHub for
`translate-en_my` / `translate-my_en` model files returns nothing. The two model
files that do exist for this project's languages are Chinese/English only:

| file | size | source |
|---|---|---|
| `translate-zh_en-1_0.argosmodel` | 83 MB | `jiangwensm/OPUS-argosmodels` (mirror of the Argos package) |
| `translate-en_zh-1_0.argosmodel` | 82 MB | same |

They are Marian/OPUS checkpoints, and they are fetched through a sparse git clone
because `argosopentech.com` and `raw.githubusercontent.com` are not reachable from
this machine.

So the Burmese routes need an engine that is not Argos: `mt/nllb.py` (offline,
NLLB-200 under CTranslate2) or an API. Azure Translator v3 supports `my` in
both directions, and `mt/translate.py --engine azure` already speaks it: it reads
`AZURE_TRANSLATOR_KEY` and `AZURE_TRANSLATOR_REGION` from your shell, never from a
file, and refuses to run when they are missing.

## Install

```sh
uv run mt/fetch_engine.py --install zh-en    # downloads and installs the model
uv run mt/fetch_engine.py --check            # what is installed
uv run mt/fetch_engine.py --remove zh-en
```

Models go to `$XDG_DATA_HOME/argos-translate/packages` and are not committed.

## Run

```sh
python3 mt/translate.py --list                       # availability per route and engine
python3 mt/translate.py --route zh-en                # all 210 Chinese chapters
python3 mt/translate.py --route zh-en --only 193     # one chapter
python3 mt/translate.py --route en-my --engine azure # needs the two env vars
python3 mt/translate.py --route zh-my --engine glossary --only 193
```

Outputs, one directory per route:

```
content/mtranslate/zh-en/chapters/ch0193.en.txt    one file per chapter
content/mtranslate/zh-en/book.en.txt               the whole run
content/mtranslate/zh-en/report.json               engine, sentences, seconds, empty lines
content/mtranslate/manifest.json                   every route of the last run
```

`content/mtranslate/` holds generated route outputs; the merged books under `content/merged/` are tracked core data.

## The glossary engine is not a translation engine

`--engine glossary` walks each Chinese sentence with CC-CEDICT, maps the English
glosses through the English-Myanmar dictionary, and prints what it resolved:

```
这些人口，可都是大周的底子  →  人口→လူဦးရေ/ဦးရေ 底子→အောက်ခြေ/အောက်ခံ
```

It measures dictionary coverage (`unresolved` / `tokens` in `report.json`), which
is useful for judging whether a dictionary-only path could ever beat MT. It does
not produce Burmese prose, and nothing downstream should treat it as translation.

## Reading the Chinese

Both scripts split the source at the `===== 第…章: … =====` headings and convert
the Chinese numeral in the heading to an Arabic number, so `第一百九十三章`
becomes chapter 193. Traditional and simplified forms are both understood: the
dictionary stores both and OpenCC normalises running text before lookup.

## What the offline model actually produces

Chapter 193, first sentences (`content/mtranslate/zh-en/book.en.txt`):

```
These people, they're the bottom of the week.
If we go to Wei, isn't it the power of the Emperor?
That's why Tsai was almost unsuspecting and stopped the displaced first.
```

`底子` becomes "bottom of the week" and `蔡向高` becomes "Tsai" — usable for
gist, not for publishing. That is the trade: an 83 MB offline model that runs at
about 30 sentences/second on CPU, against an API that costs money and needs a
key.

## RapidAPI translator (Chinese → Burmese)

`mt/rapidapi_translator.py` speaks the RapidAPI "Multi format AI translator" API
and `mt/api_translate.py` runs it over chapters of the local source, writing
JSONL/TXT plus a Chinese/Burmese comparison against the existing human
translation. `mt/mcp_server.py` exposes the same calls as a local MCP server.

```sh
python3 mt/api_translate.py --chapters 1-2 --plan   # offline, no key
RAPIDAPI_KEY=... python3 mt/api_translate.py --chapters 1-2 --run
```

The key is read from `RAPIDAPI_KEY`, or from a file named with `--env-file`
(nothing is loaded implicitly; `.env` is gitignored), never stored. `mt/chapter_map.py` reads the
Chinese↔Burmese chapter numbers out of `content/merged/episodes.docx` (last
existing: Chinese 193 ↔ Burmese 195; next untranslated: 194), and `--chapters
last|next|existing` uses it for both the run and the comparison reference.
`mt/mcp_server.py --selftest` checks the MCP server without a key or network, and
`mt/mcp_server.py --print-config --client kilo|claude|codex|gemini` prints that
client's config. See `mt/RAPIDAPI.md` for the endpoint formats, the SSH/phone
setup, and the cache/retry rules.
