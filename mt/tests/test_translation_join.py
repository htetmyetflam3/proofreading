"""read_chapter joins the API's Burmese to paragraphs, and checks the alignment."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mt"))

import agent_work  # noqa: E402


class TranslationJoinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paragraphs = agent_work.chapter_paragraphs_by_number(1)

    def write(self, records):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "ch0001.my.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return Path(directory)

    def fresh(self):
        return [agent_work.Paragraph(p.chapter, p.index, p.text)
                for p in self.paragraphs]

    def test_matching_source_is_attached(self):
        paras = self.fresh()
        directory = self.write([{"chapter": 1, "index": paras[0].index,
                                 "source": paras[0].text, "target": "ဘာသာပြန်"}])
        report = agent_work.load_translation(1, paras, directory)
        self.assertTrue(report["available"])
        self.assertEqual(report["attached"], 1)
        self.assertEqual(paras[0].translation, "ဘာသာပြန်")

    def test_mismatched_source_is_refused(self):
        paras = self.fresh()
        directory = self.write([{"chapter": 1, "index": paras[0].index,
                                 "source": "not this paragraph", "target": "WRONG"}])
        report = agent_work.load_translation(1, paras, directory)
        self.assertEqual(report["attached"], 0)
        self.assertEqual(report["mismatched"], 1)
        self.assertEqual(paras[0].translation, "")

    def test_missing_file_is_not_an_error(self):
        paras = self.fresh()
        report = agent_work.load_translation(1, paras, Path(tempfile.mkdtemp()))
        self.assertFalse(report["available"])
        self.assertIn("no API translation", report["detail"])

    def test_read_chapter_exposes_my_only_when_present(self):
        payload = agent_work.read_chapter(1, translations=Path(tempfile.mkdtemp()))
        self.assertFalse(payload["translation"]["available"])
        self.assertNotIn("my", payload["paragraphs"][0])


if __name__ == "__main__":
    unittest.main()
