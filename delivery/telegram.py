import asyncio
import html
import re
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils.text import split_text

MAX_TELEGRAM_MESSAGE_LEN = 3900


def clean_telegram_text(text: str) -> str:
    """Strip raw source hashes like (src_8f5433ebce) to keep Telegram briefs elegant and prevent broken entity errors."""
    if not text:
        return ""
    cleaned = re.sub(r"[\(\[]?\s*(?:Source(?:\s*ID)?:?\s*)?src_[a-fA-F0-9_-]+\s*[\)\]]?", "", text)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def markdown_to_safe_html(text: str) -> str:
    """
    Convert markdown bold, italic, and inline code to Telegram-compatible HTML,
    safely escaping HTML special characters (&, <, >) to avoid parse errors.
    """
    if not text:
        return ""

    # First, HTML-escape everything
    escaped = html.escape(text)

    # Convert code blocks ```text``` -> <pre>text</pre>
    escaped = re.sub(r"```([\s\S]*?)```", r"<pre>\1</pre>", escaped)

    # Convert inline code `text` -> <code>text</code>
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)

    # Convert bold *text* -> <b>text</b> (avoid matching single asterisks)
    escaped = re.sub(r"\*([^\*\n]+)\*", r"<b>\1</b>", escaped)

    # Convert italic _text_ -> <i>text</i> (only when preceded/followed by non-alphanumeric to avoid snake_case)
    escaped = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"<i>\1</i>", escaped)

    return escaped


async def _send_chunk(bot: telegram.Bot, chunk: str) -> None:
    """Send a single chunk with HTML formatting, falling back to plain text, and handling rate limits."""
    html_chunk = markdown_to_safe_html(chunk)

    for attempt in range(3):
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=html_chunk,
                parse_mode="HTML",
            )
            return
        except telegram.error.RetryAfter as err:
            wait_time = max(int(err.retry_after), 1) + 1
            print(f"  [telegram] Rate limited. Retrying after {wait_time}s...")
            await asyncio.sleep(wait_time)
        except Exception as e:
            # If HTML parsing fails, fallback to plain text
            print(f"  [telegram] HTML parse error ({e}), falling back to plain text...")
            try:
                await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=chunk)
                return
            except telegram.error.RetryAfter as retry_err:
                wait_time = max(int(retry_err.retry_after), 1) + 1
                await asyncio.sleep(wait_time)
            except Exception as final_err:
                print(f"  [telegram] send failed: {final_err}")
                return


async def _send(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [telegram] skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured")
        return

    formatted_text = clean_telegram_text(text)
    chunks = split_text(formatted_text, MAX_TELEGRAM_MESSAGE_LEN)

    request = telegram.request.HTTPXRequest(connection_pool_size=8, connect_timeout=15, read_timeout=30)
    async with telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request) as bot:
        for chunk in chunks:
            await _send_chunk(bot, chunk)


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
