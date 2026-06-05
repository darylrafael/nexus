from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPINFRA_TOKEN = os.getenv("DEEPINFRA_TOKEN")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

OPENROUTER_MODEL = "openai/gpt-oss-120b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
KIMI_MODEL = "moonshotai/Kimi-K2.6"
DEEPINFRA_BASE_URL = "https://api.deepinfra.com/v1/openai"
OBSIDIAN_BASE_URL = "https://127.0.0.1:27124"
