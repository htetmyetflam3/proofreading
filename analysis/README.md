# Reference data audit — not a grammar resolver

`reference-data-audit.json` records observations from the actual tagged DOCX and
loads the supplied `top`, `resolution` and rule catalogs. It is **not** a parsed
compound/sentence result or an MT-quality score.

Verified reference totals: 12,096 tagger units; 625,428 raw tag occurrences;
106,612 unknown and 270,880 ambiguous occurrences. A surface can belong to
several roles, so lexical-binding hit counts overlap and must not be read as
accuracy or resolved-role counts.

The supplied sequence catalog has 353 records. Its word-composition part has
38 rules (15 noun, 10 verb, 4 adjective, 9 adverb); 9 further records describe
compound clauses. These are separate stages. The former flat POS-window
matching/counting has been removed rather than presented as composition.

The comparison contract supplied by the owner is preserved:

- lexical components → compound candidates with children/spans → outer grammar;
- LSE (literature style in essay) by default outside character speech;
- LSN (narration style) for quoted character speech;
- particle decisions use sentence style **and** grammatical role via `top` and
  `resolution`, not a global surface replacement;
- lexical noun/verb/adjective/adverb overlap needs rule-governed contextual roles.

That resolver and validated cross-language 1:1 phrase alignment remain pending.
The current step obtains direct Chinese→Burmese and English-pivot Burmese MT
candidates. `MT.md` has the commands and API setup guidance. No live MT or AI
translation was used to create this audit, and no automatic correction is enabled.
