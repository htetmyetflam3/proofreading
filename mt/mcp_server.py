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
    parse_chapters,
)

SERVER_NAME = "rapidapi-translator"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07")
DEFAULT_PROTOCOL = "2024-11-05"

INSTRUCTIONS = (
    "Translation tools backed by the RapidAPI 'Multi format AI translator' API. "
    f"The API key is read from {KEY_ENV}. `translate_chapters` reads the local "
    "Chinese web-novel source and writes files under content/mtranslate/rapidapi; "
    "it costs one request per ~4,500 characters, so check the plan output first "
    "with mt/api_translate.py --plan."
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
        "name": "translate_chapters",
        "description": "Translate chapters of the local Chinese novel and write "
                       "JSONL, TXT, a Chinese/Burmese comparison markdown and "
                       "report.json. Costs one request per ~4,500 characters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "chapters": {"type": "string",
                             "description": "'1-2', '1,3-4' or 'all'.",
                             "default": "1-2"},
                "target": {"type": "string", "description": "Target language code.",
                           "default": "my"},
                "source": {"type": "string", "description": "Source code or 'auto'.",
                           "default": "auto"},
                "out_dir": {"type": "string",
                            "description": "Output directory; default "
                                           "content/mtranslate/rapidapi."},
            },
            "required": ["chapters"],
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
                 out_dir: Path | str | None = None) -> None:
        self.cache_path = cache_path
        self.enabled_cache = enabled_cache
        self.max_chars = max_chars
        self.max_items = max_items
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.source_file = source_file
        self.existing = existing
        self.out_dir = out_dir
        self._translator: CachedTranslator | None = None

    @property
    def translator(self) -> CachedTranslator:
        if self._translator is None:
            self._translator = CachedTranslator(
                cache_path=self.cache_path, enabled=self.enabled_cache,
                timeout=self.timeout, max_attempts=self.max_attempts,
                max_chars=self.max_chars, max_items=self.max_items)
        return self._translator

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
        if name == "translate_chapters":
            return self._translate_chapters(arguments)
        raise KeyError(name)

    def _translate_chapters(self, arguments: dict) -> dict:
        from api_translate import (  # noqa: PLC0415
            BURMESE, CHINESE, OUTPUT, chinese_chapters, run, select,
        )

        spec = arguments.get("chapters", "1-2")
        if not isinstance(spec, str) or not spec.strip():
            raise ValueError("`chapters` must be a string such as '1-2'")
        target = self._language(arguments.get("target", "my"), "target")
        source = self._language(arguments.get("source", "auto"), "source")
        out_dir = Path(arguments.get("out_dir") or self.out_dir or OUTPUT)
        chapters = chinese_chapters(Path(self.source_file or CHINESE))
        if spec.strip().lower() == "all":
            wanted = [chapter.number for chapter in chapters]
        else:
            wanted = parse_chapters(spec)
        selected = select(chapters, wanted)
        missing = sorted(set(wanted) - {chapter.number for chapter in selected})
        if missing or not selected:
            raise ValueError(f"chapter(s) {missing or wanted} not found in the local source")
        report = run(selected, target=target, source=source, out_dir=out_dir,
                     cache_path=self.cache_path, enabled_cache=self.enabled_cache,
                     max_chars=self.max_chars, max_items=self.max_items,
                     timeout=self.timeout, max_attempts=self.max_attempts,
                     existing_path=Path(self.existing or BURMESE))
        return {
            "target": report["target"],
            "detected": report["detected"],
            "totals": report["totals"],
            "chapters": report["chapters"],
            "files": report["files"],
            "elapsed_seconds": report["elapsed_seconds"],
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
                    out_dir=args.out_dir)
    return server.serve()


if __name__ == "__main__":
    sys.exit(main())
