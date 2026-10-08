import os
import sys
from pathlib import Path

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
import traceback
import subprocess
import shutil

scheduler = BlockingScheduler(timezone="Asia/Jakarta")


def push_artifacts_to_git(commit_message: str):
    """Auto sync runs to dashboard and push to GitHub so Vercel updates immediately."""
    try:
        root_dir = Path(__file__).parent
        dashboard_runs = root_dir / "dashboard" / "data" / "runs"
        dashboard_runs.mkdir(parents=True, exist_ok=True)
        for item in (root_dir / "runs").iterdir():
            dest = dashboard_runs / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

        # In GitHub Actions cloud runner, file sync is done.
        # Git commit & push are handled by the dedicated workflow runner step.
        if os.getenv("GITHUB_ACTIONS"):
            print("[scheduler] Running in GitHub Actions. Git commit/push delegated to workflow step.")
            return

        subprocess.run(["git", "add", "runs/", "dashboard/data/runs/"], cwd=str(root_dir), check=True)
        staged = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=str(root_dir))
        if staged.returncode != 0:
            subprocess.run(["git", "commit", "-m", commit_message], cwd=str(root_dir), check=True)
            subprocess.run(["git", "pull", "--no-edit", "-X", "ours", "origin", "main"], cwd=str(root_dir), check=True)
            subprocess.run(["git", "push", "origin", "main"], cwd=str(root_dir), check=True)
            print(f"[scheduler] Successfully pushed artifacts to GitHub: {commit_message}")
        else:
            print("[scheduler] No new artifacts to push to GitHub.")
    except Exception as e:
        print(f"[scheduler] Warning: Auto-push artifacts to GitHub skipped or failed: {e}")


def daily_brief(force: bool = False):
    now          = jakarta_now()
    date_key     = now.strftime("%Y-%m-%d")
    current_date = now.strftime("%B %d, %Y")

    is_forced = force or os.getenv("FORCE_RUN", "").lower() in ("true", "1", "yes")

    # Guard: IDX is closed on weekends (Saturday & Sunday)
    if now.weekday() >= 5 and not is_forced:
        print(f"\n[scheduler] Today is {now.strftime('%A')} (weekend). IDX market closed. Skipping morning brief.")
        return

    brief_artifact = Path(__file__).parent / "runs" / date_key / "morning_prediction.json"
    brief_artifact_dash = Path(__file__).parent / "dashboard" / "data" / "runs" / date_key / "morning_prediction.json"
    review_artifact = Path(__file__).parent / "runs" / date_key / "evening_review.json"
    review_artifact_dash = Path(__file__).parent / "dashboard" / "data" / "runs" / date_key / "evening_review.json"

    brief_exists = brief_artifact.exists() or brief_artifact_dash.exists()
    review_exists = review_artifact.exists() or review_artifact_dash.exists()

    # Intelligent post-market delegation:
    # If daily_brief is called after market close (>= 16:00 WIB), e.g. via an automated external
    # webhook / dispatch intended for evening review, check if today's evening review still needs to run.
    if now.hour >= 16 and not is_forced:
        if brief_exists and not review_exists:
            print(f"\n[scheduler] Notice: daily_brief invoked at {now.strftime('%H:%M WIB')} (after market close 16:00 WIB).")
            print(f"[scheduler] Morning brief for {date_key} already exists, but evening review is pending.")
            print(f"[scheduler] Auto-delegating execution to evening_review()...")
            evening_review(force=False, target_date=date_key)
            return

    if brief_exists and not is_forced:
        print(f"\n[scheduler] Morning brief for {date_key} already exists. Skipping duplicate execution.")
        return

    print(f"\n[scheduler] Morning brief starting -- {now.strftime('%H:%M')}")

    try:
        result = run_market_brief()

        # Save note — evening_reviewer reads this by exact title
        title = f"{date_key} - IHSG Market Brief"
        write_note(title, f"# IHSG Daily Brief -- {current_date}\n\n{result}")

        send_report(f"\U0001f4ca *Nexus -- IHSG Daily Brief*\n_{current_date}_\n\n{result}")
        print("[scheduler] Morning brief done.")

        push_artifacts_to_git(f"chore(data): auto-archive morning brief artifacts [{date_key}]")

    except Exception as e:
        err = traceback.format_exc()
        print(f"[scheduler] ERROR - Morning brief crashed:\n{err}")
        send_report(
            f"\u274c *Nexus -- Morning Brief FAILED*\n"
            f"_{now.strftime('%Y-%m-%d %H:%M')}_\n\n"
            f"`{str(e)[:400]}`"
        )
        raise


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

    runs_dir = Path(__file__).parent / "runs"
    if runs_dir.exists():
        import re
        from datetime import datetime
        candidate_dirs = sorted(
            [d.name for d in runs_dir.iterdir() if d.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", d.name)],
            reverse=True
        )
        for date_str in candidate_dirs:
            # Skip future dates
            if date_str > today_key:
                continue
            # Skip dates older than 4 calendar days
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                if (now.date() - dt).days > 4:
                    continue
            except Exception:
                continue
            # If candidate is today, only evaluate if market has closed (>= 16:00 WIB)
            if date_str == today_key and now.hour < 16:
                continue
            has_morning = (runs_dir / date_str / "morning_prediction.json").exists() or (runs_dir / date_str / "morning_brief.md").exists()
            has_evening = (runs_dir / date_str / "evening_review.json").exists()
            if has_morning and not has_evening:
                return date_str

    return today_key


def evening_review(force: bool = False, target_date: str = None):
    now       = jakarta_now()
    is_forced = force or os.getenv("FORCE_RUN", "").lower() in ("true", "1", "yes")

    # Guard 1: Weekend guard (unless a specific historical target_date is given)
    if now.weekday() >= 5 and not is_forced and not target_date and not os.getenv("TARGET_DATE"):
        print(f"\n[scheduler] Today is {now.strftime('%A')} (weekend). IDX market closed. Skipping evening review.")
        return

    # Guard 2: Late-night stale execution guard (Anti-2AM Telegram spam).
    # If GitHub Actions runner schedule was heavily delayed into the middle of the night
    # (between 23:00 WIB and 05:00 WIB next morning), do not send stale reviews unless explicitly forced.
    if (now.hour >= 23 or now.hour < 5) and not is_forced and not target_date and not os.getenv("TARGET_DATE"):
        print(f"\n[scheduler] Current time is {now.strftime('%H:%M WIB')}, outside the acceptable evening review window (16:00 - 22:59 WIB).")
        print(f"[scheduler] Skipping stale delayed execution to prevent waking user at 2 AM.")
        return

    date_key = resolve_evening_review_date(target_date)

    # Guard 3: If evaluating today, ensure market has closed (>= 16:00 WIB)
    if date_key == now.strftime("%Y-%m-%d") and now.hour < 16 and not is_forced:
        print(f"\n[scheduler] Market has not closed yet ({now.strftime('%H:%M WIB')} < 16:00 WIB). Skipping evening review.")
        return

    review_artifact = Path(__file__).parent / "runs" / date_key / "evening_review.json"
    review_artifact_dash = Path(__file__).parent / "dashboard" / "data" / "runs" / date_key / "evening_review.json"
    if (review_artifact.exists() or review_artifact_dash.exists()) and not is_forced:
        print(f"\n[scheduler] Evening review for {date_key} already exists. Skipping duplicate execution.")
        return

    print(f"\n[scheduler] Evening review starting for session {date_key} -- {now.strftime('%H:%M WIB')}")

    try:
        learning = run_evening_review(date_key)

        if learning is None:
            print("[scheduler] Evening review skipped -- no morning brief found.")
            send_report(
                f"\u2139\ufe0f *Nexus Evening Review* -- {date_key}\n"
                f"_No morning brief found. Skipped._"
            )
            return

        # Format Telegram message
        ihsg_icon = "✅" if learning.get("ihsg_correct") else "❌"
        ff_icon   = "✅" if learning.get("foreign_flow_correct") else "❌"
        pct       = learning.get("ihsg_actual_pct", 0)
        pct_str   = f"{pct:+.2f}%"

        msg = (
            f"🔄 *Nexus -- Evening Review* | _{date_key}_\n\n"
            f"*IHSG* {ihsg_icon}: {learning.get('ihsg_predicted', 'N/A')} -> {learning.get('ihsg_actual', 'N/A')} ({pct_str})\n"
            f"*Foreign Flow* {ff_icon}: {learning.get('foreign_flow_predicted', 'N/A')} -> {learning.get('foreign_flow_actual', 'N/A')}\n"
            f"*USD/IDR*: {learning.get('actual_usdidr', 'N/A')}\n"
            f"*Accuracy*: {learning.get('accuracy_score', 0)}% | Error: {learning.get('error_rate_pct', 0)}%\n"
        )

        # Root Cause Analysis: check all categories so none are dropped
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
            msg += f"\n*Root Cause Analysis*:\n"
            for item in rca_items[:4]:
                msg += f"  {item}\n"

        if learning.get("lessons"):
            msg += f"\n*Lessons Learned*:\n"
            for lesson in learning["lessons"][:2]:
                msg += f"  💡 {lesson}\n"

        summary = learning.get("summary", "").strip()
        if summary:
            msg += f"\n📝 *Summary*:\n_{summary}_\n"

        send_report(msg)
        print("[scheduler] Evening review done.")

        push_artifacts_to_git(f"chore(data): auto-archive evening review artifacts [{date_key}]")

    except Exception as e:
        err = traceback.format_exc()
        print(f"[scheduler] ERROR - Evening review crashed:\n{err}")
        send_report(
            f"\u274c *Nexus -- Evening Review FAILED*\n"
            f"_{now.strftime('%Y-%m-%d %H:%M')}_\n\n"
            f"`{str(e)[:400]}`"
        )
        raise


# Morning brief:  Mon-Fri 07:30 WIB
scheduler.add_job(daily_brief,    'cron', day_of_week='mon-fri', hour=7,  minute=30)

# Evening review: Mon-Fri 20:00 WIB
scheduler.add_job(evening_review, 'cron', day_of_week='mon-fri', hour=20, minute=0)


if __name__ == "__main__":
    print("Nexus scheduler started.")
    print("  Morning brief:  Mon-Fri 07:30 WIB")
    print("  Evening review: Mon-Fri 20:00 WIB")
    print("Press Ctrl+C to stop.")

    try:
        send_report(
            f"\U0001f7e2 *Nexus Scheduler Started*\n"
            f"_{jakarta_now().strftime('%Y-%m-%d %H:%M')}_\n\n"
            f"Morning brief: Mon-Fri 07:30 WIB\n"
            f"Evening review: Mon-Fri 20:00 WIB"
        )
    except Exception:
        pass

    scheduler.start()
