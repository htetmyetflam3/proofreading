# Restoring the Burmese MT columns (zh→my, en→my)

The generated MT text was wiped because it looked like a build artifact that
could be regenerated. It could not, because the Burmese engine is not a
dependency of this repository — Argos publishes no Burmese package at all.

This file is the recovery runbook. The short version:

```sh
git pull
export MT_ENGINE_COMMAND='<your translator command>'
python3 mt/translate.py --route zh-my --engine cmd --only 1 --only 2 \
    --engine-note '<model id>' 
```

Read `content/mtranslate/zh-my/report.json` afterwards: `detail` records the
exact command and model note that produced the text. Commit that file. It is
the one thing a wipe cannot then lose.

## Why there is no default engine

Argos publishes exactly 100 packages; none of them is `my`, in either
direction. Verified against `argosopentech/argospm-index`:

```sh
curl -s https://api.github.com/repos/argosopentech/argospm-index/contents/index.json \
  | python3 -c "import json,sys,base64; d=json.load(sys.stdin); \
r=json.loads(base64.b64decode(d['content'])); \
print(len(r), [x for x in r if 'my' in x['from_code']+x['to_code']])"
# 100 []
```

So `--engine offline` can never serve `zh-my`, `en-my`, `my-en`. Whatever
Burmese engine you install, it lives outside the repository and must be
recorded.

## What was lost, and what is committed instead

| thing | committed? | note |
|---|---|---|
| `content/mtranslate/<route>/*.txt` | no | regenerable output; leave it untracked |
| `content/mtranslate/<route>/report.json` | **yes** | engine, command, model note, counts |
| the Burmese engine itself | **never** | installed on the VPS, outside the repo |
| `MT_ENGINE_COMMAND` | **no** | shell environment only |

Rule: if you delete the generated text, `git log -- content/mtranslate` must
still tell you which engine produced it. That is what `--engine-note` is for.

## The offline path: mt/nllb.py

`mt/nllb.py` is a real translator: NLLB-200 in a CTranslate2 conversion, CPU,
no key, no billing. It covers all three dead routes (zh→my, en→my, my→en).

```sh
pip install ctranslate2 sentencepiece huggingface_hub
python3 mt/nllb.py --check                       # what is missing
python3 mt/nllb.py --search                      # candidate CT2 NLLB repos on the Hub
python3 mt/nllb.py --download --repo <picked>    # ~600 MB, outside the repo
python3 mt/nllb.py --from zh --to my --text "天下太平"
```

Language codes are the short ones (`zh`, `my`, `en`) and are mapped to FLORES
internally; a FLORES code passed directly is accepted unchanged.

Into the route runner:

```sh
python3 mt/translate.py --route zh-my --engine cmd \
    --cmd-template "python3 mt/nllb.py --from {source} --to {target}" \
    --engine-note "nllb-200-distilled-600M int8 (ct2)" --only 1 --only 2
```

`report.json` then records the command and the model note, exactly like any
other `cmd` engine.

## Wiring any engine

`--engine cmd` runs a command per sentence. Two calling conventions:

```sh
# text on stdin, translation on stdout
--cmd-template "/opt/mt/bin/translate --to mya_MM"

# text substituted into the command
--cmd-template "/opt/mt/bin/translate --to mya_MM --text {text}"
```

`{source}` and `{target}` are substituted with the route's codes (`zh`/`my`,
`en`/`my`). A non-zero exit aborts the route with the command and the first
200 bytes of stderr, so a broken engine fails loudly instead of writing empty
files.

Sanity check before touching the real corpus — one chapter, a stub that only
prefixes:

```sh
python3 mt/translate.py --route zh-my --engine cmd \
    --cmd-template "sed 's/^/MY:/'" --only 1 --out-dir /tmp/mt-check
head -3 /tmp/mt-check/zh-my/book.my.txt
```

Then the real run, chapters 1–2:

```sh
python3 mt/translate.py --route zh-my --engine cmd \
    --cmd-template "$MT_ENGINE_COMMAND" \
    --engine-note '<what is actually installed>' \
    --only 1 --only 2
```

## The two routes, and why both

| route | input | use |
|---|---|---|
| `zh-my` | Chinese chapters | direct MT — first disagreement signal |
| `en-my` | the `zh-en` output | pivot MT — a second, independent-ish path |

The pivot route reads `content/mtranslate/zh-en/chapters/`, so run `zh-en`
first:

```sh
python3 mt/translate.py --route zh-en --engine offline --only 1 --only 2
python3 mt/translate.py --route en-my --engine cmd --cmd-template "$MT_ENGINE_COMMAND" \
    --only 1 --only 2
```

Redirect the output directory if you want both candidates side by side:

```sh
python3 mt/translate.py --route zh-my --engine cmd --cmd-template "$A" \
    --out-dir content/mtranslate/candidate-a --only 1 --only 2
python3 mt/translate.py --route zh-my --engine cmd --cmd-template "$B" \
    --out-dir content/mtranslate/candidate-b --only 1 --only 2
```

`mt/pivot.py --compare` diffs them.

## The glossary route is not MT

`--engine glossary` reads two dictionaries (CC-CEDICT, then English→Burmese) and
prints one line per Chinese word:

```
世界→ကမ္ဘာ/ကမ္ဘာမြေ
穿越→ဖြတ်သည်/ကျော်သည်
帝都→∅
```

That is a **sense list**, not a translation: word order is the source order, no
grammar is applied, and 36% of words in chapters 1–2 have no entry at all
(`∅`). It is the right tool for "what can this word mean", and the wrong tool
for "how does this sentence read". Never place it beside the AI translation as
a peer — it belongs with the dictionary, not with the MT columns.

The dictionaries are committed nowhere and rebuild in seconds:

```sh
python3 format/fetch_dicts.py           # CC-CEDICT 8.6 MB + en-my 16.7 MB, sha256 verified
python3 mt/translate.py --route zh-my --engine glossary --only 1 --only 2
```

## How the MT is used, and how it is not

It is **evidence, not truth**. For each AI-translated sentence the agent may
consult:

- the Chinese original — authority on meaning,
- `zh-my` and `en-my` MT — two weak readers, useful when they agree against
  the AI sentence,
- the human Burmese in the docx — authority on tone, damaged spelling and all,
- the overview in `content/review/burmese-overview.md` — background.

Agreement between MT and AI is not proof of correctness; both can be wrong the
same way. Disagreement is only a prompt to go back to the Chinese.

The MT columns never supply wording. They are not a style source and are never
edited.

## If the engine is a model in a git clone

Model repositories are cloned, not pip-installed, so they are gone with the
same wipe. Record what to re-clone in the note:

```sh
--engine-note 'nllb-200-distilled-600M int8, ct2, cpu, cloned from <url> @ <sha>'
```

Then re-cloning is a copy-paste, not an archaeology exercise.
