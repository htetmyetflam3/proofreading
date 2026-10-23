# Machine translation (`mt/`)

> Setup, keys, Kilo, the MCP server and every command flag live in
> [`SETUP.md`](SETUP.md). This file only explains the two translation routes.

Two routes, one runner. Engine availability is checked before anything runs, and
the output directory records which engine actually produced the text.

```
zh-en   Chinese -> English   offline model installed          RUNS HERE
en-zh   English -> Chinese   offline model                    RUNS HERE
```

There is no machine translation to or from Burmese. The Burmese under review
comes from the translator API (`mt/RAPIDAPI.md`); these two routes exist so a
local agent can read the Chinese source in English, and re-express an English
reading back into Chinese to check the meaning survived.

## Install

```sh
python3 mt/fetch_engine.py --install zh-en   # clones and unpacks the model
python3 mt/fetch_engine.py --check           # what is installed; writes nothing
python3 mt/fetch_engine.py --remove zh-en
```

Models go to `$XDG_DATA_HOME/argos-translate/packages` and are not committed.
Installing needs no packages: the `.argosmodel` is a zip and it is unpacked
in-tree. Only running a model needs `ctranslate2` and `sentencepiece`, in the
same `python3` that runs `mt/translate.py` (see `SETUP.md` 1.1).

## Run

```sh
python3 mt/translate.py --list                       # availability per route and engine
python3 mt/translate.py --route zh-en                # all 210 Chinese chapters
python3 mt/translate.py --route zh-en --only 193     # one chapter
python3 mt/translate.py --route en-zh --engine offline --only 193
```

Outputs, one directory per route:

```
content/mtranslate/zh-en/chapters/ch0193.en.txt    one file per chapter
content/mtranslate/zh-en/book.en.txt               the whole run
content/mtranslate/zh-en/report.json               engine, sentences, seconds, empty lines
content/mtranslate/manifest.json                   every route of the last run
```

`content/mtranslate/` holds generated route outputs; the merged books under `content/merged/` are tracked core data.

## What the two routes are for

| route | what it is for |
|---|---|
| `zh-en` | read the Chinese source in English; check that the API's Burmese says the same thing |
| `en-zh` | re-express an English reading back into Chinese and compare it with the original |

Neither produces Burmese, and neither is a substitute for the reference text in
`content/merged/episodes.docx`. The agent's judgement comes from the Chinese,
the human Burmese, and the engine — not from machine translation.

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
translation. `mcp.py` exposes the same calls as a local MCP server.

```sh
python3 mt/api_translate.py --chapters 1-2 --plan   # offline, no key
RAPIDAPI_KEY=... python3 mt/api_translate.py --chapters 1-2 --run
```

The key is read from `RAPIDAPI_KEY`, or from a file named with `--env-file`
(nothing is loaded implicitly; `.env` is gitignored), never stored. `mt/chapter_map.py` reads the
Chinese↔Burmese chapter numbers out of `content/merged/episodes.docx` (last
existing: Chinese 193 ↔ Burmese 195; next untranslated: 194), and `--chapters
last|next|existing` uses it for both the run and the comparison reference.
`mcp.py --selftest` checks the MCP server without a key or network, and
`mcp.py --print-config --client kilo|claude|codex|gemini` prints that
client's config. See `mt/RAPIDAPI.md` for the endpoint formats, the SSH/phone
setup, and the cache/retry rules.
