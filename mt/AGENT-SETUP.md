# Wiring Groq to the agent host

Terminal only. Every step is one copy-paste block.

## 1. The key name

`.env` currently holds `groq=key`. The dotenv parser here accepts any valid name,
so that line loads — but nothing reads a variable called `groq`. Groq's own
tooling and Kilo both look for **`GROQ_API_KEY`**, and a value of literally `key`
is not a key.

```sh
grep -n '^GROQ_API_KEY=' ~/.env || echo 'GROQ_API_KEY is missing'
```

Fix the line (keep the rest of the file):

```sh
sed -i '/^groq=/d' ~/.env
printf 'GROQ_API_KEY=%s\n' 'gsk_your_real_key_here' >> ~/.env
```

Verify the key itself, before any agent config:

```sh
set -a; . ~/.env; set +a
curl -s https://api.groq.com/openai/v1/models \
  -H "Authorization: Bearer $GROQ_API_KEY" | head -c 300
```

A JSON list of models means the key works. `401` means the value is wrong;
`403` means the key has no access to that endpoint.

## 2. Why Groq is not read by this repository

The MCP server needs `RAPIDAPI_KEY` (for the translator) and nothing else. The
Groq key is read by the **agent host** — the program that runs the model and
calls the MCP tools. So the two keys live in the same `.env` but are consumed by
different processes:

| key | read by |
|---|---|
| `RAPIDAPI_KEY` | `mt/mcp_server.py --env-file ~/.env` |
| `GROQ_API_KEY` | the agent host (Kilo), exported into its shell |

Keep both in `~/.env`, never in the repository.

## 3. Kilo configuration

Config file: `~/.config/kilo/kilo.jsonc`. This writes a fresh one — if you
already have one, merge the `provider` and `mcp` blocks by hand instead.

```sh
mkdir -p ~/.config/kilo
cat > ~/.config/kilo/kilo.jsonc <<EOF
{
  "\$schema": "https://app.kilo.ai/config.json",
  "model": "groq/moonshotai/kimi-k2-instruct",
  "provider": {
    "groq": { "options": { "apiKey": "{env:GROQ_API_KEY}" } }
  },
  "mcp": {
    "rapidapi-translator": {
      "type": "local",
      "command": [
        "$(command -v python3)",
        "$HOME/proofreading/mt/mcp_server.py",
        "--env-file", "$HOME/.env"
      ],
      "enabled": true
    }
  }
}
EOF
```

Three details that matter:

- `{env:GROQ_API_KEY}` is expanded by Kilo at launch. It is not a shell
  expansion, so quoting is irrelevant — but the variable must be **exported**
  into the process that starts Kilo.
- `--env-file` keeps the RapidAPI key out of the config file entirely. Nothing
  secret is written to `kilo.jsonc`.
- The model string is `provider/model`, so `groq/moonshotai/kimi-k2-instruct`.

## 4. Choose the model for Burmese

The host model has to read Burmese prose and judge register. That is not what
most of these models are good at.

| model id | note |
|---|---|
| `groq/moonshotai/kimi-k2-instruct` | strongest multilingual of the Groq set; 128K context; **start here** |
| `groq/llama-3.3-70b-versatile` | fast and cheap, weaker Burmese; usable for structure, not for judging particles |
| `groq/openai/gpt-oss-120b` | reasoning model, good at rules, limited Burmese fluency |

To switch, change the `"model"` line only:

```sh
sed -i 's|"model": .*|"model": "groq/moonshotai/kimi-k2-instruct",|' ~/.config/kilo/kilo.jsonc
```

Expect the model to be the weakest link for Burmese regardless of which one you
pick. The tools (segmentation, dictionary, review lookup) are what make the
output checkable — the model is what makes it readable.

## 5. Launch

```sh
set -a; . ~/.env; set +a     # exports both keys into this shell
kilo                          # from ~/proofreading
```

Check the tools are visible:

```
/mcp
```

You want `rapidapi-translator` connected and ten tools listed. If it is not
there, run the server directly to see the error:

```sh
python3 mt/mcp_server.py --selftest
python3 mt/mcp_server.py --env-file ~/.env
```

## 6. Readiness check, before running anything

```sh
cd ~/proofreading
set -a; . ~/.env; set +a

echo "GROQ_API_KEY:   ${GROQ_API_KEY:+set}"
echo "RAPIDAPI_KEY:   ${RAPIDAPI_KEY:+set}"
python3 mt/mcp_server.py --selftest | grep -E '"ok"|"key"'
python3 mt/rapidapi_translator.py --check | grep '"key"'
command -v kilo || echo "kilo is not installed"
```

`--env-file` is not passed to the selftest above; the key lines show what the
shell is carrying. Both must say `set` before chapter work starts.

## 7. The AI text has to exist first

The agent judges the API's Burmese. Nothing in the repository contains it —
`content/mtranslate/` holds only `zh-en` and `en-zh`. Without step one there is
nothing to proofread, only a Chinese source and a human reference.

```sh
python3 mt/rapidapi_translator.py --translate "天下太平"
```

If that returns Burmese, the key works. Then produce the two chapters:

```
translate_chapters {"chapters": "1-2"}
```

This is the only paid step; it is one request per ~4,500 characters and writes
to `content/mtranslate/rapidapi/`. Everything after it is local.

## 8. The first run

`kilo run` is the non-interactive command; `--file` attaches a file, and
`--auto` stops it from auto-rejecting every permission request.

```sh
kilo run --auto --file mt/quality/finetune-agent-prompt.md \
  "Follow the brief. Call read_chapter for chapter 1, then segment_text on the
   first three AI sentences, and stop. Report the tool output verbatim."
```

Interactively, it is just `kilo` and then the same instruction typed in.

The first useful signal is not the rewrite — it is whether the model quotes
tool output accurately. If it invents a `segment_text` result, the model is too
weak; the key is fine.

## 9. What to watch on the first chapter

| symptom | meaning |
|---|---|
| it rewrites without calling `segment_text` | the tool loop is not happening; check `/mcp` |
| it calls `translate_text` for every sentence | wasteful; the AI text is already on disk after `translate_chapters` |
| it treats `∅` or `{?}` as errors | it ignored the prompt; re-read step 3 |
| it "fixes" `အေခြအေန` in the reference | it is editing the tone reference, not the AI text |
| it produces fluent Burmese with no evidence line | reject the record; the prompt requires one |

Cost on a 70B-class model is roughly a cent per chapter; on Kimi K2 more. Run
one chapter, count the calls, then decide before doing 195.
