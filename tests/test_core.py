"""Regression tests for deterministic Nexus components.

These tests do not call external APIs or require credentials.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.prediction_extractor import extract_predictions
from memory import artifacts
from utils.text import split_text


class ArtifactTests(unittest.TestCase):
    def test_malformed_json_artifact_is_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            path = root / "2026-01-01"
            path.mkdir()
            (path / "broken.json").write_text("{not valid json", encoding="utf-8")
            with patch.object(artifacts, "ARTIFACT_ROOT", root):
                self.assertIsNone(artifacts.load_json_artifact("2026-01-01", "broken.json"))


class ParsingTests(unittest.TestCase):
    def test_prediction_parser_extracts_signals_and_tickers(self):
        brief = """
### 1. Domestic
- **Market Impact**: Bullish | **Confidence**: 70%
### 2. Global
- **Market Impact**: Bearish | **Confidence**: 50%
### 3. Commodities
- **Market Impact**: Bullish | **Confidence**: 80%
### 4. Regional
- **Market Impact**: Neutral | **Confidence**: 60%
### 5. Foreign Flow
- **Net Buy/Sell**: Net Buy Rp1 Triliun
- **Signal**: Accumulation
### 6. Sector Outlook
**Bullish:**
- **Energy**: Higher oil — MEDC
**Neutral:**
- **Banks**: Stable — BBCA
**Bearish:**
- **Consumer**: Costs — ICBP
### 7. Key Risk
- USD/IDR volatility.
"""
        prediction = extract_predictions(brief, "2026-01-01")
        self.assertEqual(prediction.ihsg_signal, "Bullish")
        self.assertEqual(prediction.foreign_flow_signal, "Accumulation")
        self.assertIn("MEDC", prediction.recommended_tickers)
        self.assertEqual(prediction.sector_bullish, ["Energy"])

class TelegramTests(unittest.TestCase):
    def test_message_chunks_are_nonempty_and_within_limit(self):
        chunks = split_text("A" * 25 + "\n" + "B" * 25, max_length=20)
        self.assertTrue(chunks)
        self.assertTrue(all(0 < len(chunk) <= 20 for chunk in chunks))
        self.assertEqual("".join(chunks).replace("\n", ""), "A" * 25 + "B" * 25)


if __name__ == "__main__":
    unittest.main()
