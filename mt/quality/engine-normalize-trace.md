# Trace: why segmentation breaks in `proofreading` but not in `linga`/architecture

Question asked: did an agent corrupt `normalize` (lowercase `e` vs uppercase `E`)?
Answer: **no. `normalize` is untouched. The call site in `generators/input.js`
calls the wrong composite, and the reorder step inside it flips the mark order
that `mapperStr` depends on.**

## 1. The map code is byte-identical in both checkouts

```
Engine/MonoSyllabism/mapbuilder/base/function.js      SAME (sha256 matches build-info.json)
Engine/MonoSyllabism/mapbuilder/base/normalize.js     SAME (sha256 matches build-info.json)
Engine/MonoSyllabism/mapbuilder/base/sourceMap.js     SAME (sha256 matches build-info.json)
Engine/MonoSyllabism/mapbuilder/base/sourceMapper.js  SAME (sha256 matches build-info.json)
Engine/knowledge/isTreasure/master.json               SAME (sha256 matches build-info.json)
```

All five inputs match the hashes recorded in `scraper/wasm/box/build-info.json`,
which means the WASM box was built from exactly the files on disk — and those
files are byte-identical to the `architecture` branch. `normalize()` output is
identical in both checkouts for every probe.

## 2. The difference is which function `readAndPrepare` calls

| checkout | `generators/input.js` |
|---|---|
| `linga` architecture | `normalize(block)` → `mapperStr(cleaned)` |
| `proofreading` | `mapperNormalize(block)` |

`mapperNormalize` is `normalize` **→ `reorderAndWrap` →** `mapperStr`
(`normalize.js`). The extra step is the whole bug.

## 3. Step-by-step, using the base sources directly

Input `သင့်` — 4 code points. Both spellings tested.

```
input            သ င ် ့           101E 1004 103A 1037
  normalize      သ င ့ ်           101E 1004 1037 103A     ← dot before asat
  reorderAndWrap သ င ် ့           101E 1004 103A 1037     ← flipped back
  mapperStr(norm)  "YE¿^"                                  ← correct, what the tree holds
  mapperStr(reord) "Ye¿"                                   ← lowercase e, caret lost
```

`reorderAndWrap` sorts marks with `mapData.Priority`:

```
U+103A ် asat      priority 14
U+1037 ့ dot       priority 15     → asat sorts before dot
U+1038 း visarga   priority 16
U+1036 ံ anusvara  priority 13
```

And `compose()` (`function.js`) has this rule:

```js
/([A-Z])\^\$|\$([A-Z])|\$([a-z])|\$([^A-Za-z])|([A-Z])\^/g
...
if (upper) return String.fromCharCode(upper.charCodeAt(0) + 32);
```

`X^` means "base + asat" and becomes the lowercase tail token `x`. So when
reorder puts `်` immediately after `င`, `E^` collapses to `e` and the dot `့` is
left stranded: `YE¿^` → `Ye¿`.

The POS tree is built with `buildSyllableLookup()`, which maps each syllable
through `MyNormalize` = `normalize` → `deleteEnglishBlocks` → `mapperStr` — no
reorder. So the tree holds `YE¿^` while the segmentor is fed `Ye¿`. No match →
one mark per token.

## 4. Measured end to end (chapters 1–2, same tree, same segmentor)

| encoder | ch01 mark-fragments | ch02 mark-fragments |
|---|---|---|
| `mapperNormalize` (current) | 111 / 2080 = 5.34% | 136 / 2354 = 5.78% |
| `normalize` + `mapperStr` (linga) | 63 / 2025 = 3.11% | 62 / 2280 = 2.72% |
| `mapperNormalize` with Priority swapped | **63 / 2031 = 3.10%** | **62 / 2281 = 2.72%** |

POS `{?}` barely moves (13.7% / 15.0% → 13.7% / 15.3%) because those leftovers
are dictionary gaps (`ကမ္ဘာ`, `ခန္ဓာ`, `ဧ`, `၏` standalone-id mismatch, loan
stacks) — a different cause from this one.

## 5. Why the agent changed it (and why reverting alone is not enough)

`normalize + mapperStr` leaves Latin/digit blocks unmasked, and `mapperStr` maps
`A–Z` onto Burmese bases — "Hello 123" becomes `ညင် ဏ် ဏ် ဒ်` garbage.
`reorderAndWrap` is what wraps English into `{...}` blocks. So the intention was
right; the composite was wrong.

Two ways out, both keep the masking:

1. **Swap the two Priority values** (`့` → 14, `်` → 15) so `reorderAndWrap`
   preserves the order `compose()` expects. Verified:

   ```
   mapperNormalize("သင့်")          → "YE¿^"
   mapperNormalize("Hello 123 သင့် ok") → "{Hello} {123} YE¿^ {ok}"
   ```

   Cost: `Priority` lives in `master.json → mapData`, which is sealed into the
   WASM box — needs a re-seal/rebuild, not a text edit.

2. **Keep `input.js` on `normalize + mapperStr`** for Burmese lines and mask
   Latin blocks before mapping. No box rebuild, but changes `input.js`.

## 6. What could not be verified

`Engine/MonoSyllabism/generators/input.js` has exactly one commit in this
checkout (`f50a1d6`, a squashed merge), so there is no history to name the commit
or author that introduced `mapperNormalize`. The content difference against the
architecture branch is the evidence, not a blame trail.
