import asyncio
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.text import split_text

import re

MAX_TELEGRAM_MESSAGE_LEN = 4000


def clean_telegram_text(text: str) -> str:
    """Strip raw source hashes like (src_8f5433ebce) to keep Telegram briefs elegant and prevent broken entity errors."""
    if not text:
        return ""
    cleaned = re.sub(r"[\(\[]?\s*(?:Source(?:\s*ID)?:?\s*)?src_[a-fA-F0-9_-]+\s*[\)\]]?", "", text)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


async def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [telegram] skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured")
        return

    formatted_text = clean_telegram_text(text)

    # Configure request to avoid timeouts
    request = telegram.request.HTTPXRequest(connection_pool_size=8, connect_timeout=15, read_timeout=30)
    async with telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request) as bot:
        for chunk in split_text(formatted_text, MAX_TELEGRAM_MESSAGE_LEN):
            try:
                await bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=chunk,
                    parse_mode="Markdown",
                )
            except Exception as e:
                print(f"  [telegram] markdown failed, sending plain text: {e}")
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk)


def send_report(text: str):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send(text))
            print("  [telegram] report sent")
        finally:
            loop.close()
    except Exception as e:
        print(f"  [telegram] failed: {e}")
