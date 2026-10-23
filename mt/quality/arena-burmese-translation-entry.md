# Paste this as the Arena agent's task entry

Translate Chinese chapters 194 and 195 into Burmese, following the unified workflow
in `mt/quality/START.md` and the detailed Burmese rules in
`mt/quality/finetune-agent-prompt.md`.

The final target is **Burmese**. First compare the retained API English and local
Argos English against the original Chinese using the bounded comparison tool. If the
API English is accurate enough, use it as a bridge into Burmese; if it is not,
correct it in working context against Chinese before translating. Then verify the
Burmese against Chinese. English review is a required quality gate, not a separate
English-only task or final deliverable.

No API calls and no API-generated Burmese. Do not stop because the Burmese `my`
field is absent; it is expected. Do not edit `english.txt`, `zh-en.txt`, `en-zh.txt`,
the Chinese source, the human Burmese source, or the DOCX. Save the fresh Burmese
work as an unapproved draft using the existing draft tools, without fabricating an
API source string.

Before starting, ensure the MCP server advertises the required tools; launch it
with `--tools burmese-translation` (or no tool filter). In particular, `lean` does
not advertise `register_name`, while `english-review` lacks chapter-reading, draft,
and verse tools. If a tool is missing, request the proper preset or use the direct
`python3 mcp.py --register-name ...` CLI; do not claim the repository lacks it.

Read the review, use `EtoBnames.txt` as the canonical name list, consult damaged
human Burmese only as uncertain prior context, and apply the formal-narration /
colloquial-dialogue distinction. Use the existing tools for bounded source reading,
English alignment, name checks/registration, Burmese segmentation, draft saving, and
export. Handle poems, songs, maxims, and philosophical lines in a separate
verse-focused session/pass and export their review separately; their English aid is
not the final translation.

Work chapter-by-chapter: complete 194 and report, then handle 195 in a separate
session. Return Burmese translations, a concise note on any English-bridge
corrections, names registered, verse handled, and unresolved uncertainties. Do not
continue beyond chapter 195 unless asked.
