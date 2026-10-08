import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from data_sources.market_data import jakarta_now


def resolve_evening_review_date(target_date: str = None) -> str:
    """
    Resolve which session date to evaluate for evening review:
    1. If target_date is given (or TARGET_DATE env var), use it.
    2. Check the most recent session directory in `runs/` that has
       morning_prediction.json (or morning_brief.md) and NO evening_review.json.
       If that date is today, only select it if the market has closed (after 16:00 WIB).
    3. If all sessions have reviews, default to today in Jakarta time.
    """
    if target_date:
        return target_date
    env_date = os.getenv("TARGET_DATE")
    if env_date:
        return env_date

    now = jakarta_now()
    today_key = now.strftime("%Y-%m-%d")

    runs_dir = Path(__file__).parent.parent / "runs"
    if runs_dir.exists():
        candidate_dirs = sorted(
            [d.name for d in runs_dir.iterdir() if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)],
            reverse=True
        )
        for date_str in candidate_dirs:
            if date_str > today_key:
                continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                if (now.date() - dt).days > 4:
                    continue
            except Exception:
                continue
            if date_str == today_key and now.hour < 16:
                continue
            has_morning = (runs_dir / date_str / "morning_prediction.json").exists() or (runs_dir / date_str / "morning_brief.md").exists()
            has_evening = (runs_dir / date_str / "evening_review.json").exists()
            if has_morning and not has_evening:
                return date_str

    return today_key


def is_late_night_stale(now: datetime) -> bool:
    """
    Anti-2AM stale execution guard. Returns True if current time is between
    23:00 WIB and 05:00 WIB next morning (outside acceptable evening review window).
    """
    return now.hour >= 23 or now.hour < 5


def should_delegate_to_evening_review(now: datetime, brief_exists: bool, review_exists: bool) -> bool:
    """
    Returns True if daily_brief is called after market close (>= 16:00 WIB)
    and morning brief already exists while evening review is pending.
    """
    return now.hour >= 16 and brief_exists and not review_exists
