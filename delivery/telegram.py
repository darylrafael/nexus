import asyncio
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

MAX_TELEGRAM_MESSAGE_LEN = 4000


async def _send(text: str):
    # Configure request to avoid timeouts
    request = telegram.request.HTTPXRequest(connection_pool_size=8, connect_timeout=15, read_timeout=30)
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request)
    
    # Smart chunking by paragraph to avoid breaking markdown formatting
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 > MAX_TELEGRAM_MESSAGE_LEN:
            chunks.append(current_chunk.strip())
            current_chunk = p + "\n\n"
        else:
            current_chunk += p + "\n\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    for chunk in chunks:
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
