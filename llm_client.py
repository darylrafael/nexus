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
) -> object:
    """
    Chat completion with automatic 3-tier free fallback.

    Args:
        messages:     OpenAI-format message list.
        model:        Override primary OpenRouter model (optional).
        max_tokens:   Max tokens to generate.
        temperature:  Sampling temperature.
        tools:        Optional tool definitions (function calling).
        tool_choice:  Optional tool_choice value.

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

    openrouter = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)

    # ── Tier 1: OpenRouter primary model ────────────────────────────────────
    try:
        response = _call(openrouter, model or OPENROUTER_MODEL, kwargs)
        return response
    except Exception as e:
        if not _is_retriable_error(e):
            raise
        print(f"  [llm_client] [WARN] Tier 1 ({OPENROUTER_MODEL}) limited/failed: {e}")

    # ── Tier 2: OpenRouter fallback model (same key) ─────────────────────────
    try:
        print(f"  [llm_client] [INFO] Tier 2 -> {OPENROUTER_FALLBACK_MODEL}")
        response = _call(openrouter, OPENROUTER_FALLBACK_MODEL, kwargs)
        print(f"  [llm_client] [OK] Tier 2 responded.")
        return response
    except Exception as e:
        if not _is_retriable_error(e):
            raise
        print(f"  [llm_client] [WARN] Tier 2 ({OPENROUTER_FALLBACK_MODEL}) limited/failed: {e}")

    # ── Tier 3: Gemini direct (free Google AI Studio key) ────────────────────
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "All OpenRouter free tiers are rate-limited and GEMINI_API_KEY is not set.\n"
            "Get a free key at: https://aistudio.google.com/app/apikey\n"
            "Then add GEMINI_API_KEY=... to your .env file."
        )

    try:
        print(f"  [llm_client] [INFO] Tier 3 -> Gemini ({GEMINI_MODEL})")
        gemini = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
        response = _call(gemini, GEMINI_MODEL, kwargs)
        print(f"  [llm_client] [OK] Tier 3 (Gemini) responded.")
        return response
    except Exception as e:
        raise RuntimeError(
            f"All 3 LLM tiers failed. Last error (Gemini): {e}\n"
            "Check your API keys and network connection."
        ) from e
