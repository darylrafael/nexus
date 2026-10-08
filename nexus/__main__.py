import argparse
import sys
from pathlib import Path

# Ensure workspace root is in python path
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from scheduler import daily_brief, evening_review, start_scheduler


def main():
    parser = argparse.ArgumentParser(
        prog="python -m nexus",
        description="Nexus: IHSG multi-agent market intelligence pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand to execute")

    # Command: brief
    brief_parser = subparsers.add_parser("brief", help="Run morning brief pipeline")
    brief_parser.add_argument("--force", action="store_true", help="Force run ignoring weekend/duplicate guards")

    # Command: review
    review_parser = subparsers.add_parser("review", help="Run evening review pipeline")
    review_parser.add_argument("--force", action="store_true", help="Force run ignoring weekend/window guards")
    review_parser.add_argument("--date", type=str, default=None, help="Target date to evaluate (YYYY-MM-DD)")

    # Command: serve
    subparsers.add_parser("serve", help="Start local scheduler daemon")

    args = parser.parse_args()

    if args.command == "brief":
        daily_brief(force=args.force)
    elif args.command == "review":
        evening_review(force=args.force, target_date=args.date)
    elif args.command == "serve":
        start_scheduler()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
