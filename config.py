from dotenv import load_dotenv
import os

load_dotenv()

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
    "OPENROUTER_FALLBACK_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
)
OPENROUTER_BASE_URL       = "https://openrouter.ai/api/v1"

# Gemini — optional fallback tier 2 (only used if GEMINI_API_KEY is set)
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

OBSIDIAN_BASE_URL = "https://127.0.0.1:27124"
