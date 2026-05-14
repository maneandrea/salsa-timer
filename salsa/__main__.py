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

from salsa.query import salsa_clear, salsa_log, salsa_show, salsa_status
from salsa.timer import salsa_pause, salsa_resume, salsa_start, salsa_stop
from salsa.utils import valid_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Salsa: Simple timesheet CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a new timesheet entry")
    start_parser.add_argument("description", nargs="*", help="Description of the task (optional)")
    start_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)

    stop_parser = subparsers.add_parser("stop", help="Stop the current timesheet entry")
    stop_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)

    log_parser = subparsers.add_parser("log", help="Show log entries")
    log_parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Show entries since date (YYYY-MM-DD), default: today",
    )
    log_parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        default=False,
        help="Print individual events below each session row",
    )

    _status_parser = subparsers.add_parser("status", help="Show current session status")

    pause_parser = subparsers.add_parser("pause", help="Pause the current task without ending it")
    pause_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)

    resume_parser = subparsers.add_parser("resume", help="Resume a paused task")
    resume_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)

    _show_parser = subparsers.add_parser("show", help="Shows the status and continuously updates if running")

    clear_parser = subparsers.add_parser("clear", help="Cleanup data")
    clear_parser.add_argument("scope", help="What to eliminate", choices=["all", "today"])

    args = parser.parse_args()

    if args.command == "start":
        desc = " ".join(args.description) if args.description else None
        salsa_start(desc, args.time)
    elif args.command == "stop":
        salsa_stop(args.time)
    elif args.command == "log":
        salsa_log(args.since, detailed=args.detailed)
    elif args.command == "status":
        salsa_status()
    elif args.command == "clear":
        salsa_clear(args.scope)
    elif args.command == "pause":
        salsa_pause(args.time)
    elif args.command == "resume":
        salsa_resume(args.time)
    elif args.command == "show":
        salsa_show()
    else:
        salsa_show()


if __name__ == "__main__":
    main()
