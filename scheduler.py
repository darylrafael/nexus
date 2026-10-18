import os
import sys
import traceback

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from apscheduler.schedulers.blocking import BlockingScheduler
from agents.market_agent import run_market_brief
from agents.evening_reviewer import run_evening_review
from delivery.telegram import send_report
from memory.obsidian import write_note
from data_sources.market_data import jakarta_now
from core.calendar import is_idx_trading_day, get_holiday_reason
from core.paths import get_runs_dir, get_dashboard_runs_dir
from core.schedule import load_schedule_config
from core.locking import run_lock_context
from utils.dates import (
    resolve_evening_review_date,
    is_late_night_stale,
    should_delegate_to_evening_review,
)


def daily_brief(force: bool = False):
    """
    Execute daily morning brief pipeline with guards for holidays, weekends,
    prior completion idempotency, and concurrent runner locks.
    """
    now = jakarta_now()
    date_key = now.strftime("%Y-%m-%d")
    current_date = now.strftime("%B %d, %Y")

    is_forced = force or os.getenv("FORCE_RUN", "").lower() in ("true", "1", "yes")

    # Guard 1: IDX is closed on weekends and official exchange holidays / cuti bersama
    if not is_forced and not is_idx_trading_day(now):
        reason = get_holiday_reason(now) or "Market closed"
        print(f"\n[scheduler] Today ({date_key}) is non-trading day: {reason}. Skipping morning brief.")
        return

    runs_dir = get_runs_dir()
    dash_runs_dir = get_dashboard_runs_dir()
    brief_artifact = runs_dir / date_key / "morning_prediction.json"
    brief_artifact_dash = dash_runs_dir / date_key / "morning_prediction.json"
    review_artifact = runs_dir / date_key / "evening_review.json"
    review_artifact_dash = dash_runs_dir / date_key / "evening_review.json"

    brief_exists = brief_artifact.exists() or brief_artifact_dash.exists()
    review_exists = review_artifact.exists() or review_artifact_dash.exists()

    # Guard 2: Post-market delegation
    if not is_forced and should_delegate_to_evening_review(now, brief_exists, review_exists):
        print(f"\n[scheduler] Notice: daily_brief invoked at {now.strftime('%H:%M WIB')} (after market close 16:00 WIB).")
        print(f"[scheduler] Morning brief for {date_key} already exists, but evening review is pending.")
        print("[scheduler] Auto-delegating execution to evening_review()...")
        evening_review(force=False, target_date=date_key)
        return

    # Guard 3: Idempotency (already completed)
    if brief_exists and not is_forced:
        print(f"\n[scheduler] Morning brief for {date_key} already exists. Skipping duplicate execution.")
        return

    with run_lock_context(date_key, "morning_brief") as acquired:
        if not acquired:
            print(f"\n[scheduler] Another runner is currently executing morning brief for {date_key}. Skipping duplicate run.")
            return

        print(f"\n[scheduler] Morning brief starting -- {now.strftime('%H:%M')}")

        try:
            result = run_market_brief()

            # Save note — evening_reviewer reads this by exact title
            title = f"{date_key} - IHSG Market Brief"
            write_note(title, f"# IHSG Daily Brief -- {current_date}\n\n{result}")

            send_report(f"\U0001f4ca *Nexus -- IHSG Daily Brief*\n_{current_date}_\n\n{result}")
            print("[scheduler] Morning brief done.")

        except Exception as e:
            err = traceback.format_exc()
            print(f"[scheduler] ERROR - Morning brief crashed:\n{err}")
            try:
                from memory.session import log_session
                log_session(
                    query=f"daily_brief_{date_key}",
                    agent="scheduler",
                    success=False,
                    error_msg=str(e)[:500],
                )
            except Exception:
                pass

            # Record failed status artifact
            try:
                import json
                run_dir = get_runs_dir() / date_key
                run_dir.mkdir(parents=True, exist_ok=True)
                status_file = run_dir / "pipeline_status.json"
                status_file.write_text(json.dumps({
                    "stage": "morning_brief",
                    "status": "failed",
                    "date": date_key,
                    "error": str(e),
                    "failed_at": now.isoformat()
                }, indent=2), encoding="utf-8")
            except Exception:
                pass
            send_report(
                f"\u274c *Nexus -- Morning Brief FAILED*\n"
                f"_{now.strftime('%Y-%m-%d %H:%M')}_\n\n"
                f"`{str(e)[:400]}`"
            )
            raise


def evening_review(force: bool = False, target_date: str = None):
    """
    Execute evening review pipeline with holiday guards, late-night guards,
    and runner concurrency locks.
    """
    now = jakarta_now()
    is_forced = force or os.getenv("FORCE_RUN", "").lower() in ("true", "1", "yes")

    # Guard 1: Weekend and IDX holiday guard (unless a specific historical target_date is given)
    if not is_forced and not target_date and not os.getenv("TARGET_DATE") and not is_idx_trading_day(now):
        reason = get_holiday_reason(now) or "Market closed"
        print(f"\n[scheduler] Today ({now.strftime('%Y-%m-%d')}) is non-trading day: {reason}. Skipping evening review.")
        return

    # Guard 2: Late-night stale execution guard (Anti-2AM Telegram spam).
    if not is_forced and not target_date and not os.getenv("TARGET_DATE") and is_late_night_stale(now):
        print(f"\n[scheduler] Current time is {now.strftime('%H:%M WIB')}, outside the acceptable evening review window (16:00 - 22:59 WIB).")
        print("[scheduler] Skipping stale delayed execution to prevent waking user at 2 AM.")
        return

    date_key = resolve_evening_review_date(target_date)

    # Guard 3: If evaluating today, ensure market has closed (>= 16:00 WIB)
    today_key = now.strftime("%Y-%m-%d")
    if date_key == today_key and now.hour < 16 and not is_forced:
        print(f"\n[scheduler] Current time is {now.strftime('%H:%M WIB')} (before market close 16:00 WIB). Skipping review until market closes.")
        return

    runs_dir = get_runs_dir()
    dash_runs_dir = get_dashboard_runs_dir()
    review_artifact = runs_dir / date_key / "evening_review.json"
    review_artifact_dash = dash_runs_dir / date_key / "evening_review.json"
    if (review_artifact.exists() or review_artifact_dash.exists()) and not is_forced:
        print(f"\n[scheduler] Evening review for {date_key} already exists. Skipping duplicate execution.")
        return

    with run_lock_context(date_key, "evening_review") as acquired:
        if not acquired:
            print(f"\n[scheduler] Another runner is currently executing evening review for {date_key}. Skipping duplicate run.")
            return

        print(f"\n[scheduler] Evening review starting for session {date_key} -- {now.strftime('%H:%M WIB')}")

        try:
            learning = run_evening_review(date_key)

            if learning is None:
                status_file = get_runs_dir() / date_key / "pipeline_status.json"
                reason_msg = "no morning brief found"
                if status_file.exists():
                    try:
                        import json
                        s_data = json.loads(status_file.read_text(encoding="utf-8"))
                        if s_data.get("status") == "failed":
                            reason_msg = f"morning brief failed ({s_data.get('error', 'unknown error')[:120]})"
                    except Exception:
                        pass

                print(f"[scheduler] Evening review skipped -- {reason_msg}.")
                send_report(
                    f"\u2139\ufe0f *Nexus Evening Review* -- {date_key}\n"
                    f"_Execution skipped: {reason_msg}._"
                )
                return

            # Format Telegram message
            ihsg_icon = "✅" if learning.get("ihsg_correct") else "❌"
            ff_icon = "✅" if learning.get("foreign_flow_correct") else "❌"
            pct = learning.get("ihsg_actual_pct", 0)
            pct_str = f"{pct:+.2f}%"

            msg = (
                f"🔄 *Nexus -- Evening Review* | _{date_key}_\n\n"
                f"*IHSG* {ihsg_icon}: {learning.get('ihsg_predicted', 'N/A')} -> {learning.get('ihsg_actual', 'N/A')} ({pct_str})\n"
                f"*Foreign Flow* {ff_icon}: {learning.get('foreign_flow_predicted', 'N/A')} -> {learning.get('foreign_flow_actual', 'N/A')}\n"
                f"*USD/IDR*: {learning.get('actual_usdidr', 'N/A')}\n"
                f"*Accuracy*: {learning.get('accuracy_score', 0)}% | Error: {learning.get('error_rate_pct', 0)}%\n"
            )

            rca_items = []
            for f in learning.get("rca_unanticipated", []):
                rca_items.append(f"• [Tak Terduga] {f}")
            for f in learning.get("rca_overestimated", []):
                rca_items.append(f"• [Overestimated] {f}")
            for f in learning.get("rca_underestimated", []):
                rca_items.append(f"• [Underestimated] {f}")
            for f in learning.get("rca_inverse_correlation", []):
                rca_items.append(f"• [Korelasi Terbalik] {f}")

            if rca_items:
                msg += "\n*Root Cause Analysis*:\n"
                for item in rca_items[:4]:
                    msg += f"  {item}\n"

            if learning.get("lessons"):
                msg += "\n*Lessons Learned*:\n"
                for lesson in learning["lessons"][:2]:
                    msg += f"  💡 {lesson}\n"

            summary = learning.get("summary", "").strip()
            if summary:
                msg += f"\n📝 *Summary*:\n_{summary}_\n"

            send_report(msg)
            print("[scheduler] Evening review done.")

        except Exception as e:
            err = traceback.format_exc()
            print(f"[scheduler] ERROR - Evening review crashed:\n{err}")
            try:
                from memory.session import log_session
                log_session(
                    query=f"evening_review_{date_key}",
                    agent="scheduler",
                    success=False,
                    error_msg=str(e)[:500],
                )
            except Exception:
                pass

            send_report(
                f"\u274c *Nexus -- Evening Review FAILED*\n"
                f"_{now.strftime('%Y-%m-%d %H:%M')}_\n\n"
                f"`{str(e)[:400]}`"
            )
            raise


def create_scheduler() -> BlockingScheduler:
    """Build and configure BlockingScheduler based on schedule.yaml."""
    sched = BlockingScheduler(timezone="Asia/Jakarta")
    cfg = load_schedule_config()
    m_cfg = cfg["jobs"]["morning_brief"]
    e_cfg = cfg["jobs"]["evening_review"]

    sched.add_job(
        daily_brief,
        'cron',
        day_of_week=m_cfg.get("days_of_week", "mon-fri"),
        hour=m_cfg.get("hour_wib", 6),
        minute=m_cfg.get("minute_wib", 55),
    )
    sched.add_job(
        evening_review,
        'cron',
        day_of_week=e_cfg.get("days_of_week", "mon-fri"),
        hour=e_cfg.get("hour_wib", 20),
        minute=e_cfg.get("minute_wib", 0),
    )
    return sched


def start_scheduler():
    """Start the blocking scheduler process."""
    cfg = load_schedule_config()
    m_cfg = cfg["jobs"]["morning_brief"]
    e_cfg = cfg["jobs"]["evening_review"]

    print("Nexus scheduler started.")
    print(f"  Morning brief:  Mon-Fri {m_cfg.get('time_wib', '06:55')} WIB")
    print(f"  Evening review: Mon-Fri {e_cfg.get('time_wib', '20:00')} WIB")
    print("Press Ctrl+C to stop.")

    try:
        send_report(
            f"\U0001f7e2 *Nexus Scheduler Started*\n"
            f"_{jakarta_now().strftime('%Y-%m-%d %H:%M')}_\n\n"
            f"Morning brief: Mon-Fri {m_cfg.get('time_wib', '06:55')} WIB\n"
            f"Evening review: Mon-Fri {e_cfg.get('time_wib', '20:00')} WIB"
        )
    except Exception:
        pass

    sched = create_scheduler()
    sched.start()


if __name__ == "__main__":
    start_scheduler()
