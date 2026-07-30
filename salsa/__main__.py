"""
Salsa CLI: Simple timesheet logger

Usage:
  salsa start   # Start logging time
  salsa stop    # Stop logging
  salsa clear   # Clean up files
  salsa log     # Browse previous entries
  salsa status  # Check the current status
"""

import argparse

from salsa.query import salsa_clear, salsa_log, salsa_show, salsa_status, salsa_today
from salsa.timer import salsa_pause, salsa_resume, salsa_start, salsa_stop, salsa_task, salsa_undo
from salsa.utils import valid_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Salsa: Simple timesheet CLI")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a new timesheet entry")
    start_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)

    stop_parser = subparsers.add_parser("stop", help="Stop the current timesheet entry")
    stop_parser.add_argument("description", help="What did you complete?")
    stop_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)
    stop_parser.add_argument(
        "--deliverable",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Optional deliverable as evidence of the task, passed by key and value. May be passed multiple times",
    )

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

    _undo_parser = subparsers.add_parser("undo", help="Delete the last entry")

    task_parser = subparsers.add_parser("task", help="Register the completion of a task")
    task_parser.add_argument("description", help="What did you complete?")
    task_parser.add_argument("--time", "-t", help="Use a different time than now (HH:MM)", type=valid_time)
    task_parser.add_argument(
        "--deliverable",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Optional deliverable as evidence of the task, passed by key and value. May be passed multiple times",
    )

    _today_parser = subparsers.add_parser("today", help="Get a string summarizing the last log entry")

    args = parser.parse_args()

    if args.command == "start":
        salsa_start(args.time)
    elif args.command == "stop":
        salsa_stop(args.time, args.description, deliverables=dict(args.deliverable or []))
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
    elif args.command == "undo":
        salsa_undo()
    elif args.command == "task":
        salsa_task(args.time, args.description, deliverables=dict(args.deliverable or []))
    elif args.command == "today":
        salsa_today()
    else:
        salsa_show()


if __name__ == "__main__":
    main()
