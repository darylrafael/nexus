"""
utils/json_parser.py

Robust JSON extraction and repair for LLM outputs.
Handles:
1. <think>...</think> thinking/reasoning tags.
2. Markdown fences (```json ... ```).
3. Leading preambles and trailing commentary.
4. Greedy bracket mismatches (balanced bracket extraction).
5. Trailing commas.
6. Truncated output repair (unclosed strings, braces, brackets).
"""
import json
import re
from typing import Any, Optional


def strip_thinking_tags(text: str) -> str:
    """Strip <think>...</think> and <reasoning>...</reasoning> tags completely."""
    if not text:
        return ""
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<reasoning>[\s\S]*?</reasoning>", "", text, flags=re.IGNORECASE)
    return text.strip()


def strip_markdown_fences(text: str) -> str:
    """Extract content inside ```json ... ``` or ``` ... ``` code blocks if present."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def sanitize_json_commas(text: str) -> str:
    """Remove illegal trailing commas before closing braces/brackets."""
    text = re.sub(r",\s*(\})", r"\1", text)
    text = re.sub(r",\s*(\])", r"\1", text)
    return text


def repair_truncated_json(text: str) -> str:
    """Attempt simple structural repair for truncated JSON responses."""
    cleaned = text.strip()
    if not cleaned:
        return "{}"

    # Balance unclosed quotes (ignoring escaped quotes)
    in_string = False
    escape = False
    brace_stack = []

    for char in cleaned:
        if char == '\\' and not escape:
            escape = True
            continue
        if char == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if char in ('{', '['):
                brace_stack.append('}' if char == '{' else ']')
            elif char in ('}', ']'):
                if brace_stack and brace_stack[-1] == char:
                    brace_stack.pop()
        escape = False

    repaired = cleaned
    if in_string:
        repaired += '"'

    # Close remaining open brackets in reverse order
    while brace_stack:
        repaired += brace_stack.pop()

    return sanitize_json_commas(repaired)


def extract_balanced_json(text: str) -> Optional[str]:
    """Find the first balanced outermost JSON object { ... } in the text."""
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    depth = 0
    in_string = False
    escape = False

    for i in range(start_idx, len(text)):
        char = text[i]
        if char == '\\' and not escape:
            escape = True
            continue
        if char == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start_idx : i + 1]
        escape = False

    return None


def extract_structured_json(raw_text: str) -> Optional[dict[str, Any]]:
    """
    Robust multi-stage JSON extractor for arbitrary LLM completions.
    Guarantees returning a dictionary if valid JSON can be recovered, or None.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    # Step 1: Strip thinking/reasoning blocks
    cleaned = strip_thinking_tags(raw_text)

    # Step 2: Extract inside markdown code fence if present
    fenced = strip_markdown_fences(cleaned)

    # Step 3: Direct JSON parse attempt
    try:
        obj = json.loads(fenced)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Step 4: Extract balanced { ... } object from fenced text
    balanced = extract_balanced_json(fenced)
    if balanced:
        try:
            obj = json.loads(sanitize_json_commas(balanced))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # Step 5: Extract balanced { ... } from full cleaned text
    balanced_cleaned = extract_balanced_json(cleaned)
    if balanced_cleaned:
        try:
            obj = json.loads(sanitize_json_commas(balanced_cleaned))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # Step 6: Regex fallback for outermost { ... }
    match = re.search(r'\{[\s\S]*\}', fenced)
    if match:
        try:
            obj = json.loads(sanitize_json_commas(match.group(0)))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # Step 7: Repair truncated JSON (unclosed brackets/quotes)
    start_idx = fenced.find('{')
    if start_idx != -1:
        candidate = fenced[start_idx:]
        try:
            repaired = repair_truncated_json(candidate)
            obj = json.loads(repaired)
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return None
