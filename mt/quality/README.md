# Quality tools and translation workflow

## Active chapter task

The final target is Burmese. The retained API English and local Argos English are
checked against Chinese first; accurate-enough English is used as a bridge, and
any correction is kept in working context before producing Burmese. This English
quality gate is part of the Burmese translation task, not a separate English-only
assignment.

- Start card: [`START.md`](START.md)
- Paste-ready task: [`arena-burmese-translation-entry.md`](arena-burmese-translation-entry.md)
- English gate procedure: [`english-review-task.md`](english-review-task.md)
- Detailed Burmese style, terminology, and verse rules:
  [`finetune-agent-prompt.md`](finetune-agent-prompt.md)
- `arena-english-review-entry.md` is a redirect to the unified task.

The API-generated Burmese output was removed. Do not call an API or use
`read_chapter`'s legacy `my` field as a prerequisite; for 194 onward it is
expected to be absent. Use the aligned Chinese/English tools, register names,
save Burmese drafts, and handle poems/philosophy in a separate verse pass.

---

## Quality probes (read-only)

Scratch-free analysis of the Engine against real chapters. Nothing here writes
to `Engine/`, `master.json`, the POS tree or the caches.

| file | what it does |
|---|---|
| `units.mjs` | the **syllable-only** path — `bridgeSyllable()`, tagger never constructed |
| `tag-both.mjs` | same pipeline with both writers (`syllable:true, rawPos:true`) |
| `tag.py` | drives both, parses word view + unit view, aligns units to words |
| `profile.py` | per-chapter numbers: lengths, register, fragments, spacing, coverage |

```bash
# units the segmentor produces, no POS at all
node --import ./scraper/wasm/box/runtime-guard.mjs mt/quality/units.mjs SRC WORK OUT.json

# word view + unit view
node --import ./scraper/wasm/box/runtime-guard.mjs mt/quality/tag-both.mjs SRC WORK OUT.json

# chapter numbers for the two-chapter assessment
python3 mt/quality/profile.py --chapter 1 --chapter 2 --json mt/quality/ch01-02-profile.json
```

## What the probes established (2026-10-21)

The segmentor, not the POS tree, breaks these clusters. Same output with the
tagger never built:

| input | units emitted |
|---|---|
| `သူ့` | `သူ့` |
| `သင့်` | `သင်` · `့` |
| `ပြည့်` | `ပြည်` · `့` |
| `ကျောင်း` | `ကျောင်း` |
| `ရှန်း` | `ရှ` · `န်` · `း` |
| `ဗုဒ္ဓ` | `ဗု` · `ဒ` · `္ဓ` |
| `ခန္ဓာ` | `ခ` · `န` · `္ဓ` · `ာ` |
| `အင်္ဂလိပ်` | `အ` · `င` · `်္` · `ဂ` · `လိပ်` |

`ကြောင့်`, `နှင့်`, `ပြည့်` are present in both the unit table
(`syllable.mapped.txt`) and `master.json` (WIBAT/SPLIT/CONJUNCTION/PARTICLE/VERB
entries). The split is upstream of both, so `{?}` on a mark is an engine
artifact, never evidence of bad text.

Genuine gaps:

- **Fixed** — `syllables.pali` (732 units, e.g. `န္ဓာ`, `ဒ္ဓ`, `က္က`) used to be
  dropped by the syllable loader, so no Pali dictionary entry could be reached
  and every `္` cluster split. The loader now reads both lists and the cache is
  rebuilt: 3,229 units, 0 blocked entries, `ဗုဒ္ဓ` and `ခန္ဓာ` whole.
- Still open: `ကမ္ဘာ` is absent from the dictionary (`ကမ္ဘ` = 0 hits; only Pali
  `သမ္ဘာ` and friends). It now segments as `က · မ္ဘာ` — the correct smallest
  units — but no entry joins them into a word.
