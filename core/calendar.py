import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Union
from core.paths import get_data_dir
from core.time import jakarta_now

HOLIDAYS_PATH: Optional[Path] = None

_CACHED_HOLIDAYS: Optional[dict[str, str]] = None


def _get_holidays_path() -> Path:
    if HOLIDAYS_PATH is not None:
        return Path(HOLIDAYS_PATH)
    return get_data_dir() / "idx_holidays.json"


def load_idx_holidays(force_reload: bool = False) -> dict[str, str]:
    """
    Load official IDX trading holidays and cuti bersama from JSON into a dict mapping 'YYYY-MM-DD' -> holiday name.
    """
    global _CACHED_HOLIDAYS
    if _CACHED_HOLIDAYS is not None and not force_reload:
        return _CACHED_HOLIDAYS

    holidays_map = {}
    h_path = _get_holidays_path()
    if h_path.exists():
        try:
            data = json.loads(h_path.read_text(encoding="utf-8"))
            for year, entries in data.get("holidays", {}).items():
                for item in entries:
                    d_str = item.get("date")
                    name = item.get("name", "Libur Bursa")
                    if d_str:
                        holidays_map[d_str] = name
        except Exception as e:
            print(f"[calendar] Warning: failed to parse {h_path}: {e}")

    _CACHED_HOLIDAYS = holidays_map
    return _CACHED_HOLIDAYS


def _normalize_date(dt: Union[str, date, datetime]) -> date:
    if isinstance(dt, datetime):
        return dt.date()
    elif isinstance(dt, date):
        return dt
    elif isinstance(dt, str):
        return datetime.strptime(dt[:10], "%Y-%m-%d").date()
    raise ValueError(f"Unsupported date format: {dt}")


def is_idx_trading_day(target_date: Union[str, date, datetime]) -> bool:
    """
    Check if target_date is a valid IDX trading day (Monday to Friday, excluding official IDX holidays).
    """
    d = _normalize_date(target_date)
    # Saturday (5) or Sunday (6)
    if d.weekday() >= 5:
        return False

    holidays = load_idx_holidays()
    date_str = d.strftime("%Y-%m-%d")
    return date_str not in holidays


def get_holiday_reason(target_date: Union[str, date, datetime]) -> Optional[str]:
    """
    Return human-readable reason if target_date is a non-trading day (weekend or holiday name), else None.
    """
    d = _normalize_date(target_date)
    if d.weekday() == 5:
        return "Weekend (Saturday)"
    if d.weekday() == 6:
        return "Weekend (Sunday)"

    holidays = load_idx_holidays()
    date_str = d.strftime("%Y-%m-%d")
    return holidays.get(date_str)


def get_last_trading_day(reference_date: Union[str, date, datetime] = None) -> str:
    """
    Walk backwards strictly before reference_date to find the most recent IDX trading day.
    """
    if reference_date is None:
        ref_d = jakarta_now().date()
    else:
        ref_d = _normalize_date(reference_date)

    cur = ref_d - timedelta(days=1)
    while not is_idx_trading_day(cur):
        cur -= timedelta(days=1)
    return cur.strftime("%Y-%m-%d")


def get_trading_day_or_previous(reference_date: Union[str, date, datetime] = None) -> str:
    """
    If reference_date is a trading day, return it. Otherwise walk backwards to nearest trading day.
    """
    if reference_date is None:
        ref_d = jakarta_now().date()
    else:
        ref_d = _normalize_date(reference_date)

    cur = ref_d
    while not is_idx_trading_day(cur):
        cur -= timedelta(days=1)
    return cur.strftime("%Y-%m-%d")


def get_next_trading_day(
    reference_date: Union[str, date, datetime] = None,
    include_today: bool = False,
) -> str:
    """
    Find the next IDX trading day.
    If include_today is True and reference_date is a trading day, return reference_date.
    Otherwise, walk forward strictly after reference_date.
    """
    if reference_date is None:
        ref_d = jakarta_now().date()
    else:
        ref_d = _normalize_date(reference_date)

    if include_today and is_idx_trading_day(ref_d):
        return ref_d.strftime("%Y-%m-%d")

    cur = ref_d + timedelta(days=1)
    while not is_idx_trading_day(cur):
        cur += timedelta(days=1)
    return cur.strftime("%Y-%m-%d")

