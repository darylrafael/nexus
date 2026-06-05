from apscheduler.schedulers.blocking import BlockingScheduler
from agents.market_agent import run_market_brief
from agents.evening_reviewer import run_evening_review
from agents.prediction_extractor import extract_predictions
from delivery.telegram import send_report
from memory.obsidian import write_note
from datetime import datetime

scheduler = BlockingScheduler()


def daily_brief():
    now          = datetime.now()
    date_key     = now.strftime("%Y-%m-%d")
    current_date = now.strftime("%B %d, %Y")

    print(f"\n[scheduler] 🌅 Morning brief — {now.strftime('%H:%M')}")

    result = run_market_brief()

    # Save note — evening_reviewer reads this by exact title
    title = f"{date_key} - IHSG Market Brief"
    write_note(title, f"# IHSG Daily Brief — {current_date}\n\n{result}")

    send_report(f"📊 *Nexus — IHSG Daily Brief*\n_{current_date}_\n\n{result}")
    print("[scheduler] Morning brief done ✅")


def evening_review():
    now      = datetime.now()
    date_key = now.strftime("%Y-%m-%d")

    print(f"\n[scheduler] 🌆 Evening review — {now.strftime('%H:%M')}")

    learning = run_evening_review()   # reads morning brief from Obsidian internally

    if learning is None:
        print("[scheduler] Evening review skipped — no morning brief found.")
        send_report(f"ℹ️ *Nexus Evening Review* — {date_key}\n_No morning brief found. Skipped._")
        return

    # Format Telegram message
    ihsg_icon = "✅" if learning["ihsg_correct"] else "❌"
    ff_icon   = "✅" if learning["foreign_flow_correct"] else "❌"
    pct       = learning.get("ihsg_actual_pct", 0)
    pct_str   = f"{pct:+.2f}%"

    msg = (
        f"🔁 *Nexus — Evening Review* | _{date_key}_\n\n"
        f"*IHSG* {ihsg_icon}: {learning['ihsg_predicted']} → {learning['ihsg_actual']} ({pct_str})\n"
        f"*Foreign Flow* {ff_icon}: {learning['foreign_flow_predicted']} → {learning['foreign_flow_actual']}\n"
        f"*USD/IDR*: {learning.get('actual_usdidr', 'N/A')}\n"
        f"*Accuracy*: {learning['accuracy_score']}% | Error: {learning['error_rate_pct']}%\n"
    )

    if learning.get("rca_unanticipated"):
        msg += f"\n*Missed factors*:\n"
        for f in learning["rca_unanticipated"][:3]:
            msg += f"  • {f}\n"

    if learning.get("lessons"):
        msg += f"\n*Lessons learned*:\n"
        for lesson in learning["lessons"][:2]:
            msg += f"  📌 {lesson}\n"

    msg += f"\n_{learning.get('summary', '')}_"

    send_report(msg)
    print("[scheduler] Evening review done ✅")


# Morning brief:   Mon-Fri 07:00
scheduler.add_job(daily_brief,    'cron', day_of_week='mon-fri', hour=7,  minute=0)

# Evening review:  Mon-Fri 19:00 (after market close + settlement buffer)
scheduler.add_job(evening_review, 'cron', day_of_week='mon-fri', hour=19, minute=0)


if __name__ == "__main__":
    print("Nexus scheduler started.")
    print("  🌅 Morning brief:    Mon-Fri 07:00")
    print("  🌆 Evening review:   Mon-Fri 19:00")
    print("Press Ctrl+C to stop.")
    scheduler.start()