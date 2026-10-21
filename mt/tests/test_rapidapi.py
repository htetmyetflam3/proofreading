#!/usr/bin/env python3
"""Offline tests for the RapidAPI translator client, chapter runner and MCP server.

A local HTTP server imitates the three documented endpoints, including failures,
so the tests need no key and no internet:

    python3 -m unittest discover -s mt/tests -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qsl, urlsplit

HERE = Path(__file__).resolve().parent
MT = HERE.parent
ROOT = MT.parent
sys.path.insert(0, str(MT))

import api_translate  # noqa: E402
from rapidapi_translator import (  # noqa: E402
    CachedTranslator,
    RapidApiClient,
    TranslatorError,
    chunk_texts,
    parse_chapters,
    split_text,
)

KEY = "test-key-0123456789"
HOST = "test.example"
LANGUAGE = {"language": "zh-Hant", "language_name": "Chinese (Traditional)"}


# ---------------------------------------------------------------- mock API


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8")
        parsed = urlsplit(self.path)
        record = {
            "path": parsed.path,
            "params": dict(parse_qsl(parsed.query)),
            "body": body,
            "content_type": self.headers.get("Content-Type", ""),
            "key": self.headers.get("X-RapidAPI-Key", ""),
            "host": self.headers.get("X-RapidAPI-Host", ""),
        }
        self.server.requests.append(record)
        directive = self.server.directives.pop(0) if self.server.directives else None
        if directive is not None:
            if directive.get("redirect"):
                self.send_response(307)
                self.send_header("Location", "/translate")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self._send(directive.get("status", 200), directive.get("payload", {}),
                       directive.get("headers"))
            return
        if parsed.path == "/detect":
            self._send(200, {"status": True, "data": dict(LANGUAGE)})
        elif parsed.path == "/translate":
            self._send(200, {"status": True, "data": {
                "translated_text": "MY:" + body,
                "source_language": "zh-Hant",
                "source_language_name": "Chinese (Traditional)",
            }})
        elif parsed.path == "/translate/batch":
            texts = json.loads(body)
            self._send(200, {"status": True, "data": {
                "translated_texts": ["MY:" + text for text in texts],
                "source_language": "zh-Hant",
                "source_language_name": "Chinese (Traditional)",
            }})
        else:
            self._send(404, {"status": False, "error": "unknown path"})

    def _send(self, status, payload, headers=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8") \
            if not isinstance(payload, bytes) else payload
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # silence the test log
        pass


class MockApi:
    def __init__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.requests = []
        self.httpd.directives = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    @property
    def requests(self):
        return self.httpd.requests

    def queue(self, status=200, payload=None, headers=None, redirect=False):
        self.httpd.directives.append({
            "status": status, "payload": payload or {}, "headers": headers,
            "redirect": redirect,
        })

    def last(self):
        return self.requests[-1]


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.api = MockApi().start()
        self.addCleanup(self.api.stop)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.tmp = Path(self.tmpdir.name)
        self.cache = self.tmp / "cache.sqlite3"
        patcher = mock.patch.dict(os.environ, {
            "RAPIDAPI_KEY": KEY,
            "RAPIDAPI_BASE_URL": self.api.url,
            "RAPIDAPI_HOST": HOST,
            "RAPIDAPI_CACHE": str(self.cache),
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def client(self, **kwargs):
        kwargs.setdefault("backoff", 0.01)
        return RapidApiClient(**kwargs)

    def cached(self, **kwargs):
        kwargs.setdefault("backoff", 0.01)
        kwargs.setdefault("cache_path", self.cache)
        return CachedTranslator(**kwargs)


# ---------------------------------------------------------------- client


class ClientTests(ApiTestCase):
    def test_detect_posts_raw_text(self):
        result = self.client().detect("大周，帝都盛京。")
        self.assertEqual(result["language"], "zh-Hant")
        record = self.api.last()
        self.assertEqual(record["path"], "/detect")
        self.assertEqual(record["body"], "大周，帝都盛京。")
        self.assertTrue(record["content_type"].startswith("text/plain"))
        self.assertEqual(record["key"], KEY)
        self.assertEqual(record["host"], HOST)

    def test_translate_uses_query_and_raw_body(self):
        data = self.client().translate("你好", "my", "auto")
        self.assertEqual(data["translated_text"], "MY:你好")
        record = self.api.last()
        self.assertEqual(record["path"], "/translate")
        self.assertEqual(record["params"], {"source": "auto", "target": "my"})
        self.assertEqual(record["body"], "你好")
        self.assertTrue(record["content_type"].startswith("text/plain"))

    def test_batch_deduplicates_and_keeps_order(self):
        result = self.client().translate_batch(["一", "二", "一", "三"], "my")
        self.assertEqual(result.texts, ["MY:一", "MY:二", "MY:一", "MY:三"])
        self.assertEqual(result.requests, 1)
        self.assertEqual(json.loads(self.api.last()["body"]), ["一", "二", "三"])
        self.assertEqual(self.api.last()["params"], {"source": "auto", "target": "my"})

    def test_batch_chunks_by_item_limit(self):
        texts = [f"第{i}段" for i in range(5)]
        result = self.client(max_items=2).translate_batch(texts, "my")
        self.assertEqual(result.texts, ["MY:" + text for text in texts])
        self.assertEqual(result.requests, 3)

    def test_batch_chunks_by_character_limit(self):
        texts = ["一" * 30, "二" * 30, "三" * 30]
        result = self.client(max_chars=50).translate_batch(texts, "my")
        self.assertEqual(result.texts, ["MY:" + text for text in texts])
        self.assertEqual(result.requests, 3)

    def test_long_string_is_split_and_rejoined(self):
        text = "第一句話。第二句話。第三句話。第四句話。"
        client = self.client(max_chars=12)
        result = client.translate_batch([text], "my")
        self.assertEqual(result.requests, 2)
        self.assertTrue(result.texts[0].startswith("MY:第一句話。"))
        self.assertIn("第四句話", result.texts[0])

    def test_status_false_raises(self):
        self.api.queue(200, {"status": False, "error": "quota exhausted"})
        with self.assertRaises(TranslatorError) as caught:
            self.client().translate("hi", "my")
        self.assertIn("quota exhausted", str(caught.exception))

    def test_forbidden_redacts_key(self):
        self.api.queue(403, {"message": f"invalid key {KEY}"})
        with self.assertRaises(TranslatorError) as caught:
            self.client().translate("hi", "my")
        message = str(caught.exception)
        self.assertNotIn(KEY, message)
        self.assertIn("<redacted>", message)
        self.assertIn("HTTP 403", message)

    def test_429_is_retried(self):
        self.api.queue(429, {"error": "slow down"}, {"Retry-After": "0"})
        self.api.queue(429, {"error": "slow down"}, {"Retry-After": "0"})
        client = self.client()
        result = client.translate_batch(["一"], "my")
        self.assertEqual(result.texts, ["MY:一"])
        self.assertEqual(client.stats["retries"], 2)
        self.assertEqual(client.stats["requests"], 3)

    def test_retries_stop_at_max_attempts(self):
        self.api.queue(500, {"error": "boom"})
        self.api.queue(500, {"error": "boom"})
        client = self.client(max_attempts=2)
        with self.assertRaises(TranslatorError) as caught:
            client.translate("hi", "my")
        self.assertEqual(caught.exception.attempts, 2)
        self.assertEqual(len(self.api.requests), 2)

    def test_redirect_is_not_followed(self):
        self.api.queue(redirect=True)
        with self.assertRaises(TranslatorError) as caught:
            self.client().translate("hi", "my")
        self.assertIn("redirect", str(caught.exception))
        self.assertEqual(len(self.api.requests), 1)

    def test_non_json_response(self):
        self.api.queue(200, b"<html>gateway error</html>")
        with self.assertRaises(TranslatorError) as caught:
            self.client().translate("hi", "my")
        self.assertIn("not JSON", str(caught.exception))

    def test_missing_key_is_refused(self):
        with mock.patch.dict(os.environ, {"RAPIDAPI_KEY": ""}):
            with self.assertRaises(TranslatorError) as caught:
                RapidApiClient()
        self.assertIn("RAPIDAPI_KEY", str(caught.exception))


class CacheTests(ApiTestCase):
    def test_second_run_uses_cache(self):
        translator = self.cached()
        first = translator.translate_batch(["一", "二"], "my")
        self.assertEqual(first.requests, 1)
        self.assertEqual(first.cached, 0)
        before = len(self.api.requests)
        second = translator.translate_batch(["一", "二"], "my")
        self.assertEqual(len(self.api.requests), before)
        self.assertEqual(second.requests, 0)
        self.assertEqual(second.cached, 2)
        self.assertEqual(second.cache_hits, [True, True])
        self.assertEqual(second.texts, first.texts)
        translator.close()

    def test_only_missing_strings_are_sent(self):
        translator = self.cached()
        translator.translate_batch(["一", "二"], "my")
        translator.translate_batch(["二", "三"], "my")
        self.assertEqual(json.loads(self.api.last()["body"]), ["三"])
        translator.close()

    def test_cache_key_includes_language_pair(self):
        translator = self.cached()
        translator.translate_batch(["一"], "my")
        translator.translate_batch(["一"], "en")
        self.assertEqual(len(self.api.requests), 2)
        translator.close()

    def test_disabled_cache_always_requests(self):
        translator = self.cached(enabled=False)
        translator.translate_batch(["一"], "my")
        translator.translate_batch(["一"], "my")
        self.assertEqual(len(self.api.requests), 2)
        translator.close()


class HelperTests(unittest.TestCase):
    def test_split_text_roundtrip(self):
        text = "第一句話。第二句話！第三句話？第四句話…第五句話；第六句話。"
        for limit in (5, 12, 20):
            pieces = split_text(text, limit)
            self.assertEqual("".join(pieces), text)
            self.assertTrue(all(len(piece) <= limit for piece in pieces))

    def test_split_keeps_spaces(self):
        text = "One sentence. Two sentence. Three sentence. Four sentence."
        self.assertEqual("".join(split_text(text, 20)), text)

    def test_chunk_texts_limits(self):
        chunks = list(chunk_texts(["一" * 10, "二" * 10, "三" * 10],
                                  max_chars=25, max_items=10))
        self.assertEqual([len(chunk) for chunk in chunks], [2, 1])
        chunks = list(chunk_texts(["a", "b", "c"], max_chars=100, max_items=2))
        self.assertEqual([len(chunk) for chunk in chunks], [2, 1])

    def test_parse_chapters(self):
        self.assertEqual(parse_chapters("1-2"), [1, 2])
        self.assertEqual(parse_chapters("1,3-4"), [1, 3, 4])
        self.assertEqual(parse_chapters(["1", "1"]), [1])
        with self.assertRaises(ValueError):
            parse_chapters("3-1")


# ---------------------------------------------------------------- chapters


SOURCE = """===== 第一章：測試一 =====

大周，帝都盛京。
“我就這麼穿越了？”
[[KMTCRAWLER MARKER 2]]
===== 第二章：測試二 =====

他叫葉寧。
PS: 求推薦票！
..........................................................................
(活動時間：10月1日到10月7日)
[[KMTCRAWLER MARKER 3]]
"""

EXISTING = """Chapter 1: ပထမအခန်း
မဟာကျိုးဧကရာဇ်တိုင်းပြည်၊ ရှန်းကျင်းနန်းမြို့တော်။
wunzinnosp

Chapter 2: ဒုတိယအခန်း
သူ့နာမည်က ယဲ့နင်။
"""


class ChapterTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.source = self.tmp / "source.txt"
        self.source.write_text(SOURCE, encoding="utf-8")
        self.existing = self.tmp / "existing.txt"
        self.existing.write_text(EXISTING, encoding="utf-8")
        self.out = self.tmp / "out"

    def test_paragraphs_drop_crawler_junk(self):
        chapters = api_translate.chinese_chapters(self.source)
        paragraphs = api_translate.chapter_paragraphs(chapters[0])
        self.assertEqual(paragraphs, ["大周，帝都盛京。", "“我就這麼穿越了？”"])
        notes = api_translate.chapter_paragraphs(chapters[0], keep_notes=True)
        self.assertEqual(notes, paragraphs)
        second = api_translate.chapter_paragraphs(chapters[1])
        self.assertEqual(second, ["他叫葉寧。"])

    def test_plan_makes_no_request(self):
        chapters = api_translate.chinese_chapters(self.source)
        plan = api_translate.build_plan(chapters, target="my", source="auto",
                                        max_chars=4500, max_items=40)
        self.assertEqual(plan["totals"]["paragraphs"], 3)
        self.assertEqual(plan["totals"]["requests"], 2)
        self.assertEqual(self.api.requests, [])

    def test_run_writes_files(self):
        chapters = api_translate.chinese_chapters(self.source)
        report = api_translate.run(chapters, out_dir=self.out, cache_path=self.cache,
                                   existing_path=self.existing)
        self.assertEqual(report["totals"]["chapters"], 2)
        self.assertEqual(report["totals"]["paragraphs"], 3)
        self.assertEqual(report["totals"]["requests"], 2)
        for name in ("ch0001.my.jsonl", "ch0001.my.txt", "ch0002.my.txt",
                     "book.my.txt", "compare-ch001-ch002.md", "report.json"):
            self.assertTrue((self.out / name).is_file(), name)
        records = [json.loads(line) for line in
                   (self.out / "ch0001.my.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["source"] for row in records],
                         ["大周，帝都盛京。", "“我就這麼穿越了？”"])
        self.assertEqual([row["target"] for row in records],
                         ["MY:大周，帝都盛京。", "MY:“我就這麼穿越了？”"])
        comparison = (self.out / "compare-ch001-ch002.md").read_text(encoding="utf-8")
        self.assertIn("မဟာကျိုး", comparison)
        self.assertIn("Existing human Burmese — chapter 1", comparison)

    def test_second_run_hits_cache(self):
        chapters = api_translate.chinese_chapters(self.source)
        api_translate.run(chapters, out_dir=self.out, cache_path=self.cache,
                         existing_path=self.existing)
        before = len(self.api.requests)
        report = api_translate.run(chapters, out_dir=self.out, cache_path=self.cache,
                                   existing_path=self.existing)
        self.assertEqual(len(self.api.requests), before)
        self.assertEqual(report["totals"]["requests"], 0)
        self.assertEqual(report["totals"]["cached"], 3)

    def test_cli_plan_then_run(self):
        plan = api_translate.main([
            "--chapters", "1-2", "--source-file", str(self.source),
            "--out-dir", str(self.out), "--existing", str(self.existing),
            "--cache", str(self.cache), "--json",
        ])
        self.assertEqual(plan, 0)
        self.assertEqual(self.api.requests, [])
        code = api_translate.main([
            "--chapters", "1-2", "--source-file", str(self.source),
            "--out-dir", str(self.out), "--existing", str(self.existing),
            "--cache", str(self.cache), "--run", "--json",
        ])
        self.assertEqual(code, 0)
        self.assertTrue((self.out / "report.json").is_file())
        self.assertEqual(len(self.api.requests), 2)

    def test_cli_rejects_unknown_chapter(self):
        code = api_translate.main([
            "--chapters", "9", "--source-file", str(self.source),
            "--out-dir", str(self.out),
        ])
        self.assertEqual(code, 2)


# ---------------------------------------------------------------- MCP


SERVER = MT / "mcp_server.py"


class McpProcess:
    def __init__(self, env, args=()):
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), *args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=str(ROOT), env=env)
        self.next_id = 0

    def request(self, method, params=None, timeout=20):
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()
        return json.loads(self._readline(timeout))

    def notify(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def _readline(self, timeout):
        box = {}

        def read():
            box["line"] = self.proc.stdout.readline()

        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.proc.kill()
            raise AssertionError("MCP server did not answer in time")
        line = box.get("line", "")
        if not line:
            self.proc.kill()
            raise AssertionError("MCP server closed stdout: "
                                 + self.proc.stderr.read())
        return line

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            self.proc.kill()
        for stream in (self.proc.stdout, self.proc.stderr):
            if stream is not None:
                stream.close()


class McpTests(ApiTestCase):
    def env(self):
        environment = dict(os.environ)
        environment.update({
            "RAPIDAPI_KEY": KEY,
            "RAPIDAPI_BASE_URL": self.api.url,
            "RAPIDAPI_HOST": HOST,
            "RAPIDAPI_CACHE": str(self.cache),
        })
        return environment

    def start(self, env=None, args=()):
        process = McpProcess(env or self.env(), args)
        self.addCleanup(process.close)
        return process

    def test_handshake_and_tool_call(self):
        process = self.start()
        init = process.request("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        })
        self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(init["result"]["serverInfo"]["name"], "rapidapi-translator")
        process.notify("notifications/initialized")
        listed = process.request("tools/list")
        names = {tool["name"] for tool in listed["result"]["tools"]}
        self.assertEqual(names, {"detect_language", "translate_text",
                                 "translate_batch", "translate_chapters"})
        called = process.request("tools/call", {
            "name": "translate_text",
            "arguments": {"text": "你好", "target": "my"},
        })
        self.assertFalse(called["result"]["isError"])
        payload = json.loads(called["result"]["content"][0]["text"])
        self.assertEqual(payload["translated_text"], "MY:你好")

    def test_batch_and_detect_tools(self):
        process = self.start()
        process.request("initialize", {"protocolVersion": "2025-06-18"})
        batch = process.request("tools/call", {
            "name": "translate_batch",
            "arguments": {"texts": ["一", "二"], "target": "my"},
        })
        payload = json.loads(batch["result"]["content"][0]["text"])
        self.assertEqual(payload["translations"], ["MY:一", "MY:二"])
        detect = process.request("tools/call", {
            "name": "detect_language", "arguments": {"text": "大周"},
        })
        payload = json.loads(detect["result"]["content"][0]["text"])
        self.assertEqual(payload["language"], "zh-Hant")

    def test_unknown_tool_and_method(self):
        process = self.start()
        process.request("initialize", {"protocolVersion": "2025-06-18"})
        unknown = process.request("tools/call", {"name": "nope", "arguments": {}})
        self.assertEqual(unknown["error"]["code"], -32602)
        method = process.request("resources/subscribe", {"uri": "x"})
        self.assertEqual(method["error"]["code"], -32601)

    def test_missing_key_is_a_tool_error(self):
        environment = self.env()
        environment["RAPIDAPI_KEY"] = ""
        process = self.start(environment)
        process.request("initialize", {"protocolVersion": "2025-06-18"})
        called = process.request("tools/call", {
            "name": "translate_text", "arguments": {"text": "你好"},
        })
        self.assertTrue(called["result"]["isError"])
        self.assertIn("RAPIDAPI_KEY", called["result"]["content"][0]["text"])

    def test_chapter_tool_writes_files(self):
        source = self.tmp / "source.txt"
        source.write_text(SOURCE, encoding="utf-8")
        existing = self.tmp / "existing.txt"
        existing.write_text(EXISTING, encoding="utf-8")
        out = self.tmp / "mcp-out"
        process = self.start(args=("--source-file", str(source),
                                   "--existing", str(existing)))
        process.request("initialize", {"protocolVersion": "2025-06-18"})
        called = process.request("tools/call", {
            "name": "translate_chapters",
            "arguments": {"chapters": "1-2", "target": "my", "out_dir": str(out)},
        }, timeout=60)
        self.assertFalse(called["result"]["isError"], called["result"])
        payload = json.loads(called["result"]["content"][0]["text"])
        self.assertEqual(payload["totals"]["paragraphs"], 3)
        self.assertTrue((out / "report.json").is_file())


class ConfigTests(unittest.TestCase):
    def run_server(self, *args, env=None):
        return subprocess.run([sys.executable, str(SERVER), *args],
                              capture_output=True, text=True, timeout=30,
                              env=env)

    def test_client_snippets(self):
        for client in ("json", "claude", "kilo", "codex", "gemini"):
            output = self.run_server("--print-config", "--client", client)
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn("mcp_server.py", output.stdout)
            if client == "claude":
                self.assertIn("claude mcp add --scope user", output.stdout)
                continue
            body = "\n".join(line for line in output.stdout.splitlines()
                             if not line.lstrip().startswith("#"))
            if client == "codex":
                try:
                    import tomllib
                except ImportError:  # pragma: no cover - python < 3.11
                    self.assertIn('env_vars = ["RAPIDAPI_KEY"]', body)
                    continue
                data = tomllib.loads(body)
                table = data["mcp_servers"]["rapidapi-translator"]
                self.assertEqual(table["env_vars"], ["RAPIDAPI_KEY"])
                self.assertTrue(table["args"][0].endswith("mcp_server.py"))
                continue
            data = json.loads(body)
            table = (data.get("mcp") or data.get("mcpServers"))["rapidapi-translator"]
            if client == "kilo":
                self.assertTrue(table["command"][0].endswith("python3"))
                self.assertIn("mcp_server.py", table["command"][1])
                self.assertEqual(table["environment"]["RAPIDAPI_KEY"],
                                 "{env:RAPIDAPI_KEY}")
            else:
                self.assertTrue(table["command"].endswith("python3"))
                self.assertTrue(table["args"][0].endswith("mcp_server.py"))
        unknown = self.run_server("--print-config", "--client", "nope")
        self.assertNotEqual(unknown.returncode, 0)

    def test_selftest_needs_no_key_or_network(self):
        environment = dict(os.environ, RAPIDAPI_KEY="")
        output = self.run_server("--selftest", env=environment)
        self.assertEqual(output.returncode, 0, output.stderr)
        payload = json.loads(output.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tools"], ["detect_language", "translate_text",
                                            "translate_batch", "translate_chapters"])
        self.assertEqual(payload["key"], "missing")

    def test_print_config_is_valid_json(self):
        output = subprocess.run([sys.executable, str(SERVER), "--print-config"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(output.returncode, 0, output.stderr)
        payload = json.loads(output.stdout)
        server = payload["mcpServers"]["rapidapi-translator"]
        self.assertTrue(server["args"][0].endswith("mcp_server.py"))
        self.assertIn("RAPIDAPI_KEY", server["env"])

    def test_check_hides_key(self):
        environment = dict(os.environ, RAPIDAPI_KEY=KEY)
        output = subprocess.run([sys.executable, str(SERVER), "--check"],
                                capture_output=True, text=True, timeout=20,
                                env=environment)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertNotIn(KEY, output.stdout)
        self.assertEqual(json.loads(output.stdout)["key"], "set")


if __name__ == "__main__":
    unittest.main()
