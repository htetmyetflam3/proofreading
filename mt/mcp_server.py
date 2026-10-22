#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""A local MCP (stdio) server for the RapidAPI multi-format translator.

Speaks newline-delimited JSON-RPC 2.0 on stdin/stdout, so any MCP client that
can launch a command works: Claude Desktop, Claude Code, Cursor, Zed, ...

    python3 mt/mcp_server.py --print-config --client kilo   # config snippet
    python3 mt/mcp_server.py --install-config --client kilo # write it
    python3 mt/mcp_server.py --selftest                     # no-network check
    python3 mt/mcp_server.py                                # serve on stdio

Tools:

    detect_language      language code/name for a string
    translate_text       one string, any supported pair
    translate_batch      many strings in one request (cache-aware)
    translate_chapters   run mt/api_translate.py on the local Chinese novel,
                         writing JSONL/TXT/compare/report files

The key comes from `RAPIDAPI_KEY` in the server environment. Nothing is printed
to stdout except protocol messages; diagnostics go to stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from rapidapi_translator import (  # noqa: E402
    CACHE_ENV,
    DEFAULT_CACHE,
    HOST,
    KEY_ENV,
    MAX_REQUEST_CHARS,
    MAX_REQUEST_ITEMS,
    CachedTranslator,
    TranslatorError,
    load_env_file,
)

SERVER_NAME = "rapidapi-translator"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07")
DEFAULT_PROTOCOL = "2024-11-05"

INSTRUCTIONS = (
    "Translation tools backed by the RapidAPI 'Multi format AI translator' API. "
    f"The API key is read from {KEY_ENV}. `translate_chapters` translates ONE "
    "PAIR of chapters of the local Chinese novel, two chapters at most, and "
    "writes files under content/mtranslate/rapidapi; it costs about five "
    "requests per chapter. Omit `chapters` for the next pair after the human "
    "translation (194+195, then 196+197). Check the free plan first with "
    "`mt/apicaller.py` or `mt/api_translate.py --plan`."
)

TOOLS = [
    {
        "name": "detect_language",
        "description": "Detect the language of a text with the RapidAPI translator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to analyse."},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "translate_text",
        "description": "Translate one string. One API request per call unless cached.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to translate."},
                "target": {"type": "string", "description": "Target language code.",
                           "default": "my"},
                "source": {"type": "string", "description": "Source code or 'auto'.",
                           "default": "auto"},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "translate_batch",
        "description": "Translate many strings in as few requests as possible. "
                       "Only strings missing from the local cache are sent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "texts": {"type": "array", "items": {"type": "string"},
                          "description": "Strings, translated in input order."},
                "target": {"type": "string", "description": "Target language code.",
                           "default": "my"},
                "source": {"type": "string", "description": "Source code or 'auto'.",
                           "default": "auto"},
            },
            "required": ["texts"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_chapter",
        "description": "Read one Chinese chapter with stable paragraph ids. Each "
                       "paragraph carries `my`, the API's Burmese, once "
                       "api_translate.py has produced it; the existing human Burmese "
                       "of the same chapter comes back as a style reference; and the "
                       "response says which paragraphs already have drafts. Call this "
                       "first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter": {"type": "integer", "description": "Chinese chapter number."},
                "translations": {"type": "string",
                                 "description": "Directory holding chNNNN.my.jsonl from "
                                                "api_translate.py; default "
                                                "content/mtranslate/rapidapi."},
                "reference_lines": {"type": "integer",
                                    "description": "How many existing Burmese lines to "
                                                   "include as a style reference.",
                                    "default": 60},
            },
            "required": ["chapter"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_draft",
        "description": "Store the agent's adjusted Burmese for one paragraph. It is "
                       "kept as a draft with the AI translation it started from; it "
                       "never overwrites the translation and is never approved text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter": {"type": "integer"},
                "paragraph": {"type": "string",
                              "description": "1-based index or a paragraph id from "
                                             "read_chapter."},
                "draft": {"type": "string", "description": "Adjusted Burmese text."},
                "ai_text": {"type": "string",
                            "description": "AI translation (RapidAPI output) this draft "
                                           "started from. Not the legacy MT column."},
                "mt": {"type": "string",
                       "description": "Deprecated alias of ai_text, kept for old callers."},
                "model": {"type": "string", "description": "Which model wrote it."},
                "note": {"type": "string", "description": "Optional note."},
            },
            "required": ["chapter", "paragraph", "draft"],
            "additionalProperties": False,
        },
    },
    {
        "name": "export_drafts",
        "description": "Write the drafted chapter as text plus a Chinese / AI / "
                       "draft comparison, and report which paragraphs are still missing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter": {"type": "integer"},
                "out_dir": {"type": "string",
                            "description": "Default content/mtranslate/drafts."},
                "require_all": {"type": "boolean", "default": False},
            },
            "required": ["chapter"],
            "additionalProperties": False,
        },
    },
    {
        "name": "lookup_word",
        "description": "Read-only dictionary probe. Says whether a spelling is an entry, "
                       "its POS families, whether the POS tree can reach it, and returns "
                       "dictionary-proved repairs for storage-order damage "
                       "(e.g. အေခြအေန -> အခြေအနေ, ဘ၀ -> ဘဝ). A suggestion is only "
                       "returned when the written form is not an entry and the repaired "
                       "form is.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "The spelling to check."},
            },
            "required": ["word"],
            "additionalProperties": False,
        },
    },
    {
        "name": "review_lookup",
        "description": "Read-only lookup into content/review/burmese-overview.md, the "
                       "background document: characters, arcs, and the dossier of known "
                       "translation errors in the human Burmese. Use it during editing "
                       "when you have forgotten a character's nature, a rank, or how a "
                       "term was ruled on. Returns one matching section, not the whole "
                       "document. Never imitate its conversational register — it is "
                       "notes about the novel, not the novel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Character name, Chinese term, or words to find."},
                "section": {"type": "string",
                            "description": "Exact section id, skips the search."},
                "chapter": {"type": "integer",
                            "description": "Return the arc that covers this chapter."},
                "limit": {"type": "integer", "default": 2},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "review_brief",
        "description": "The whole review in one round: the character table, the known "
                       "translation defects, the reviewer's verdict, and every story "
                       "arc's title with its opening. Call this ONCE at the start of a "
                       "session instead of reading the 7,279-line document. Its voice "
                       "is casual on purpose and is NOT the author's tone; its Burmese "
                       "quotes may carry PDF damage.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chars_per_arc": {"type": "integer", "default": 420,
                                  "description": "Story characters per arc; lower it "
                                                 "if the session is already long."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "lookup_name",
        "description": "The name list (content/reference/EtoBnames.txt) is the "
                       "authority for how a name or term is written in Burmese. Look "
                       "one up by its key (Ye Nin) or by a Burmese form (ယဲ့နင်). Omit "
                       "`term` to list every entry. A term the list knows is written "
                       "exactly as the list writes it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "Key or Burmese form."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "check_names",
        "description": "Report which listed names occur in a Burmese text, and which "
                       "spellings look like a variant of a listed name. A report, not a "
                       "rewriter: rewrite to the canonical form yourself. A name the "
                       "list spells correctly wins even when the text's spelling is also "
                       "correct Burmese.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "description": "One paragraph or sentence of Burmese."},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "register_name",
        "description": "Append a genuinely new term to content/reference/EtoBnames.txt. "
                       "The record has two sides and nothing else: `key` is the English "
                       "as the zh-en column writes it, `burmese` is the form the AI "
                       "translation used (corrected by you when it is wrong). No "
                       "categories. A term is not only a person: a weapon, a martial "
                       "art, a bloodline ability, a pill, a rank or a place is "
                       "registered the same way when it will recur — 'Golden Eagle "
                       "Saber' must be registered even though it translates cleanly on "
                       "its own, because the API will not spell it the same way in "
                       "chapter 212. Use it only when no entry exists (check with "
                       "lookup_name first), never invent an alternative spelling for "
                       "something already listed, and never replace an existing entry: "
                       "if an entry looks wrong, flag it in your report instead.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string",
                        "description": "The English term as the zh-en column writes it, "
                                       "e.g. 'Shen Ji' or 'Golden Eagle Saber'."},
                "burmese": {"type": "string",
                            "description": "The Burmese form, taken from the AI "
                                           "translation and corrected if needed."},
                "note": {"type": "string",
                         "description": "Optional note: where it first appears."},
            },
            "required": ["key", "burmese"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_verse",
        "description": "Record ONE line you judged to be verse — a poem, a song, a "
                       "maxim, an inscription, a philosophy line — with an English "
                       "version for the human to review. YOU decide what is verse: no "
                       "tool extracts it, because the boundary between a short sentence "
                       "and a line of poetry is a reading judgement and you are the one "
                       "reading. Do this while you re-match tone, when you already have "
                       "the paragraph in front of you. Write the English yourself or "
                       "quote the zh-en column (`mt/verse.py mt <chapter>` prints it "
                       "numbered); say which with `english_source`. Use kind `none` once "
                       "if the chapter genuinely has no verse — that is different from "
                       "never having looked.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapter": {"type": "integer"},
                "paragraph": {"type": "string",
                              "description": "1-based index or a paragraph id from "
                                             "read_chapter. Omit only for kind `none`."},
                "kind": {"type": "string",
                         "enum": ["poem", "philosophy", "song", "inscription",
                                  "maxim", "other", "none"],
                         "description": "What the line is. `none` records that the "
                                        "chapter has no verse at all."},
                "english": {"type": "string",
                            "description": "The English version of this line."},
                "english_source": {"type": "string", "enum": ["mt", "own", "mixed"],
                                   "default": "own",
                                   "description": "`mt` = the zh-en column verbatim, "
                                                  "`own` = your own rendering, `mixed` "
                                                  "= quoted then rewritten."},
                "mt_english": {"type": "string",
                               "description": "The zh-en line you started from, if any."},
                "note": {"type": "string",
                         "description": "Why this line is verse, and what to watch in "
                                        "the Burmese."},
                "model": {"type": "string"},
            },
            "required": ["chapter", "kind"],
            "additionalProperties": False,
        },
    },
    {
        "name": "export_verse",
        "description": "Write the chapter's verse section — Chinese, the zh-en line, "
                       "your English, and why — to content/mtranslate/verse/"
                       "chNNNN.verse.md, which is the 'separate section for careful "
                       "review' at the end of the chapter. Returns the file, the line "
                       "count and whether the chapter was checked at all (`none`).",
        "inputSchema": {
            "type": "object",
            "properties": {"chapter": {"type": "integer"}},
            "required": ["chapter"],
            "additionalProperties": False,
        },
    },
    {
        "name": "segment_text",
        "description": "Read-only segmentation probe. Runs the repository engine on the "
                       "text and returns every token with its smallest units and POS "
                       "candidates, plus which tokens are split clusters and why "
                       "(word / unit / loan / unknown), plus character coverage. "
                       "Use it before rewriting a sentence; {?} tags are NOT error "
                       "signals on their own.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "One or more sentences."},
            },
            "required": ["text"],
            "additionalProperties": False,
        },
    },
    {
        "name": "translate_chapters",
        "description": "Translate ONE PAIR of chapters of the local Chinese "
                       "novel (two at most; a third is refused) and write "
                       "JSONL, TXT, a comparison markdown and a report. Omit "
                       "`chapters` for the next pair after the human "
                       "translation that is not on disk yet, e.g. 194+195 then "
                       "196+197. Costs ~5 requests per chapter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapters": {"type": "string",
                             "description": "One or two chapters: '194&195', "
                                            "'194+195', '194,195' or '194'. "
                                            "Omit for the next pair."},
                "target": {"type": "string", "description": "Target language code.",
                           "default": "my"},
                "source": {"type": "string", "description": "Source code or 'auto'.",
                           "default": "auto"},
                "out_dir": {"type": "string",
                            "description": "Output directory; default "
                                           "content/mtranslate/rapidapi."},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]


class Server:
    def __init__(self, *, cache_path: Path | str | None = None, enabled_cache: bool = True,
                 max_chars: int = MAX_REQUEST_CHARS,
                 max_items: int = MAX_REQUEST_ITEMS,
                 timeout: float = 60.0, max_attempts: int = 3,
                 source_file: Path | str | None = None,
                 existing: Path | str | None = None,
                 out_dir: Path | str | None = None,
                 draft_store: Path | str | None = None,
                 docx: Path | str | None = None) -> None:
        self.cache_path = cache_path
        self.enabled_cache = enabled_cache
        self.max_chars = max_chars
        self.max_items = max_items
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.source_file = source_file
        self.existing = existing
        self.draft_store = draft_store
        self.docx = docx
        self.out_dir = out_dir
        self._translator: CachedTranslator | None = None
        self._drafts = None

    @property
    def translator(self) -> CachedTranslator:
        if self._translator is None:
            self._translator = CachedTranslator(
                cache_path=self.cache_path, enabled=self.enabled_cache,
                timeout=self.timeout, max_attempts=self.max_attempts,
                max_chars=self.max_chars, max_items=self.max_items)
        return self._translator

    @property
    def drafts(self):
        """Opened lazily so read-only tools never create a database."""
        if self._drafts is None:
            from agent_work import DraftStore  # noqa: PLC0415
            store = self.draft_store or None
            self._drafts = DraftStore(store) if store else DraftStore()
        return self._drafts

    # -- tools -------------------------------------------------------

    @staticmethod
    def _text_arg(arguments: dict, name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"`{name}` must be a non-empty string")
        return value

    @staticmethod
    def _language(value: str, name: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"`{name}` must be a language code")
        return value

    def call_tool(self, name: str, arguments: dict) -> dict:
        if name == "read_chapter":
            chapter = self._chapter_arg(arguments)
            return self._read_chapter(chapter, arguments)
        if name == "save_draft":
            return self._save_draft(arguments)
        if name == "export_drafts":
            chapter = self._chapter_arg(arguments)
            out_dir = arguments.get("out_dir")
            from api_translate import CHINESE  # noqa: PLC0415
            return self.drafts.export(
                chapter, Path(out_dir) if out_dir else Path(
                    self.out_dir or "content/mtranslate/drafts"),
                require_all=bool(arguments.get("require_all", False)),
                source=Path(self.source_file or CHINESE))
        if name == "detect_language":
            text = self._text_arg(arguments, "text")
            return self.translator.detect(text)
        if name == "translate_text":
            text = self._text_arg(arguments, "text")
            target = self._language(arguments.get("target", "my"), "target")
            source = self._language(arguments.get("source", "auto"), "source")
            translated = self.translator.translate(text, target, source)
            return {"translated_text": translated, "target": target, "source": source}
        if name == "translate_batch":
            texts = arguments.get("texts")
            if not isinstance(texts, list) or not texts or not all(
                    isinstance(item, str) and item.strip() for item in texts):
                raise ValueError("`texts` must be a non-empty array of non-empty strings")
            target = self._language(arguments.get("target", "my"), "target")
            source = self._language(arguments.get("source", "auto"), "source")
            result = self.translator.translate_batch(texts, target, source)
            return {
                "translations": result.texts,
                "source_language": result.source_language,
                "source_language_name": result.source_language_name,
                "requests": result.requests,
                "cached": result.cached,
            }
        if name == "lookup_word":
            word = self._text_arg(arguments, "word")
            from lexicon import lookup, suggest  # noqa: PLC0415
            result = lookup(word)
            result["repairs"] = suggest(word)
            return result
        if name == "segment_text":
            text = self._text_arg(arguments, "text")
            from lexicon import segment  # noqa: PLC0415
            return segment(text)
        if name == "review_lookup":
            return self._review_lookup(arguments)
        if name == "review_brief":
            return self._review_brief(arguments)
        if name == "lookup_name":
            return self._lookup_name(arguments)
        if name == "check_names":
            return self._check_names(arguments)
        if name == "register_name":
            return self._register_name(arguments)
        if name == "save_verse":
            return self._save_verse(arguments)
        if name == "export_verse":
            return self._export_verse(arguments)
        if name == "translate_chapters":
            return self._translate_chapters(arguments)
        raise KeyError(name)

    @staticmethod
    def _chapter_arg(arguments: dict) -> int:
        value = arguments.get("chapter")
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("`chapter` must be a chapter number")
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError("`chapter` must be a chapter number") from None

    def _review_lookup(self, arguments: dict) -> dict:
        """One section of the background document, never the whole file."""
        import overview_index  # noqa: PLC0415
        index_path = ROOT / "content" / "review" / "overview.yaml"
        source = ROOT / "content" / "review" / "burmese-overview.md"
        if not index_path.is_file():
            raise ValueError("content/review/overview.yaml is missing — run "
                             "`python3 mt/overview_index.py --build`")
        index = overview_index.load(index_path)
        lines = source.read_text(encoding="utf-8").splitlines()
        limit = int(arguments.get("limit", 2))

        def render(section: dict) -> dict:
            start = section["lines"][0]
            end = overview_index.own_end(section, index["sections"])
            body = lines[start - 1:end]
            return {
                "id": section["id"],
                "kind": section["kind"],
                "title": section["title"],
                "lines": [start, end],
                "text": "\n".join(body[:overview_index.MAX_LINES]).strip(),
                "truncated": len(body) > overview_index.MAX_LINES,
            }

        if arguments.get("section"):
            wanted = str(arguments["section"]).strip()
            match = next((s for s in index["sections"] if s["id"] == wanted), None)
            if match is None:
                raise ValueError(f"no section {wanted!r}; use `query` to search")
            return {"matches": [render(match)], "count": 1}

        if arguments.get("chapter") is not None:
            chapter = int(arguments["chapter"])
            arcs = [s for s in index["sections"] if s["kind"] == "arc"
                    and len(s["chapters"]) == 2
                    and s["chapters"][0] <= chapter <= s["chapters"][1]]
            if not arcs:
                raise ValueError(f"chapter {chapter} is outside the indexed arcs")
            arc = arcs[0]
            children = [s for s in index["sections"] if s.get("parent") == arc["id"]]
            return {"chapter": chapter, "arc": render(arc),
                    "parts": [{k: s[k] for k in ("id", "kind", "title", "lines")}
                              for s in children],
                    "count": 1 + len(children)}

        query = str(arguments.get("query", "")).strip()
        if not query:
            raise ValueError("pass `query`, `section`, or `chapter`")
        words = query.lower().split()
        hits = []
        for section in index["sections"]:
            start = section["lines"][0]
            end = overview_index.own_end(section, index["sections"])
            body = "\n".join(lines[start - 1:end]).lower()
            if all(word in section["title"].lower() or word in body for word in words):
                hits.append(section)
        rank = {"character": 0, "issue": 1, "arc-title": 2}
        hits.sort(key=lambda s: (0 if s["title"].lower() == query.lower() else 1,
                                 rank.get(s["kind"], 3), s["lines"][0]))
        rows = [row for row in index.get("characters", [])
                if all(word in (row["name"] + row["role"] + row["relation"]).lower()
                       for word in words)]
        return {"matches": [render(s) for s in hits[:limit]],
                "characters": rows, "count": len(hits)}

    @staticmethod
    def _names_path(path: Path) -> str:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)

    def _review_brief(self, arguments: dict) -> dict:
        """The whole document in one bounded digest, for the start of a session."""
        import overview_index  # noqa: PLC0415
        index_path = ROOT / "content" / "review" / "overview.yaml"
        source = ROOT / "content" / "review" / "burmese-overview.md"
        if not index_path.is_file():
            raise ValueError("content/review/overview.yaml is missing — run "
                             "`python3 mt/overview_index.py --build`")
        try:
            per_arc = int(arguments.get("chars_per_arc", 420))
        except (TypeError, ValueError):
            raise ValueError("`chars_per_arc` must be a number") from None
        index = overview_index.load(index_path)
        text = overview_index.brief(source, index, chars_per_arc=per_arc)
        return {
            "markdown": text,
            "characters": len(index["characters"]),
            "sections": len(index["sections"]),
            "note": "facts and defects only; the review's voice is not the "
                    "author's tone, and its Burmese quotes may carry PDF damage",
            "next": "read_chapter for the chapter, then judge one paragraph at a time",
        }

    def _lookup_name(self, arguments: dict) -> dict:
        import names  # noqa: PLC0415
        result = names.load()
        term = arguments.get("term")
        if term is None or not str(term).strip():
            return {
                "file": self._names_path(names.NAMES_FILE),
                "count": len(result.entries),
                "entries": [entry.as_dict() for entry in result.entries],
                "note": "the list is the authority for spelling; reuse it, do not "
                        "coin a new form for a term it already lists",
            }
        found = names.lookup(result.entries, str(term))
        if not found:
            return {
                "file": self._names_path(names.NAMES_FILE),
                "count": 0,
                "entries": [],
                "suggestion": "no entry; check a variant spelling, or register it with "
                              "register_name if the entity is genuinely new",
            }
        return {"file": self._names_path(names.NAMES_FILE),
                "count": len(found),
                "entries": [entry.as_dict() for entry in found]}

    def _check_names(self, arguments: dict) -> dict:
        import names  # noqa: PLC0415
        text = arguments.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("`text` must be a non-empty string")
        result = names.load()
        found = names.hits(text, result.entries)
        suspects = names.variants(text, result.entries)
        return {
            "file": self._names_path(names.NAMES_FILE),
            "hits": found,
            "variants": suspects,
            "verdict": ("clean" if not suspects else
                        "rewrite each variant to its canonical form; the list wins "
                        "even when the text's spelling is also correct Burmese"),
        }

    def _register_name(self, arguments: dict) -> dict:
        import names  # noqa: PLC0415
        key = arguments.get("key")
        burmese = arguments.get("burmese")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("`key` must be a non-empty string")
        if not isinstance(burmese, str) or not burmese.strip():
            raise ValueError("`burmese` must be a non-empty string")
        note = arguments.get("note") or ""
        try:
            entry = names.add(names.NAMES_FILE, key, burmese, str(note))
        except ValueError as error:
            return {"added": None, "refused": str(error),
                    "note": "do not work around this: reuse the existing entry, "
                            "and flag the conflict in your report"}
        return {"added": entry.as_dict(),
                "file": self._names_path(names.NAMES_FILE),
                "note": "registered; every later occurrence must use this spelling"}

    def _save_verse(self, arguments: dict) -> dict:
        import verse  # noqa: PLC0415
        chapter = self._chapter_arg(arguments)
        kind = arguments.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("`kind` must be one of: " + ", ".join(verse.KINDS))
        english = arguments.get("english") or ""
        if not isinstance(english, str):
            raise ValueError("`english` must be a string")
        try:
            record = verse.save(
                chapter, kind=kind,
                paragraph=arguments.get("paragraph"),
                english=english,
                english_source=str(arguments.get("english_source", "own")),
                mt_english=arguments.get("mt_english"),
                note=str(arguments.get("note") or ""),
                model=arguments.get("model"))
        except verse.VerseError as error:
            raise ValueError(str(error)) from None
        return {"saved": record,
                "note": "the human reviews this section; it is not part of the draft",
                "next": "export_verse at the end of the chapter"}

    def _export_verse(self, arguments: dict) -> dict:
        import verse  # noqa: PLC0415
        chapter = self._chapter_arg(arguments)
        report = verse.export(chapter)
        if report["empty"]:
            report["warning"] = ("nothing recorded for this chapter — save_verse each "
                                 "line, or save_verse with kind `none` after checking")
        return report

    def _read_chapter(self, chapter: int, arguments: dict) -> dict:
        from agent_work import DEFAULT_OUT, read_chapter  # noqa: PLC0415
        from api_translate import BURMESE, CHINESE, DOCX  # noqa: PLC0415
        try:
            limit = int(arguments.get("reference_lines", 60))
        except (TypeError, ValueError):
            raise ValueError("`reference_lines` must be a number") from None
        translations = arguments.get("translations")
        return read_chapter(
            chapter,
            source=Path(self.source_file or CHINESE),
            existing=Path(self.existing or BURMESE),
            docx=Path(self.docx or DOCX),
            store=self.drafts,
            reference_lines_limit=max(0, limit),
            translations=Path(translations) if translations else None,
        )

    def _save_draft(self, arguments: dict) -> dict:
        from agent_work import DraftError, chapter_paragraphs_by_number, _select  # noqa: PLC0415
        from api_translate import CHINESE  # noqa: PLC0415
        chapter = self._chapter_arg(arguments)
        try:
            paragraph = _select(
                chapter_paragraphs_by_number(chapter,
                                             source=Path(self.source_file or CHINESE)),
                str(arguments.get("paragraph", "")))
        except DraftError as error:
            raise ValueError(str(error)) from None
        draft = arguments.get("draft")
        if not isinstance(draft, str) or not draft.strip():
            raise ValueError("`draft` must be a non-empty string")
        ai_text = arguments.get("ai_text") or arguments.get("mt")
        return self.drafts.save(paragraph, draft, ai_text=ai_text,
                                model=arguments.get("model"),
                                note=arguments.get("note"))

    def _translate_chapters(self, arguments: dict) -> dict:
        from apicaller import (  # noqa: PLC0415
            PairError, next_numbers, resolve, translate_pair,
        )
        from api_translate import BURMESE, CHINESE, DOCX, OUTPUT, chinese_chapters
        from chapter_map import ChapterMapError, load_or_derive

        spec = arguments.get("chapters")
        if spec is not None and not isinstance(spec, str):
            raise ValueError("`chapters` must be a string such as '194&195'")
        target = self._language(arguments.get("target", "my"), "target")
        source = self._language(arguments.get("source", "auto"), "source")
        out_dir = Path(arguments.get("out_dir") or self.out_dir or OUTPUT)
        chapters = chinese_chapters(Path(self.source_file or CHINESE))
        chapter_map = None
        try:
            chapter_map = load_or_derive(None, Path(self.docx or DOCX))
        except (ChapterMapError, OSError, KeyError):
            chapter_map = None
        try:
            numbers, selected, note = resolve(
                spec, chapters, chapter_map, out_dir=out_dir, target=target)
        except PairError as error:
            raise ValueError(str(error)) from error
        report = translate_pair(
            selected, chapter_map=chapter_map, target=target, source=source,
            out_dir=out_dir, cache_path=self.cache_path,
            enabled_cache=self.enabled_cache, max_chars=self.max_chars,
            max_items=self.max_items, timeout=self.timeout,
            attempts=self.max_attempts,
            existing=Path(self.existing or BURMESE))
        return {
            "target": report["target"],
            "detected": report["detected"],
            "requested": numbers,
            "selection": note,
            "totals": report["totals"],
            "chapters": report["chapters"],
            "files": report["files"],
            "elapsed_seconds": report["elapsed_seconds"],
            "next": next_numbers(chapter_map, chapters, out_dir=out_dir,
                                 target=target),
        }

    # -- protocol ----------------------------------------------------

    def handle(self, request: dict) -> dict | None:
        request_id = request.get("id")
        method = request.get("method")
        if not isinstance(method, str):
            return self._error(request_id, -32600, "invalid request: missing method")
        if request_id is None and method.startswith("notifications/"):
            return None
        if method == "initialize":
            offered = (request.get("params") or {}).get("protocolVersion")
            version = offered if offered in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
            return self._result(request_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            })
        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            return self._result(request_id, {"tools": TOOLS})
        if method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if not isinstance(name, str):
                return self._error(request_id, -32602, "missing tool name")
            if not isinstance(arguments, dict):
                return self._error(request_id, -32602, "arguments must be an object")
            try:
                payload = self.call_tool(name, arguments)
            except KeyError:
                return self._error(request_id, -32602, f"unknown tool: {name}")
            except (ValueError, TranslatorError) as error:
                return self._result(request_id, {
                    "content": [{"type": "text", "text": str(error)}],
                    "isError": True,
                })
            except Exception as error:  # pragma: no cover - defensive
                return self._result(request_id, {
                    "content": [{"type": "text",
                                 "text": f"{type(error).__name__}: {error}"}],
                    "isError": True,
                })
            return self._result(request_id, {
                "content": [{"type": "text",
                             "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                "isError": False,
            })
        if request_id is None:
            return None
        return self._error(request_id, -32601, f"method not found: {method}")

    @staticmethod
    def _result(request_id, result) -> dict:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": code, "message": message}}

    def serve(self, stdin=None, stdout=None) -> int:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as error:
                response = self._error(None, -32700, f"parse error: {error.msg}")
            else:
                if isinstance(request, dict):
                    try:
                        response = self.handle(request)
                    except Exception as error:  # pragma: no cover - defensive
                        response = self._error(request.get("id"), -32603,
                                               f"internal error: {error}")
                else:
                    response = self._error(None, -32600, "invalid request")
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()
        return 0


CLIENTS = ("json", "claude", "kilo", "codex", "gemini")


CONFIG_PATHS = {
    "kilo": ("~/.config/kilo/kilo.json", "mcp"),
    "gemini": ("~/.gemini/settings.json", "mcpServers"),
}


def _extra_args(env_file: Path | str | None) -> list[str]:
    return ["--env-file", str(Path(env_file).expanduser())] if env_file else []


def config_payload(client: str = "json", env_file: Path | str | None = None) -> dict:
    """The server entry in the shape that client expects.

    With `env_file`, the server reads the key from that file at startup and the
    entry carries no `environment` placeholder, so nothing has to be exported
    into the client's shell.
    """
    if client not in CLIENTS:
        raise ValueError(f"client must be one of {', '.join(CLIENTS)}")
    command = sys.executable
    server = str(Path(__file__).resolve())
    extra = _extra_args(env_file)
    environment = {} if env_file else {KEY_ENV: "{env:" + KEY_ENV + "}"}
    if client == "kilo":
        return {"mcp": {SERVER_NAME: {
            "type": "local",
            "command": [command, server, *extra],
            "enabled": True,
            **({"environment": environment} if environment else {}),
        }}}
    if client == "gemini":
        env = {} if env_file else {KEY_ENV: "${" + KEY_ENV + "}"}
        payload = {"command": command, "args": [server, *extra]}
        return {"mcpServers": {SERVER_NAME: dict(payload, **({"env": env} if env else {}))}}
    return {"mcpServers": {SERVER_NAME: {
        "command": command,
        "args": [server, *extra],
        "env": {KEY_ENV: "<your-rapidapi-key>"},
    }}}


def config_snippet(client: str = "json", env_file: Path | str | None = None) -> str:
    """Client config that keeps the key out of the file where the client can.

    `codex` forwards the variable with `env_vars`, `kilo` and `gemini` expand
    `{env:VAR}` / `${VAR}` at launch, and the `claude` snippet relies on the
    script inheriting the exported variable. Only the generic JSON (Claude
    Desktop and other GUI clients that do not expand variables) shows a
    placeholder value.
    """
    if client not in CLIENTS:
        raise ValueError(f"client must be one of {', '.join(CLIENTS)}")
    extra = _extra_args(env_file)
    if client == "claude":
        tail = " ".join(extra)
        return ("# export RAPIDAPI_KEY=... in this shell first, then:\n"
                f"claude mcp add --scope user {SERVER_NAME} -- "
                f"{sys.executable} {Path(__file__).resolve()}"
                + (f" {tail}" if tail else ""))
    if client == "codex":
        args = ", ".join(f'"{item}"' for item in
                         [str(Path(__file__).resolve()), *extra])
        return ("# ~/.codex/config.toml\n"
                f"[mcp_servers.{SERVER_NAME}]\n"
                f'command = "{sys.executable}"\n'
                f"args = [{args}]\n"
                + ("" if env_file else f'env_vars = ["{KEY_ENV}"]'))
    return json.dumps(config_payload(client, env_file), indent=2)


def install_config(client: str = "kilo", path: Path | str | None = None,
                   env_file: Path | str | None = None) -> dict:
    """Write or merge the entry into a client's JSON config.

    Refuses to touch a file that is not plain JSON (kilo accepts JSONC, and
    rewriting it would drop comments), and never overwrites an existing entry
    with the same name. The key is a placeholder that the client expands, so no
    secret is written here.
    """
    if client not in CONFIG_PATHS:
        return {"status": "manual", "path": None,
                "reason": f"{client} is configured by hand",
                "snippet": config_snippet(client, env_file)}
    default_path, root_key = CONFIG_PATHS[client]
    target = Path(path).expanduser() if path else Path(default_path).expanduser()
    payload = config_payload(client, env_file)[root_key][SERVER_NAME]

    if target.exists():
        text = target.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            return {"status": "manual", "path": str(target),
                    "reason": f"not plain JSON ({error.msg} at line {error.lineno}); "
                              "merge the snippet yourself so comments are not lost",
                    "snippet": config_snippet(client, env_file)}
        if not isinstance(data, dict):
            return {"status": "manual", "path": str(target),
                    "reason": "config root is not an object",
                    "snippet": config_snippet(client, env_file)}
        servers = data.get(root_key)
        if servers is not None and not isinstance(servers, dict):
            return {"status": "manual", "path": str(target),
                    "reason": f'top-level "{root_key}" is not an object',
                    "snippet": config_snippet(client, env_file)}
        servers = servers or {}
        if SERVER_NAME in servers:
            return {"status": "already", "path": str(target),
                    "entry": servers[SERVER_NAME]}
        servers[SERVER_NAME] = payload
        data[root_key] = servers
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return {"status": "merged", "path": str(target), "entry": payload}

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({root_key: {SERVER_NAME: payload}}, indent=2,
                                 ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        target.chmod(0o600)
    except OSError:
        pass
    return {"status": "created", "path": str(target), "entry": payload}


def selftest() -> dict:
    """Protocol round-trip with no network and no key; proves the server runs."""
    server = Server(enabled_cache=False)
    responses = []
    for request in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "selftest", "version": "0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "ping"},
    ):
        responses.append(server.handle(request))
    tools = responses[1]["result"]["tools"] if responses[1] else []
    return {
        "ok": responses[0] is not None and responses[1] is not None
              and responses[2] is not None,
        "protocol": (responses[0] or {}).get("result", {}).get("protocolVersion"),
        "tools": [tool["name"] for tool in tools],
        "key": "set" if os.environ.get(KEY_ENV) else "missing",
        "python": sys.executable,
        "server": str(Path(__file__).resolve()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--print-config", action="store_true",
                        help="print an MCP client configuration snippet and exit")
    parser.add_argument("--client", choices=CLIENTS, default="json",
                        help="config flavour for --print-config "
                             "(default: json, for Claude Desktop and other GUI clients)")
    parser.add_argument("--check", action="store_true",
                        help="print configuration state without a request")
    parser.add_argument("--install-config", action="store_true",
                        help="write/merge the entry into the client's JSON config "
                             "(--client kilo or gemini; default kilo)")
    parser.add_argument("--config", type=Path, default=None,
                        help="config file for --install-config "
                             "(default: the client's standard path)")
    parser.add_argument("--env-file", type=Path, default=None, metavar="PATH",
                        help="read KEY=VALUE lines from PATH at startup "
                             "(also RAPIDAPI_ENV_FILE); the shell wins")
    parser.add_argument("--selftest", action="store_true",
                        help="protocol round-trip with no network; proves the "
                             "server starts under this python")
    parser.add_argument("--cache", type=Path, default=None, help="SQLite cache path")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--source-file", type=Path, default=None,
                        help="Chinese source for translate_chapters "
                             "(default: content/source/chinese-0511241012-from-8011_1.txt)")
    parser.add_argument("--existing", type=Path, default=None,
                        help="existing human Burmese for the comparison reference")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="default output directory for translate_chapters")
    parser.add_argument("--docx", type=Path, default=None,
                        help="bilingual DOCX for chapter numbers "
                             "(default: content/merged/episodes.docx)")
    parser.add_argument("--draft-store", type=Path, default=None,
                        help="SQLite file for agent drafts "
                             "(default: content/mtranslate/agent-drafts.sqlite3)")
    parser.add_argument("--max-chars", type=int, default=MAX_REQUEST_CHARS)
    parser.add_argument("--max-items", type=int, default=MAX_REQUEST_ITEMS)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)

    if args.env_file is not None:
        args.env_file = Path(args.env_file).expanduser()
        if not args.env_file.is_file():
            print(f"[mcp] no env file at {args.env_file} — create it first, e.g.\n"
                  f"      printf 'RAPIDAPI_KEY=your-key\\n' > {args.env_file}",
                  file=sys.stderr)
            return 2

    if args.print_config:
        print(config_snippet(args.client, args.env_file))
        return 0
    if args.install_config:
        client = "kilo" if args.client == "json" else args.client
        try:
            result = install_config(client, args.config, args.env_file)
        except ValueError as error:
            print(f"[mcp] {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] in ("created", "merged", "already") else 1
    if args.selftest:
        result = selftest()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    if args.check:
        print(json.dumps({
            "host": HOST,
            "key": "set" if os.environ.get(KEY_ENV) else "missing",
            "cache": str(args.cache or os.environ.get(CACHE_ENV) or DEFAULT_CACHE),
            "protocols": list(SUPPORTED_PROTOCOLS),
            "env_file": str(args.env_file or os.environ.get("RAPIDAPI_ENV_FILE") or ""),
        }, indent=2))
        return 0

    try:
        loaded = load_env_file(args.env_file)
    except TranslatorError as error:
        print(f"[mcp] {error}", file=sys.stderr)
        return 2
    if loaded:
        print(f"[mcp] loaded {', '.join(loaded)} from {args.env_file}", file=sys.stderr)

    server = Server(cache_path=args.cache, enabled_cache=not args.no_cache,
                    max_chars=args.max_chars, max_items=args.max_items,
                    timeout=args.timeout, max_attempts=args.attempts,
                    source_file=args.source_file, existing=args.existing,
                    out_dir=args.out_dir, draft_store=args.draft_store,
                    docx=args.docx)
    return server.serve()


if __name__ == "__main__":
    sys.exit(main())
