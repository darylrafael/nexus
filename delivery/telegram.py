import asyncio
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


async def _send(text: str):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    # Telegram has 4096 char limit per message
    for i in range(0, len(text), 4000):
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text[i:i+4000])


def send_report(text: str):
    try:
        asyncio.run(_send(text))
        print("  [telegram] report sent")
    except Exception as e:
        print(f"  [telegram] failed: {e}")
