import yaml
from pathlib import Path
from typing import Any

SCHEDULE_FILE = Path(__file__).parent.parent / "schedule.yaml"

_DEFAULT_SCHEDULE = {
    "timezone": "Asia/Jakarta",
    "jobs": {
        "morning_brief": {
            "name": "Nexus Morning Brief",
            "time_wib": "06:55",
            "hour_wib": 6,
            "minute_wib": 55,
            "days_of_week": "mon,tue,wed,thu,fri",
            "cron_utc": "55 23 * * 0-4",
            "description": "IHSG Pre-Market Briefing & Sector Prediction"
        },
        "evening_review": {
            "name": "Nexus Evening Review",
            "time_wib": "20:00",
            "hour_wib": 20,
            "minute_wib": 0,
            "days_of_week": "mon,tue,wed,thu,fri",
            "cron_utc": "0 13 * * 1-5",
            "description": "Post-Market Evaluation, Prediction Scoring & Lessons"
        }
    }
}


def load_schedule_config() -> dict[str, Any]:
    """Load canonical schedule definition from schedule.yaml."""
    if SCHEDULE_FILE.exists():
        try:
            return yaml.safe_load(SCHEDULE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[schedule] Failed to parse {SCHEDULE_FILE}: {e}")
    return _DEFAULT_SCHEDULE


def get_job_schedule(job_name: str) -> dict[str, Any]:
    config = load_schedule_config()
    jobs = config.get("jobs", {})
    if job_name in jobs:
        return jobs[job_name]
    raise KeyError(f"Job '{job_name}' not defined in schedule config.")
