"""
llm_client.py — Centralised LLM call with automatic 3-tier fallback.

Fallback chain (all free, no credit needed):
  Tier 1 → OpenRouter: gpt-oss-120b:free          (primary)
  Tier 2 → OpenRouter: gemini-2.0-flash-exp:free   (same key, different model)
  Tier 3 → Gemini API: gemini-2.0-flash            (Google AI Studio free key)

Usage:
    from llm_client import llm_chat
    response = llm_chat(messages=[...], max_tokens=2000)
    text = response.choices[0].message.content

Tier 3 is only attempted if GEMINI_API_KEY is set in .env.
Get a free Gemini key (no credit card): https://aistudio.google.com/app/apikey
"""

from openai import OpenAI
from config import (
    OPENROUTER_API_KEY,    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,      OPENROUTER_FALLBACK_MODEL,
    GEMINI_API_KEY,        GEMINI_BASE_URL, GEMINI_MODEL,
)

# Signals that indicate rate-limit, network glitches, or server errors
_RETRIABLE_SIGNALS = (
    "429", "402", "404", "400", "rate limit", "rate_limit", "too many requests", "quota", 
    "insufficient credits", "overloaded", "context_length_exceeded",
    "500", "502", "503", "504", "524", "timeout", "connection error", "getaddrinfo",
    "socket", "api connection error", "service unavailable", "bad gateway"
)

def _is_retriable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(sig in msg for sig in _RETRIABLE_SIGNALS)


def _call(client: OpenAI, model: str, kwargs: dict) -> object:
    """Make one attempt with the given client + model."""
    return client.chat.completions.create(model=model, **kwargs)


def llm_chat(
    messages: list,
    model: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.2,
    tools: list = None,
    tool_choice=None,
    response_format=None,
) -> object:
    """
    Chat completion with automatic 3-tier free fallback.

    Args:
        messages:        OpenAI-format message list.
        model:           Override primary OpenRouter model (optional).
        max_tokens:      Max tokens to generate.
        temperature:     Sampling temperature.
        tools:           Optional tool definitions (function calling).
        tool_choice:     Optional tool_choice value.
        response_format: Optional response format (e.g. {"type": "json_object"}).

    Returns:
        openai ChatCompletion response object.
    Raises:
        Exception if all available tiers fail.
    """
    kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature)
    if tools:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if response_format is not None:
        kwargs["response_format"] = response_format

    # ── Tier 1: Gemini direct (fastest & highest quota if key is present) ──
    if GEMINI_API_KEY:
        try:
            gemini = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
            response = _call(gemini, GEMINI_MODEL, kwargs)
            return response
        except Exception as e:
            if not _is_retriable_error(e):
                raise
            print(f"  [llm_client] [WARN] Gemini ({GEMINI_MODEL}) failed: {e}. Falling back to OpenRouter...")

    # ── Tier 2: OpenRouter primary model ────────────────────────────────────
    openrouter = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    try:
        response = _call(openrouter, model or OPENROUTER_MODEL, kwargs)
        return response
    except Exception as e:
        if not _is_retriable_error(e):
            raise
        print(f"  [llm_client] [WARN] OpenRouter Tier 1 ({OPENROUTER_MODEL}) failed: {e}")

    # ── Tier 3: OpenRouter fallback model ─────────────────────────────────
    try:
        print(f"  [llm_client] [INFO] OpenRouter Fallback -> {OPENROUTER_FALLBACK_MODEL}")
        response = _call(openrouter, OPENROUTER_FALLBACK_MODEL, kwargs)
        print(f"  [llm_client] [OK] OpenRouter Fallback responded.")
        return response
    except Exception as e:
        raise RuntimeError(
            f"All LLM tiers failed. Last error: {e}\n"
            "Check your API keys and network connection."
        ) from e
