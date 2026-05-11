"""
Salsa CLI: Simple timesheet logger

Usage:
  salsa start [description]   # Start logging time with a description
  salsa stop                  # Stop logging and save the entry
  salsa clear                 # Clean up files
  salsa log                   # Browse previous entries
  salsa status                # Check the current status
"""

import argparse

from salsa.query import salsa_clear, salsa_log, salsa_status
from salsa.timer import salsa_start, salsa_stop


def main() -> None:
    parser = argparse.ArgumentParser(description="Salsa: Simple timesheet CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a new timesheet entry")
    start_parser.add_argument(
        "description", nargs="*", help="Description of the task (optional)"
    )

    _stop_parser = subparsers.add_parser(
        "stop", help="Stop the current timesheet entry"
    )

    log_parser = subparsers.add_parser("log", help="Show log entries")
    log_parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Show entries since date (YYYY-MM-DD), default: today",
    )

    _status_parser = subparsers.add_parser("status", help="Show current session status")

    clear_parser = subparsers.add_parser("clear", help="Cleanup data")
    clear_parser.add_argument(
        "scope", help="What to eliminate", choices=["all", "today"]
    )

    args = parser.parse_args()

    if args.command == "start":
        desc = " ".join(args.description) if args.description else None
        salsa_start(desc)
    elif args.command == "stop":
        salsa_stop()
    elif args.command == "log":
        salsa_log(args.since)
    elif args.command == "status":
        salsa_status()
    elif args.command == "clear":
        salsa_clear(args.scope)
    else:
        salsa_status()


if __name__ == "__main__":
    main()
