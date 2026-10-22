# Setup and command reference

One document for a VPS over SSH. Terminal only: every step is copy-paste, no GUI.
Order: dependencies → keys → models → Kilo → MCP → the run → every flag.

Paths assume the clone is at `~/proofreading`. If it is elsewhere, adjust `$REPO`.

```sh
export REPO="$HOME/proofreading"
cd "$REPO"
git pull
```

---

# Part 1 — Setup

## 1.1 Python and dependencies

**One interpreter runs everything in `mt/`: `python3`.** Third-party packages go
into that same interpreter, and every command in this document is spelled
`python3 …` for exactly that reason.

```sh
python3 --version                                  # 3.10 or newer
python3 -m pip install --break-system-packages \
    ctranslate2 sentencepiece                      # only for --engine offline
python3 -c "import ctranslate2, sentencepiece; print('ok')"
```

Only `mt/translate.py --engine offline` imports those two, and only when it
loads a model. Installing a model (`mt/fetch_engine.py`) is standard library: it
unpacks the `.argosmodel` zip itself and never imports `argostranslate`.
Everything else — `mt/apicaller.py`, `mt/api_translate.py`, `mt/mcp_server.py`,
`mt/lexicon.py`, `mt/overview_index.py`, `mt/agent_work.py` — needs nothing
installed at all.

### Why not `uv run`

The `pyproject.toml` at the repo root is the **scraper's** environment
(selenium, pikepdf, pyarrow), not `mt/`. `uv run mt/…` builds or reuses that
environment, so it can install hundreds of megabytes to run a script that needs
none of it — and it is a different interpreter from the one
`pip --break-system-packages` just installed `ctranslate2` into. That is the
drift: a model installed for `python3`, then a runner started by `uv` that
cannot see it.

If you have uv and want it, keep it out of the project for the stdlib scripts:

```sh
uv run --no-project mt/apicaller.py --status       # optional spelling
```

Never use `uv run` for `mt/translate.py --engine offline` unless you installed
`ctranslate2` and `sentencepiece` inside that same environment.

Node is only needed by the engine under `Engine/` (segmentation and POS), which
`mt/lexicon.py` shells out to:

```sh
node --version
cd "$REPO/Engine" && npm install --omit=dev && cd "$REPO"
```

## 1.2 Keys in `~/.env`

One file, two keys, both outside the repository. It is in `.gitignore`.

```sh
cat > ~/.env <<'EOF'
RAPIDAPI_KEY=your_rapidapi_key
GROQ_API_KEY=gsk_your_groq_key
EOF
chmod 600 ~/.env
```

Who reads what:

| key | read by | for |
|---|---|---|
| `RAPIDAPI_KEY` | `mt/api_translate.py --env-file ~/.env`, `mt/mcp_server.py --env-file ~/.env` | producing the AI-translated Burmese |
| `GROQ_API_KEY` | the agent host (Kilo), exported into its shell | the model that runs the proofreading agent |

The repository never reads `GROQ_API_KEY`. A variable named `groq` or `GROK_API_KEY`
will not be found: the name is exactly `GROQ_API_KEY`.

Verify without leaking the value:

```sh
set -a; . ~/.env; set +a
echo "RAPIDAPI_KEY: ${RAPIDAPI_KEY:+set}"
echo "GROQ_API_KEY: ${GROQ_API_KEY:+set}"

curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | head -c 200
```

Two `set` lines and a model list mean the keys are good. `401` = wrong value,
`403` = key lacks access.

## 1.3 Offline translation models (optional)

Only needed for `mt/translate.py`. There is **no Burmese model anywhere** — Argos
publishes 100 packages and none is `my` — and that is deliberate: Burmese comes
from the API, and no machine translation to or from Burmese is part of this
pipeline.

```sh
python3 mt/fetch_engine.py --check
python3 mt/fetch_engine.py --install zh-en
python3 mt/fetch_engine.py --install en-zh
python3 mt/translate.py --list          # the two routes, now available
```

Exactly two routes exist, the two `mt/translate.py` runs: `zh-en` and `en-zh`.
Models land in `$XDG_DATA_HOME/argos-translate/packages` (`translate-zh_en-1_0`,
~86 MB each) and are never committed. `--check` writes nothing, anywhere;
`--json` prints the same table as one object. The install is standard library —
no `argostranslate`, no `pip`, no virtualenv. If `git` is missing, the clone is
the step that fails, before anything is downloaded.

## 1.4 Dictionaries (optional, for the chapter merge)

```sh
python3 format/fetch_dicts.py --check
python3 format/fetch_dicts.py
```

CC-CEDICT (~8.6 MB) + English–Myanmar (~16.7 MB), sha256-verified, rebuildable.
Not needed by the proofreading agent.

## 1.5 Kilo

Skip this block if `kilo --version` already answers; only the config below matters
then.

```sh
npm install -g @kilocode/cli         # or: curl -fsSL https://kilo.ai/install | sh
kilo --version
```

Config file: `~/.config/kilo/kilo.jsonc` (global). Project file: `./kilo.jsonc`.

```sh
mkdir -p ~/.config/kilo
cat > ~/.config/kilo/kilo.jsonc <<EOF
{
  "\$schema": "https://app.kilo.ai/config.json",
  "model": "groq/openai/gpt-oss-120b",
  "provider": {
    "groq": {
      "options": { "apiKey": "{env:GROQ_API_KEY}" },
      "models": {
        "openai/gpt-oss-120b": {
          "tool_call": true,
          "limit": { "context": 131072, "output": 32000 }
        }
      }
    }
  },
  "mcp": {
    "rapidapi-translator": {
      "type": "local",
      "command": [
        "$(command -v python3)",
        "$REPO/mt/mcp_server.py",
        "--env-file", "$HOME/.env"
      ],
      "enabled": true
    }
  }
}
EOF
```

Three things that bite:

- `{env:GROQ_API_KEY}` is expanded by Kilo, not the shell. The variable must be
  **exported** into the process that starts Kilo: `set -a; . ~/.env; set +a`.
- `--env-file` keeps `RAPIDAPI_KEY` out of the config file. Nothing secret is
  written to `kilo.jsonc`.
- The model string is `provider/model`. Kilo has a built-in `groq` provider, so
  no base URL is needed.

**Check the config took, before running anything.** A bad key or an unknown model
id makes Kilo fall back to Auto Free silently, so `/status` is the only proof:

```sh
set -a; . ~/.env; set +a
kilo models groq                          # your account's list; the id must appear
kilo                                      # then, inside the TUI:
#   /models   -> pick groq/openai/gpt-oss-120b
#   /mcps     -> rapidapi-translator: on
#   /status   -> the active model is the groq one, not Auto Free
```

If `openai/gpt-oss-120b` is not in `kilo models groq`, the `models` block above
registers it by hand — that is what `provider.groq.models` is for.

Model choice, for Burmese specifically:

| model | note |
|---|---|
| `groq/openai/gpt-oss-120b` | 131,072 context, 65,536 max completion, reasoning model. Verbose by design — it narrates its thinking — which costs tokens but costs nothing in a `kilo run` session nobody reads. Default here because the context window fits a whole chapter plus the tool output |
| `groq/moonshotai/kimi-k2-instruct` | strongest multilingual on Groq, 128K; shorter reasoning, more direct |
| `groq/llama-3.3-70b-versatile` | cheap and fast, weak Burmese; fine for structure |

To quiet the reasoning, Groq accepts `reasoning_effort` of `low`, `medium` or
`high`; pass it as a provider option if your build forwards it, or leave it —
the chatter goes to the transcript, not to the draft.

Every one of them is weak at Burmese relative to this task. The tools are what
make output checkable; the model only makes it readable.

## 1.6 MCP server

```sh
python3 mt/mcp_server.py --selftest        # protocol round-trip, no network
python3 mt/mcp_server.py --check           # config state, no request
python3 mt/mcp_server.py --env-file ~/.env # run it (stdio; Kilo does this for you)
```

Register it with a client automatically instead of by hand:

```sh
python3 mt/mcp_server.py --print-config --client kilo
python3 mt/mcp_server.py --install-config --client kilo --env-file ~/.env
```

`--install-config` merges into plain JSON only. If the target is JSONC with
comments it refuses and prints the snippet, so nothing you wrote is lost.

Fourteen tools. Reading and checking (free, no API request):
`read_chapter`, `review_lookup`, `review_brief`, `lookup_word`, `lookup_name`,
`check_names`, `segment_text`, `detect_language`. Writing, all local:
`save_draft`, `export_drafts`, `register_name`. Paid, never on your behalf:
`translate_text`, `translate_batch`, `translate_chapters`.

---

# Part 2 — The run

## 2.1 Produce the AI translation (the only paid step)

Two chapters per call, never the whole novel at once. The first call is 194 +
195: the human translation ends at Chinese 193 (`episodes.docx`), and these are
the first two chapters behind it.

```sh
cd "$REPO"
python3 mt/apicaller.py --status                   # cursor, chapters left; free
python3 mt/apicaller.py                            # plan 194 + 195; free
python3 mt/apicaller.py --run --env-file ~/.env    # translate 194 + 195
python3 mt/apicaller.py --run --env-file ~/.env    # 196 + 197
```

The cursor moves by itself: a chapter that already has a JSONL under
`content/mtranslate/rapidapi/` is not offered again.

`&` is a shell operator — unquoted, `--194&195` backgrounds `--194` and tries to
run `195`. Quote it, or use `+`:

```sh
python3 mt/apicaller.py '--194&195' --run --env-file ~/.env
python3 mt/apicaller.py --194+195 --run --env-file ~/.env    # same pair
```

194 + 195 is 363 paragraphs, 6,427 characters, **10 requests** (40 paragraphs
per request). A third chapter is refused, and the refusal prints the pairs to
run in order. `mt/api_translate.py --run` enforces the same limit unless you add
`--allow-bulk`.

Writes `content/mtranslate/rapidapi/`:

```
ch0194.my.jsonl            one record per paragraph: source, target, cached
ch0194.my.txt               the chapter in Burmese
pair-0194-0195.my.txt       both chapters
compare-ch194-ch195.md      Chinese | new Burmese | existing human Burmese
report-0194-0195.json       this pair's report
report.json                 the latest report, overwritten each run
```

Re-running is free for anything already cached; the cache is
`content/mtranslate/rapidapi-cache.sqlite3`. `--json` prints the plan or the
report as one object, which is what the agent reads.

## 2.2 Check the join before spending agent tokens

```sh
python3 - <<'EOF'
import sys; sys.path.insert(0, "mt")
from mcp_server import Server
r = Server(enabled_cache=False).call_tool("read_chapter", {"chapter": 194})
print(r["translation"])
print(r["paragraphs"][0])
EOF
```

Want `{'available': True, 'attached': 166, 'mismatched': 0, ...}` and a `my` field
on each paragraph. Alignment is verified per paragraph against the Chinese, so a
stale file cannot shift Burmese onto the wrong sentence.

## 2.3 Run the agent

Interactive — start Kilo, then point it at the brief and give it one task:

```sh
set -a; . ~/.env; set +a
cd "$REPO" && kilo
```

```
Read mt/quality/finetune-agent-prompt.md and follow it exactly.

Chapter 194. read_chapter first and check translation.available.
Start at paragraph 1, stop after 5 drafts, then report.
```

Three lines, because the brief already contains everything else — the register,
the procedure, the output contract, the honesty clause, and the rule that it must
not translate a chapter itself or spend API quota. The first line is what makes
the other two mean anything: without it the agent has opinions about Burmese and
no instructions.

Do not paste the brief into the chat: it is 300 lines, and pasting it into a
phone terminal is how a session gets truncated before it starts. Read it from
disk so the agent can re-read it when the context is compacted.

Headless:

```sh
set -a; . ~/.env; set +a
kilo run --auto -m groq/openai/gpt-oss-120b \
  --file mt/quality/finetune-agent-prompt.md \
  "Chapter 194. read_chapter first, confirm translation.available is true.
   Paragraphs 1-5: segment_text each 'my' text, lookup_word any word you doubt,
   save_draft with ai_text set to that same 'my' text. Stop after five."
```

`-m` beats the config file and the last-used model, so a headless run cannot
silently land on Auto Free. `--auto` is required for headless: without it every
permission request is auto-rejected and the run exits 1 even though nothing was
wrong.

## 2.3b The chain, and the smallest first test

Start Kilo in the repo with the keys exported, then send **text**, not shell:

```sh
set -a; . ~/.env; set +a
cd "$REPO" && kilo
```

**First test — background only, costs nothing.** Paste this as one message:

```
Read mt/quality/finetune-agent-prompt.md and follow it exactly.
Then review_brief {} and stop. Quote the register line it gives you and
state the register you will enforce. Do not open burmese-overview.md.
```

You want back: 15 characters, the three known defects, the reviewer's verdict,
every arc title. If the tool is missing from `/mcps`, the MCP server is not
running — fix that before anything else.

**The whole chain, one message.** Step 2 is the only paid one; drop it if the
chapters are already translated. Step 7 is a report, not a rewrite — the tones
are re-matched one paragraph at a time afterwards.

```
Read mt/quality/finetune-agent-prompt.md and follow it exactly.
Chapter 194. Work through the chain, then stop and report:

1. review_brief {}, then review_lookup {"chapter": 194}. One round each.
2. translate_chapters {"chapters": "194&195"} — only if read_chapter says
   translation.available is false. Say the request count out loud first.
3. read_chapter {"chapter": 194}: report available, attached, mismatched,
   and quote paragraph 1 Chinese next to its `my`.
4. check_names on every paragraph's `my` text. List every variant and the
   canonical form, per paragraph. Do not rewrite anything yet.
5. segment_text on the same paragraphs. Report splits word/unit/loan/unknown
   and coverage per sentence; list only the `unknown` ones.
6. lookup_word for each token the segmenter split, and for each name variant
   check_names reported. No repair without a dictionary hit.
7. register_name for a genuinely new term only — list what you would register
   and wait for me before writing. Never a second spelling of a listed term.
8. Re-match tone: for each paragraph say which register it is (narration or
   dialogue), quote its closing particle, and name any sentence that breaks it.
   Do not save_draft yet.

Nothing is rewritten in this pass. Report at the end.
```

`translate_chapters` is the only line that spends money: it refuses more than
two chapters and prints the pair it would send. If the human translation is
already on disk the step costs nothing — `read_chapter` tells you with
`translation.available`.

**What to check in the report** — these are the numbers you can verify yourself.
`profile.py` and `tag.py` read the **reference** chapters (the human Burmese),
so they give you the target to hold the AI text against, not the AI text itself:

```sh
python3 mt/quality/profile.py --chapter 1 --chapter 2   # target register + particles
python3 mt/quality/tag.py --chapter 1                   # target word view with POS
python3 mt/names.py --check --chapter 194               # canonical names, no agent
```

The AI translation is measured inside the session with `segment_text` (splits,
coverage, tags) and `check_names` (variants) — that is what steps 4–5 do.

## 2.4 Inspect the result

```sh
sqlite3 content/mtranslate/agent-drafts.sqlite3 \
  "select paragraph_index, note, substr(draft_text,1,40) from drafts where chapter=1"
```

Or from inside the agent session: `export_drafts {"chapter": 1}`.

---

# Part 3 — Command reference

All flags below are copied from `--help`; run any of them with `--help` for the
same text.

## `mt/apicaller.py` — the two-chapter caller

| flag | meaning |
|---|---|
| `194 195` (positional) | chapters to translate, as bare numbers |
| `--194&195` `--194+195` `--194,195` `--194-195` | the same pair written as one token; `&` needs quoting |
| `--chapters` | explicit spec, `next`, or omitted for the cursor |
| `--status` | human span, chapters done and left, next pair; no request |
| `--plan` | count the pair, no request (default) |
| `--run` | call the API; needs `RAPIDAPI_KEY` |
| `--target` | target language, default `my` |
| `--source` | source language or `auto`, default `auto` |
| `--source-file` | Chinese text with `===== 第N章 =====` headings |
| `--existing` | human Burmese, used as the comparison reference |
| `--docx` | bilingual DOCX the chapter numbers come from |
| `--map` / `--no-map` | saved chapter map; or assume Chinese N = Burmese N |
| `--out-dir` | output directory, default `content/mtranslate/rapidapi` |
| `--cache` / `--no-cache` | translation cache |
| `--no-compare` | skip the comparison markdown |
| `--max-chars` / `--max-items` | request limits |
| `--timeout` / `--attempts` | per request |
| `--json` | the plan, report or status as one object |
| `--env-file` | read `KEY=VALUE` lines from PATH; the shell wins |

## `mt/api_translate.py` — the batch engine under it

| flag | meaning |
|---|---|
| `--chapters` | `1-2`, `1,3-4`, `all`, `next`, `last`, `existing`. Default `1-2` |
| `--target` | target language, default `my` |
| `--source` | source language or `auto`, default `auto` |
| `--source-file` | Chinese text with `===== 第N章 =====` headings |
| `--existing` | human Burmese for the comparison reference |
| `--docx` | bilingual DOCX the chapter numbers come from |
| `--map` | saved chapter-map JSON; skips reading the DOCX |
| `--no-map` | assume Chinese N = Burmese N |
| `--out-dir` | output directory, default `content/mtranslate/rapidapi` |
| `--cache` | SQLite cache path |
| `--no-cache` | ignore the cache |
| `--keep-notes` | keep author notes and promo lines |
| `--no-compare` | do not write the comparison file |
| `--max-chars` | characters per request (API limit 5,000) |
| `--max-items` | strings per batch request |
| `--timeout` | per-request timeout |
| `--attempts` | retries per request |
| `--json` | print the report as JSON |
| `--env-file` | read `KEY=VALUE` lines from PATH; the shell wins |
| `--plan` | offline count, no request (default) |
| `--run` | actually call the API; needs `RAPIDAPI_KEY` |
| `--allow-bulk` | lift the two-chapter limit for one `--run` |

## `mt/mcp_server.py` — the agent's tool server

| flag | meaning |
|---|---|
| `--print-config` | print a client snippet and exit |
| `--client` | `json`, `claude`, `kilo`, `codex`, `gemini` |
| `--check` | print configuration state, no request |
| `--install-config` | write/merge the entry into the client config |
| `--config` | config file for `--install-config` |
| `--env-file` | load keys from PATH at startup (also `RAPIDAPI_ENV_FILE`) |
| `--selftest` | protocol round-trip, no network |
| `--cache` / `--no-cache` | translation cache |
| `--source-file` | Chinese source for `translate_chapters` |
| `--existing` | human Burmese for the comparison |
| `--out-dir` | default output directory |
| `--docx` | bilingual DOCX for chapter numbers |
| `--draft-store` | SQLite file for agent drafts |
| `--max-chars` `--max-items` `--timeout` `--attempts` | request limits |

Fourteen tools. The four the agent needs before it judges anything:

| tool | use |
|---|---|
| `review_brief` | the review in one round — characters, defects, verdict, arc openings |
| `lookup_name` | one `EtoBnames.txt` entry by key or Burmese form |
| `check_names` | names present in a paragraph, plus suspected variant spellings |
| `register_name` | append a new term to `EtoBnames.txt` |

## `mt/translate.py` — Chinese/English routes

| flag | meaning |
|---|---|
| `--route` | `zh-en` or `en-zh`; repeatable |
| `--engine` | `offline`, `azure`, `cmd` |
| `--cmd-template` | shell command for `cmd`; `{text}` or stdin, `{source}`/`{target}` substituted |
| `--engine-note` | model id recorded in `report.json` |
| `--source-file` | Chinese text |
| `--limit` | first N chapters |
| `--only` | chapter number; repeatable |
| `--out-dir` | output directory |
| `--list` | route availability, then exit |
| `--resume` | skip chapters that already have output |
| `--cascade` | `zh-en` first, then `en-zh` which reads it |

## `mt/agent_work.py` — drafts without an agent host

| command | purpose |
|---|---|
| `read <chapter>` | `--reference-lines N`, `--no-reference` |
| `save <chapter> <paragraph>` | `--draft` or `--draft-file`, `--ai-text`, `--model`, `--note` |
| `note <chapter> <paragraph>` | attach a note to an existing draft |
| `export <chapter>` | `--out-dir`, `--require-all` |
| `list` | drafts in a chapter, or all chapters |
| `stats` | totals for the store |

Global: `--store` (SQLite path), `--source`, `--existing`, `--docx`, `--json`.

## `mt/chapter_map.py` — chapter numbers from the DOCX

| flag | meaning |
|---|---|
| `--docx` | bilingual DOCX |
| `--at` | look up Chinese chapter N; repeatable |
| `--burmese` | look up Burmese chapter N; repeatable |
| `--json` | print the whole map |
| `--write` | save the map as JSON |

## `mt/lexicon.py` — dictionary and segmentation probes

Read-only over `Engine/`. Never writes `master.json`, the tree, or the caches.

| function | question |
|---|---|
| `lookup(word)` | is this an entry, which POS family, is it reachable, is there a dictionary-proved repair |
| `coverage(text)` | which characters no entry or syllable can explain |
| `suggest(text)` | proved repairs for storage-order damage |
| `segment(text)` | tokens, smallest units, split verdicts, coverage |

CLI: `--lookup WORD`, `--coverage TEXT`, `--suggest TEXT`, `--segment TEXT`.

Split verdicts: `word` (entry), `unit` (known syllable), `loan` (a virama stack
the inventory still cannot name — rare, since the tree now carries all 732 Pali
units), `unknown` (neither — the only suspect bucket).

### Rebuilding the syllable tree

The tree in `Engine/.cache-tree/` is built from the sealed master in
`Engine/MonoSyllabism/map/master.json.enc`. Rebuild it whenever the syllable
lists or the builder change — never edit the four files by hand.

```sh
node --import ./scraper/wasm/box/runtime-guard.mjs mt/rebuild_tree.mjs
```

The guard import is required: the builder calls `MyNormalize()`, which lives in
the WASM. It prints the unit count and the four hashes, then rewrites
`Engine/CACHE-SOURCE.json` — `tag-text.mjs`, `mt/quality/tag-both.mjs` and
`mt/quality/units.mjs` all verify the cache against that file, so a stale hash
fails loudly instead of silently tagging with an old tree.

The build is deterministic: burmese first, then pali, so every existing unit
keeps its id. `--out DIR` writes elsewhere; `--no-record` leaves the manifest
alone.

`runBuild` writes only the four cache files. Do **not** use `runBuildPos` to
regenerate them: it prunes dictionary rows from the master it is handed, which
is why `tag-both.mjs` gives it a scratch copy.

### Is the WASM current?

```sh
node scraper/wasm/box/tools/verify-payload.mjs
```

It decrypts the payload inside `box.wasm` and diffs all four modules and the
API shim against the sources on disk. Exit 0 means the binary **is** the code
you are reading — no rebuild. The tree is data: it lives outside the WASM, so a
tree rebuild never needs a new binary.

### Rebuilding the WASM, with or without `engine.wasm`

`box.wasm` is two parts: `engine.wasm` (QuickJS compiled) plus a payload built
from the four `mapbuilder/base` files and `mapData`. `build-payload.mjs`
**inlines `mapData`**, so any edit to `master.json` needs a new binary, and a
stale one is caught by the check above.

Repack only — needs no C toolchain, uses the tracked `engine.wasm`:

```sh
cd scraper/wasm/box
node build-payload.mjs && node tools/pack-box.mjs && node tools/record-build.mjs
cd ../../.. && node scraper/wasm/box/tools/verify-payload.mjs
```

`record-build.mjs` is not optional: `host.mjs` refuses to boot a `box.wasm`
whose sha256 does not equal `build-info.json.box_sha256`.

Full rebuild from source — no `engine.wasm` required; it is generated, not
authored:

```sh
python3 -m pip install "ziglang==0.17.0"
git clone --depth 1 -b v0.17.0 https://github.com/quickjs-ng/quickjs.git /tmp/qjs-ng
QJS_SRC=/tmp/qjs-ng sh scraper/wasm/rebuild-box.sh
```

Two facts worth knowing before trusting a hash:

- `engine.wasm` **is** byte-reproducible (`8cef309a…`) as long as the output
  file keeps that exact name — zig writes the output basename into the wasm
  `name` section, so building to `engine-test.wasm` changes 25 KB of the file.
- `payload.bin` and therefore `box.wasm` are **not** reproducible: the payload
  is AES-256-GCM with a fresh IV, and the loader is obfuscated with a random
  seed. Five packs of identical sources gave five different `box_sha256`
  values. `verify-payload.mjs` is the check that matters; it compares decrypted
  *contents*, not the file hash.

## `mt/overview_index.py` — the background document

| flag | meaning |
|---|---|
| `--index` | index file to read or write, default `content/review/overview.yaml` |
| `--build` | regenerate `content/review/overview.yaml` |
| `--find TEXT...` | sections mentioning every word |
| `--get ID` | print one section by id |
| `--chapter N` | the arc covering chapter N (compact map) |
| `--section` | with `--chapter`: `story`, `opinion`, `problems`, `title` |
| `--titles` | list ids only |
| `--limit` | max sections printed by `--find` |
| `--verify` | re-check every range against the markdown |
| `--brief` | the whole review in one round: characters, defects, verdict, every arc's opening (≈35k chars) |
| `--chars-per-arc N` | story characters per arc in `--brief`, default 420; `200` ≈ 25k, `60` ≈ 18k |

## `mt/names.py` — the name list (`content/reference/EtoBnames.txt`)

The list is the authority for Burmese spelling. The agent reads it before it
judges and appends to it when a genuinely new term appears.

| flag | meaning |
|---|---|
| `--list` | every entry, with line numbers |
| `--lookup TERM` | one entry by English key or by Burmese form |
| `--check --text '…'` | canonical names in a fragment, and suspected variants |
| `--check --chapter N` | the same over `chNNNN.my.jsonl` |
| `--add 'KEY = BURMESE'` | append a new entry, dated; refuses a duplicate key or a form owned by another key |
| `--warnings` | duplicate forms, reversed lines, and prose skipped |
| `--json` | the same report as one object |
| `--file` / `--translations` | override the list or the `mtranslate` directory |

Everything except `--add` is read-only. `--add` only appends; it never rewrites
an existing line.

```sh
python3 mt/names.py --lookup "Liu Jin"
python3 mt/names.py --check --chapter 194
python3 mt/names.py --add 'Shen Ji = ရှန်းကျီ'
```

## `mt/quality/profile.py` / `mt/quality/tag.py` — the numbers behind "tone"

Both are read-only and take `--chapter N` (repeatable), and both read the
**human Burmese chapters** — they measure the target, not the AI text. That is
what makes a register claim checkable instead of an opinion.

```sh
python3 mt/quality/profile.py --chapter 1 --chapter 2 --json /tmp/profile.json
python3 mt/quality/tag.py --chapter 1
```

`profile.py` prints sentence and word counts, words per sentence with median and
p90, the top words, and the particle counts — `၏` / `ရဲ့`, `တွင်` / `မှာ`,
`များ` / `တွေ` — which is exactly the narration/dialogue split the brief
enforces. `tag.py` dumps the word view with POS families via
`mt/quality/tag-both.mjs` (both views, scratch dir, nothing under `Engine/`
written).

To measure the AI text itself, use the MCP tools inside the session:
`segment_text` returns tokens, units, tags, split counts and coverage, and
`check_names` returns the canonical/variant pairs. There is no CLI equivalent
on purpose — those two read whatever text you hand them, and the chapter files
are not the only place the text lives.

## `mt/mt_compare.py` — the reference audit (one-off, not per chapter)

Read-only, zero API calls, but it profiles the **whole reference** first, so it
is a once-per-checkout audit rather than a step in the chain:

```sh
python3 -m pip install --break-system-packages 'json5>=0.12,<1'   # its only dependency
python3 format/tag_docx.py            # writes content/kmt-pos/ယဲ့နင်.raw_pos.txt (~6.3 MB of prose)
python3 mt/mt_compare.py --profile    # writes content/analysis/reference-data-audit.json
```

`--input FILE.jsonl` scores MT candidate records against that profile and writes
`output/mt/<name>-comparison.jsonl`. It does **not** by itself resolve
compounds or sentences — its own output says so.

## `mt/fetch_engine.py` / `format/fetch_dicts.py`

| flag | meaning |
|---|---|
| `--install {zh-en,en-zh}` | clone and unpack one model |
| `--all-available` | install both routes |
| `--check` | what is installed, with size; writes nothing |
| `--remove {zh-en,en-zh}` | delete one model |
| `--package-dir` | package directory, default `$XDG_DATA_HOME/argos-translate/packages` |
| `--json` | the report as one JSON object |
| `fetch_dicts.py --force` | rebuild dictionaries even if present |

---

# Part 4 — What goes wrong

| symptom | cause |
|---|---|
| `kilo run` exits 1 with a permission diagnostic | missing `--auto` |
| `401` from Groq | `GROQ_API_KEY` value is wrong, or the line is still `groq=key` |
| `/status` shows Auto Free after you set a model | the key was not exported, or the model id is not in `kilo models groq` |
| edits look like a different model wrote them | a session-level pick overrode `kilo.jsonc`; `/models` to reset, or pass `-m` |
| `/mcp` shows no server | `kilo.jsonc` path wrong, or python path in `command` is wrong |
| `--194&195` returns to the prompt, then `195: command not found` | unquoted `&`; use `'--194&195'` or `--194+195` |
| `2 at a time` refusal | intended: run the pairs it prints, in order |
| `read_chapter` has no `my` field | `apicaller.py --run` has not produced that chapter |
| Pali words split at every `္` (`ဗု · ဒ · ္ဓ`) | old cache: the loader stopped after `burmese`. Rebuild with `mt/rebuild_tree.mjs` |
| `Original scraper cache hash mismatch` | the tree was edited by hand; rebuild it, never patch the four files |
| `Master mapData.* differs from the built WASM` | `mapData` was edited; check with `scraper/wasm/box/tools/verify-payload.mjs` before rebuilding the binary |
| `engine.wasm` missing / `zig: not found` | repack only: `build-payload.mjs`, `pack-box.mjs`, `record-build.mjs`; or install `ziglang==0.17.0` and see *Rebuilding the WASM* |
| `box.wasm` hash changed after a rebuild | expected — payload IV and loader obfuscation are random; compare `verify-payload.mjs` output, not `box_sha256` |
| a name keeps changing between chapters | it was never in `EtoBnames.txt`; `names.py --add` it once, then reuse |
| `--add` refuses with "already owns" | the Burmese form belongs to another key — reuse that key, or pick a different form deliberately |
| `translation.attached` is 0 but `available` is true | the jsonl exists but its `source` lines no longer match the Chinese — regenerate it |
| `ModuleNotFoundError: No module named 'argostranslate'` | old copy of `mt/fetch_engine.py`; `git pull` — it unpacks the zip itself now |
| `uv run` says the model is missing, `python3` finds it | two interpreters; see 1.1 and use `python3` |
| `--check` lists `zt-en`, `en-my`, `zh-my` | old copy; the only routes are `zh-en` and `en-zh` |
| `no offline model installed` | `python3 mt/fetch_engine.py --install zh-en` |
| `{?}` tags in segmentation | not an error; 2 of 3 are engine coverage, not text damage |
| the agent "fixes" `အေခြအေန` in the reference | it is editing the tone reference; it must never be edited |
