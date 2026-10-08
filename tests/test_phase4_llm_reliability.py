"""
tests/test_phase4_llm_reliability.py

Comprehensive tests for Phase 4:
1. utils.json_parser: thinking tags stripping, markdown fence removal, trailing commas,
   balanced brackets, and truncated JSON repair.
2. llm_client: completion validation, content extraction, and multi-tier fallback on retriable errors.
"""
import pytest
from unittest.mock import MagicMock

from utils.json_parser import (
    extract_structured_json,
    strip_thinking_tags,
    strip_markdown_fences,
    repair_truncated_json,
)
import llm_client as lc


# ── 1. Robust JSON Extraction Tests ───────────────────────────────────────────

def test_extract_json_with_thinking_tags():
    raw_output = """
<think>
Let me analyze the post-market results:
{
  "unrelated_nested_curly": "should be ignored"
}
We must output step4_evaluation and step5_rca.
</think>
{
  "step4_evaluation": {
    "ihsg_correct": true,
    "ihsg_actual": "Bullish"
  },
  "step5_rca": {
    "unanticipated_factors": ["Rate hike pause"]
  }
}
"""
    data = extract_structured_json(raw_output)
    assert data is not None
    assert "step4_evaluation" in data
    assert data["step4_evaluation"]["ihsg_actual"] == "Bullish"
    assert data["step5_rca"]["unanticipated_factors"] == ["Rate hike pause"]


def test_extract_json_markdown_fences_and_commentary():
    raw_output = """
Here is the post-market review analysis in JSON:

```json
{
  "summary_sentence": "IHSG rose +1.20% in line with expectations.",
  "lessons": [
    "Ketika sentimen stabil, maka IHSG menguat."
  ],
}
```

Hope this helps! Let me know if you need more details.
"""
    data = extract_structured_json(raw_output)
    assert data is not None
    assert "summary_sentence" in data
    assert len(data["lessons"]) == 1


def test_repair_truncated_json():
    # Unclosed string and brackets
    truncated = '{"step4_evaluation": {"ihsg_actual": "Bullish", "details": "market was strong'
    repaired = repair_truncated_json(truncated)
    assert repaired.endswith("}}") or repaired.endswith('"}')
    data = extract_structured_json(truncated)
    assert data is not None
    assert data.get("step4_evaluation", {}).get("ihsg_actual") == "Bullish"


# ── 2. LLM Client Completion Validation & Extraction ─────────────────────────

def test_is_valid_completion():
    assert not lc._is_valid_completion(None)
    assert not lc._is_valid_completion({})

    # Object without choices
    mock_empty = MagicMock()
    mock_empty.choices = []
    assert not lc._is_valid_completion(mock_empty)

    # Choice with valid message content
    mock_valid = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Valid response text"
    mock_choice.message.tool_calls = None
    mock_valid.choices = [mock_choice]
    assert lc._is_valid_completion(mock_valid)
    assert lc.get_content(mock_valid) == "Valid response text"

    # Choice with reasoning field when content is None (deepseek / reasoning models)
    mock_reasoning = MagicMock()
    mock_choice2 = MagicMock()
    mock_choice2.message.content = None
    mock_choice2.message.reasoning = "Thought and output text"
    mock_choice2.message.tool_calls = None
    mock_reasoning.choices = [mock_choice2]
    assert lc._is_valid_completion(mock_reasoning)
    assert lc.get_content(mock_reasoning) == "Thought and output text"


# ── 3. Multi-tier Fallback Reliability on Retriable Errors ─────────────────────

def test_llm_chat_fallback_on_primary_error(monkeypatch):
    # Disable Gemini Tier 1 for this test to test OpenRouter fallback chain
    monkeypatch.setattr(lc, "GEMINI_API_KEY", None)

    attempts = []

    def mock_create(model, **kwargs):
        attempts.append(model)
        if len(attempts) == 1:
            # First attempt fails with 429 rate limit
            raise Exception("429 Too Many Requests: Rate limit exceeded")
        # Second attempt succeeds
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = '{"status": "ok_from_fallback"}'
        choice.finish_reason = "stop"
        resp.choices = [choice]
        return resp

    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create

    monkeypatch.setattr(lc, "OpenAI", lambda *args, **kwargs: mock_client)

    result = lc.llm_chat(messages=[{"role": "user", "content": "hi"}])
    assert result is not None
    assert len(attempts) >= 2
    # Verify primary model was tried first, then fallback model
    assert attempts[0] == lc.OPENROUTER_MODEL
    assert attempts[1] != lc.OPENROUTER_MODEL
    assert lc.get_content(result) == '{"status": "ok_from_fallback"}'
