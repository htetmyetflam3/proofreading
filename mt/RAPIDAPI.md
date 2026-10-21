# RapidAPI translator — chapter runs and MCP

Three files:

| file | what it is |
|---|---|
| `mt/rapidapi_translator.py` | the API caller: three endpoints, cache, retries, redaction |
| `mt/api_translate.py` | translate chapters of the local novel and compare with the existing human Burmese |
| `mt/mcp_server.py` | the same caller as a local MCP server (stdio, no dependencies) |

Nothing needs installing: all three are standard-library Python 3.10+.

## Why the API looked complicated

It is three endpoints with three different body formats, and the RapidAPI
playground only shows one of them at a time:

| endpoint | query | body | response |
|---|---|---|---|
| `POST /detect` | — | raw text, `Content-Type: text/plain` | `data.language`, `data.language_name` |
| `POST /translate` | `?source=auto&target=my` | raw text, `Content-Type: text/plain` | `data.translated_text` |
| `POST /translate/batch` | `?source=auto&target=my` | JSON **array** of strings | `data.translated_texts`, same order |

Every response is wrapped as `{"status": true, "data": {...}}`. The JSON you
pasted (`{"status": true, "data": {"language": "", "language_name": {}}}`) is the
**detect response example**, not a request body — that is why it looked wrong.
Do not send it as a body.

`/translate/batch` is the endpoint to use for a chapter: one request carries an
array of paragraphs and returns them translated in the same order.

Headers on every call:

```
X-RapidAPI-Key: <your key>
X-RapidAPI-Host: multi-format-ai-translator-the-most-complete.p.rapidapi.com
```

The client builds all of that for you.

## Key

The key is read from `RAPIDAPI_KEY` in your shell and is never written to disk,
logged, or included in an error message. Type it without putting it in history:

```sh
read -rsp 'RapidAPI key: ' RAPIDAPI_KEY; echo
export RAPIDAPI_KEY
```

Optional overrides, mainly for tests:

- `RAPIDAPI_BASE_URL` — base URL (default `https://multi-format-ai-translator-the-most-complete.p.rapidapi.com`)
- `RAPIDAPI_HOST` — value of the `X-RapidAPI-Host` header
- `RAPIDAPI_CACHE` — SQLite cache path (default `content/mtranslate/rapidapi-cache.sqlite3`)

## The first two chapters

```sh
# One cheap request first, to prove the key works:
python3 mt/rapidapi_translator.py --detect "大周，帝都盛京。"

# Offline plan: reads the source, counts paragraphs and requests. No key needed.
python3 mt/api_translate.py --chapters 1-2 --plan

# Real run (spends quota):
python3 mt/api_translate.py --chapters 1-2 --run
```

The plan for chapters 1–2 of `content/source/chinese-0511241012-from-8011_1.txt`:

```
chapter  paragraphs  characters  requests
      1          69        1562         2
      2          70        1586         2
  total         139        3148         4
```

Two requests per chapter because a batch is capped at 40 strings. Each chapter
is only ~1,570 characters, so raising the item cap puts one chapter in one
request — two requests for both chapters:

```sh
python3 mt/api_translate.py --chapters 1-2 --run --max-items 80
```

The character budget (4,500) still applies, so a longer chapter can still need
more than one request.

Outputs (`--out-dir`, default `content/mtranslate/rapidapi/`):

| file | content |
|---|---|
| `ch0001.my.jsonl` | one record per paragraph: `source`, `target`, `cached`, chapter, index |
| `ch0001.my.txt` | the chapter in Burmese, paragraphs separated by blank lines |
| `book.my.txt` | every selected chapter |
| `compare-ch001-ch002.md` | Chinese paragraph, new Burmese, and the existing human Burmese as a reference block |
| `report.json` | paragraphs, characters, requests, cache hits, detected language, files |

What is sent is the paragraph text only. Crawler markers, `--- Page N ---`
lines, site promo lines (`活動時間…`), author `PS:` notes, dotted rules and the
`wunzinnosp` watermark are dropped (`--keep-notes` keeps notes and promo lines).
The source file itself is never modified.

The comparison deliberately does **not** claim paragraph alignment with the
human translation: the human text comes from a PDF with its own line wrapping
and the alignment has never been verified. The human chapter is included whole,
under a collapsible block, so you can read the two side by side yourself.

## MCP server

```sh
python3 mt/mcp_server.py --print-config
```

prints a ready-to-paste JSON block:

```json
{
  "mcpServers": {
    "rapidapi-translator": {
      "command": "python3",
      "args": ["/absolute/path/to/repo/mt/mcp_server.py"],
      "env": {"RAPIDAPI_KEY": "<your-rapidapi-key>"}
    }
  }
}
```

Put it in the client's MCP config (Claude Desktop:
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS,
`%APPDATA%\Claude\claude_desktop_config.json` on Windows; Cursor uses
`.cursor/mcp.json`). The key lives in the client config, not in the repository.

Tools:

| tool | arguments | notes |
|---|---|---|
| `detect_language` | `text` | one request |
| `translate_text` | `text`, `target` (default `my`), `source` (default `auto`) | one request unless cached |
| `translate_batch` | `texts[]`, `target`, `source` | only uncached strings are sent |
| `translate_chapters` | `chapters` (`"1-2"`, `"1,3-4"`, `"all"`), `target`, `source`, `out_dir` | writes the same files as the CLI; one request per ~4,500 characters |

Example tool call and result:

```json
{"name": "translate_batch",
 "arguments": {"texts": ["大周，帝都盛京。", "因為他有外掛。"], "target": "my"}}
```

```json
{"translations": ["...", "..."], "source_language": "zh-Hant",
 "source_language_name": "Chinese (Traditional)", "requests": 1, "cached": 0}
```

Protocol notes: newline-delimited JSON-RPC over stdio, `initialize` /
`tools/list` / `tools/call`, protocol versions 2024-10-07 through 2025-06-18.
stdout carries protocol messages only; tool failures come back as `isError`
results, unknown tools as JSON-RPC `-32602`.

The MCP server is local. The RapidAPI-hosted MCP
(`https://mcp.rapidapi.com` through `npx mcp-remote`, the config you pasted)
also works and exposes the same three endpoints, but it cannot read the novel
file, cache paragraphs, or write the comparison — which is why this local one
exists.

## Requests, cache and retries

- One request covers many strings: up to 40 items and 4,500 characters
  (configurable with `--max-items` / `--max-chars`; the documented provider
  limit is 5,000 characters per request).
- A string longer than the budget is split on sentence punctuation and rejoined.
- Successful strings are cached in SQLite by host + language pair + exact text.
  Re-running a chapter, or translating it to a second language, sends only what
  is missing. `--no-cache` disables this.
- 408/425/429/5xx and network errors are retried with exponential backoff,
  honouring `Retry-After`. A retried request may already have been counted by
  RapidAPI; the report shows how many requests were made.
- Redirects are not followed, so the key cannot be forwarded to another host.
- The key is scrubbed from every error message before it is raised.

## What this does not do

- It does not replace the human translation or approve machine output. There is
  no automatic promotion into `mt/mt_memory.py`.
- It does not inject glossary entries; the API has no glossary parameter.
- It does not repair the OCR damage in the Chinese source (the substituted
  characters described in `MT.md`). The API will translate what it is given.
- It does not align the human Burmese to paragraphs, as explained above.

## Tests

The tests use a local mock of the three endpoints, so they need no key and no
network:

```sh
python3 -m unittest discover -s mt/tests -v
```
