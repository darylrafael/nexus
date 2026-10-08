from dotenv import load_dotenv
import os

load_dotenv()

REQUIRED_CONFIG_VARS = [
    "OPENROUTER_API_KEY",
    "TAVILY_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
]


def validate_config(required_vars=None, allow_skip=True):
    """Validate that required environment variables are present.

    Fails loudly listing ONLY missing variable names, never printing any values.
    """
    if allow_skip and os.getenv("NEXUS_SKIP_ENV_VALIDATION", "").lower() in ("1", "true", "yes"):
        return []

    keys_to_check = required_vars if required_vars is not None else REQUIRED_CONFIG_VARS
    missing = [key for key in keys_to_check if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            f"Configuration error: Missing required environment variable(s): {', '.join(missing)}. "
            f"Set them in your .env or environment. See .env.example."
        )
    return missing


# Run startup validation check
validate_config()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPINFRA_TOKEN = os.getenv("DEEPINFRA_TOKEN")  # reserved — not currently used by any agent
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL", "qwen/qwen3.8-27b:free"
)
OPENROUTER_FALLBACK_MODEL = os.getenv(
    "OPENROUTER_FALLBACK_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
)
OPENROUTER_BASE_URL       = "https://openrouter.ai/api/v1"

# Gemini — optional fallback tier 2 (only used if GEMINI_API_KEY is set)
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

OBSIDIAN_BASE_URL = os.getenv("OBSIDIAN_BASE_URL", "https://127.0.0.1:27124")
