"""NLLB runner: language codes, batching, line alignment, prefix handling."""
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mt"))

import nllb  # noqa: E402


class FakeTokenizer:
    """Whitespace tokenizer that marks word starts the way sentencepiece does."""

    def encode(self, text, out_type=str):
        return ["▁" + word for word in text.split()]


class FakeTranslator:
    """Echoes the batch back, with the target prefix in front, like CTranslate2."""

    def __init__(self):
        self.batches = []

    def translate_batch(self, batch, target_prefix, beam_size, max_batch_size):
        self.batches.append(len(batch))
        out = []
        for tokens, prefix in zip(batch, target_prefix):
            body = [t for t in tokens[1:] if t != "</s>"]
            out.append(types.SimpleNamespace(hypotheses=[list(prefix) + body]))
        return out


class LanguageTests(unittest.TestCase):
    def test_short_codes_map_to_flores(self):
        self.assertEqual(nllb.flores("zh"), "zho_Hans")
        self.assertEqual(nllb.flores("my"), "mya_MM")
        self.assertEqual(nllb.flores("en"), "eng_Latn")
        self.assertEqual(nllb.flores("ZH-Hans"), "zho_Hans")

    def test_flores_code_passes_through(self):
        self.assertEqual(nllb.flores("mya_MM"), "mya_MM")

    def test_unknown_code_is_rejected(self):
        with self.assertRaises(ValueError):
            nllb.flores("klingon")


class TranslateLinesTests(unittest.TestCase):
    def test_one_output_line_per_input_line(self):
        result = nllb.translate_lines(["天下 太平", "你 好"], FakeTranslator(),
                                      FakeTokenizer(), "zho_Hans", "mya_MM")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], "天下 太平")

    def test_blank_lines_are_preserved(self):
        result = nllb.translate_lines(["天下", "", "太平"], FakeTranslator(),
                                      FakeTokenizer(), "zho_Hans", "mya_MM")
        self.assertEqual(result[1], "")
        self.assertEqual(len(result), 3)

    def test_sentencepiece_marker_never_survives(self):
        # Real OPUS-MT decode returned "It's a▁peaceful▁world." — the marker must go.
        result = nllb.translate_lines(["天下 太平"], FakeTranslator(), FakeTokenizer(),
                                      "zho_Hans", "mya_MM")
        self.assertNotIn("▁", result[0])
        self.assertEqual(result[0], "天下 太平")

    def test_detokenize_handles_attached_markers(self):
        self.assertEqual(nllb.detokenize(["▁It", "'", "s", "▁a", "▁peaceful", "."]),
                         "It's a peaceful.")
        self.assertEqual(nllb.detokenize(["▁မြ", "န်", "မာ"]), "မြန်မာ")
        self.assertEqual(nllb.detokenize(["▁မြ", "န်", "မာ", "▁စာ"]), "မြန်မာ စာ")

    def test_target_prefix_is_not_emitted(self):
        result = nllb.translate_lines(["天下"], FakeTranslator(), FakeTokenizer(),
                                      "zho_Hans", "mya_MM")
        self.assertNotIn("mya_MM", result[0])

    def test_batches_are_capped(self):
        translator = FakeTranslator()
        nllb.translate_lines([f"w{i}" for i in range(5)], translator, FakeTokenizer(),
                             "zho_Hans", "mya_MM", batch_size=2)
        self.assertEqual(translator.batches, [2, 2, 1])

    def test_source_token_leads_every_sequence(self):
        seen = {}

        class Recorder(FakeTranslator):
            def translate_batch(self, batch, target_prefix, beam_size, max_batch_size):
                seen["first"] = batch[0][0]
                return super().translate_batch(batch, target_prefix, beam_size, max_batch_size)

        nllb.translate_lines(["天下"], Recorder(), FakeTokenizer(), "zho_Hans", "mya_MM")
        self.assertEqual(seen["first"], "zho_Hans")


class ModelTests(unittest.TestCase):
    def test_missing_model_is_reported(self):
        ready, detail = nllb.model_ready(Path("/nonexistent/nllb"))
        self.assertFalse(ready)
        self.assertIn("no model", detail)

    def test_incomplete_model_names_the_missing_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "model.bin").write_bytes(b"x")
            ready, detail = nllb.model_ready(Path(directory))
            self.assertFalse(ready)
            self.assertIn(nllb.TOKENIZER, detail)


if __name__ == "__main__":
    unittest.main()
