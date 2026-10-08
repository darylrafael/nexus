from datetime import datetime
from zoneinfo import ZoneInfo

JAKARTA_TZ = ZoneInfo("Asia/Jakarta")


def jakarta_now() -> datetime:
    """Return timezone-aware datetime in Asia/Jakarta timezone."""
    return datetime.now(JAKARTA_TZ)
