# English quality gate for the Burmese translation task

This is **Phase 1 of the Chinese → Burmese workflow**, not a separate English-only
assignment. The final target is Burmese. First make sure the retained API English is
accurate enough against Chinese to serve as a bridge. If it is not, correct the
meaning in a working copy, then continue into Burmese. Do not stop after reporting
English corrections.

## Inputs and constraints

- Chinese source: `content/source/chinese-0511241012-from-8011_1.txt` (also available
  in bounded form through the chapter tools).
- Retained API English: `content/mtranslate/english.txt`.
- Local Chinese→English Argos witness: `content/mtranslate/zh-en.txt`.
- Final target: a fresh Burmese draft. There is no API-generated Burmese baseline.

Do not call an API. Do not write corrections into `english.txt`, the Argos files, or
any source file. Keep the corrected English only as the working bridge for the
Burmese translation. Chinese controls meaning; local Argos English is a fallible
second witness.

## Compare bounded, aligned windows

Use the current Chinese chapter number and ten-paragraph windows:

```text
compare_english_chapter {"chapter": 194, "start": 1, "count": 10}
compare_english_chapter {"chapter": 195, "start": 1, "count": 10}
```

Each row aligns the Chinese (`zh`), local machine English (`machine_en`), and
retained API English (`api_en`). Read the alignment metadata before judging. Continue
only at `window.next_start`. If a source is missing or alignment fails, stop and
report the exact limitation; never shift rows by eye or fill missing text from
memory.

For each passage:

1. Compare API English to Chinese for meaning, omissions, additions, names, and
   paragraph alignment; use local machine English as a cross-check, not a verdict.
2. If API English is faithful enough, use it as the meaning bridge into Burmese.
3. If it is not, prepare a corrected English working version grounded in Chinese;
   then translate that corrected meaning into Burmese.
4. Recheck the resulting Burmese against Chinese so English errors do not propagate.

The English corrections are intermediate work, not the final deliverable. Do not
return an English-only review when the assigned task is Burmese translation.

## Names and prior Burmese context

For an uncertain recurring term, consult `previous_burmese_context` with a
Burmese-script keyword and the current Chinese chapter:

```text
previous_burmese_context {"chapter": 194, "keyword": "နတ်"}
```

The prior human Burmese source has known encoding damage; use it only as an uncertain
context clue. Do not copy corrupted spellings or treat it as a meaning authority.
Use `content/reference/EtoBnames.txt` for canonical Burmese names and terms, with
`lookup_name`, `check_names`, and `register_name` as directed by the Burmese task.

## Stop condition

Stop only for unavailable source text, broken alignment, or an ambiguity that cannot
be resolved from the Chinese and available context—not because the Burmese `my`
field is absent. For chapters 194 onward, the absence of API Burmese is expected.
After the English gate, continue to the Burmese translation phase described in
`mt/quality/START.md`.
