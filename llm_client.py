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
    "socket", "api connection error", "service unavailable", "bad gateway",
    "high demand", "temporarily", "unavailable", "choices"
)

# Robust fallback pool for OpenRouter free tier
_OPENROUTER_FALLBACK_POOL = [
    OPENROUTER_FALLBACK_MODEL,
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-r1-distill-llama-70b:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]

def _is_retriable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(sig in msg for sig in _RETRIABLE_SIGNALS) or isinstance(exc, (ValueError, KeyError, TypeError))


def _is_valid_completion(resp: object) -> bool:
    """Validate that completion has choices with readable content."""
    if not resp:
        return False
    choices = getattr(resp, "choices", None)
    if not choices or not isinstance(choices, list) or len(choices) == 0:
        return False
    choice = choices[0]
    if not choice:
        return False
    msg = getattr(choice, "message", None)
    if not msg:
        return False

    content = getattr(msg, "content", None)
    has_tools = bool(getattr(msg, "tool_calls", None))
    if content is not None:
        return True
    if has_tools:
        return True

    # If content is None, check if model emitted text in reasoning field
    reasoning = getattr(msg, "reasoning", None)
    if reasoning and isinstance(reasoning, str) and len(reasoning.strip()) > 0:
        msg.content = reasoning
        return True

    return False


def get_content(response: object) -> str:
    """Safely extract string content from ChatCompletion response without NoneType errors."""
    if not response or not getattr(response, "choices", None) or not response.choices:
        return ""
    choice = response.choices[0]
    if not choice or not getattr(choice, "message", None):
        return ""
    content = getattr(choice.message, "content", None)
    if content:
        return str(content)
    reasoning = getattr(choice.message, "reasoning", None)
    if reasoning:
        return str(reasoning)
    return ""


def _call(client: OpenAI, model: str, kwargs: dict) -> object:
    """Make one attempt with the given client + model and validate response integrity."""
    resp = client.chat.completions.create(model=model, **kwargs)
    if not _is_valid_completion(resp):
        choices_val = getattr(resp, "choices", "NO_CHOICES_ATTR")
        raise ValueError(f"Model '{model}' returned invalid completion without choices (choices={choices_val})")
    return resp


def llm_chat(
    messages: list,
    model: str = None,
    max_tokens: int = 8192,
    temperature: float = 0.2,
    tools: list = None,
    tool_choice=None,
    response_format=None,
) -> object:
    """
    Chat completion with automatic multi-tier free fallback.

    Args:
        messages:        OpenAI-format message list.
        model:           Override primary OpenRouter model (optional).
        max_tokens:      Max tokens to generate (default 8192 for reasoning/thinking model headroom).
        temperature:     Sampling temperature.
        tools:           Optional tool definitions (function calling).
        tool_choice:     Optional tool_choice value.
        response_format: Optional response format (e.g. {"type": "json_object"}).

    Returns:
        openai ChatCompletion response object guaranteed to have valid choices[0].
    Raises:
        RuntimeError if all available tiers and models fail.
    """
    kwargs = dict(messages=messages, max_tokens=max_tokens, temperature=temperature)
    if tools:
        kwargs["tools"] = tools
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if response_format is not None:
        kwargs["response_format"] = response_format

    def _post_check(resp):
        if resp and hasattr(resp, "choices") and resp.choices:
            fr = getattr(resp.choices[0], "finish_reason", None)
            if fr == "length":
                print(f"  [llm_client] [WARN] Output truncated by max_tokens limit ({max_tokens})!")
        return resp

    errors_encountered = []

    # ── Tier 1: Gemini direct (Google AI Studio free quota) ──
    if GEMINI_API_KEY:
        gemini_models = [GEMINI_MODEL]
        for alt in ["gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-2.5-pro"]:
            if alt not in gemini_models:
                gemini_models.append(alt)

        gemini = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)
        for g_model in gemini_models:
            try:
                response = _call(gemini, g_model, kwargs)
                return _post_check(response)
            except Exception as e:
                errors_encountered.append(f"Gemini {g_model}: {e}")
                if not _is_retriable_error(e):
                    raise
                print(f"  [llm_client] [WARN] Gemini ({g_model}) failed: {e}. Trying next option...")

    # ── Tier 2: OpenRouter primary model ────────────────────────────────────
    openrouter = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    primary_model = model or OPENROUTER_MODEL
    try:
        response = _call(openrouter, primary_model, kwargs)
        return _post_check(response)
    except Exception as e:
        errors_encountered.append(f"OpenRouter Primary {primary_model}: {e}")
        if not _is_retriable_error(e):
            raise
        print(f"  [llm_client] [WARN] OpenRouter Tier 1 ({primary_model}) failed: {e}")

    # ── Tier 3: OpenRouter fallback models pool ─────────────────────────────
    # Deduplicate while preserving order, skipping primary_model
    candidate_fallbacks = []
    for cand in _OPENROUTER_FALLBACK_POOL:
        if cand and cand != primary_model and cand not in candidate_fallbacks:
            candidate_fallbacks.append(cand)

    for fb_model in candidate_fallbacks:
        try:
            print(f"  [llm_client] [INFO] OpenRouter Fallback -> {fb_model}")
            response = _call(openrouter, fb_model, kwargs)
            print(f"  [llm_client] [OK] OpenRouter Fallback ({fb_model}) responded.")
            return _post_check(response)
        except Exception as e:
            errors_encountered.append(f"OpenRouter {fb_model}: {e}")
            print(f"  [llm_client] [WARN] Fallback {fb_model} failed: {e}")
            if not _is_retriable_error(e):
                continue

    last_errors_str = " | ".join(errors_encountered[-3:])
    raise RuntimeError(
        f"All LLM tiers failed. Errors encountered: {last_errors_str}\n"
        "Check your API keys and network connection."
    )
