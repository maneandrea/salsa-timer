"""
Salsa CLI: Simple timesheet logger

Usage:
  salsa start          # Start a new timesheet entry
  salsa task <desc>    # Register the completion of a task
  salsa pause          # Pause the current task without ending it
  salsa resume         # Resume a paused task
  salsa stop <desc>    # Register a final task and stop the entry
  salsa status         # Check the current status
  salsa show           # Like status, but keeps updating while running
  salsa log            # Browse previous entries
  salsa today          # Summarize today's tasks and their durations
  salsa edit           # Edit the raw JSONL file with a text editor of choice
  salsa undo           # Delete the last log entry
  salsa clear <scope>  # Clean up files ("all" or "today")
  salsa --version      # Show the installed version
"""

import argparse
from importlib.metadata import version as _pkg_version

from salsa.query import salsa_clear, salsa_log, salsa_show, salsa_status, salsa_today
from salsa.timer import salsa_edit, salsa_pause, salsa_resume, salsa_start, salsa_stop, salsa_task, salsa_undo
from salsa.utils import valid_date, valid_time


def main() -> None:
    parser = argparse.ArgumentParser(description="Salsa: Simple timesheet CLI")
    parser.add_argument("-v", "--version", action="store_true", help="display the current version")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a new timesheet entry")
    start_parser.add_argument("-t", "--time", help="Use a different time than now (HH:MM)", type=valid_time)

    stop_parser = subparsers.add_parser("stop", help="Stop the current timesheet entry")
    stop_parser.add_argument("description", help="What did you complete?")
    stop_parser.add_argument("-t", "--time", help="Use a different time than now (HH:MM)", type=valid_time)
    stop_parser.add_argument(
        "-d",
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
        "-d",
        "--detailed",
        action="store_true",
        default=False,
        help="Print individual events below each session row",
    )

    _status_parser = subparsers.add_parser("status", help="Show current session status")

    pause_parser = subparsers.add_parser("pause", help="Pause the current task without ending it")
    pause_parser.add_argument("-t", "--time", help="Use a different time than now (HH:MM)", type=valid_time)

    resume_parser = subparsers.add_parser("resume", help="Resume a paused task")
    resume_parser.add_argument("-t", "--time", help="Use a different time than now (HH:MM)", type=valid_time)

    _show_parser = subparsers.add_parser("show", help="Shows the status and continuously updates if running")

    clear_parser = subparsers.add_parser("clear", help="Cleanup data")
    clear_parser.add_argument("scope", help="What to eliminate", choices=["all", "today"])

    _undo_parser = subparsers.add_parser("undo", help="Delete the last entry")

    task_parser = subparsers.add_parser("task", help="Register the completion of a task")
    task_parser.add_argument("description", help="What did you complete?")
    task_parser.add_argument("-t", "--time", help="Use a different time than now (HH:MM)", type=valid_time)
    task_parser.add_argument(
        "-d",
        "--deliverable",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Optional deliverable as evidence of the task, passed by key and value. May be passed multiple times",
    )
    task_parser.add_argument(
        "-p",
        "--pause",
        action="store_true",
        help="Pause immediately after closing this task (same as calling salsa pause just after)",
    )

    today_parser = subparsers.add_parser("today", help="Get a string summarizing the last log entry")
    today_parser.add_argument(
        "-d",
        "--date",
        help="Use a date other than today (YYYY-MM-DD or words like 'yesterday' or '3 days ago')",
        type=valid_date,
    )

    edit_parser = subparsers.add_parser("edit", help="Edit a specific entry by opening the raw JSONL file")
    edit_parser.add_argument(
        "-d",
        "--date",
        help="Use a date other than today (YYYY-MM-DD or words like 'yesterday' or '3 days ago')",
        type=valid_date,
    )
    edit_parser.add_argument(
        "-e", "--editor", help="Use this text editor to edit the entry (default: vim)", default="vim"
    )

    args = parser.parse_args()

    if args.version:
        print("salsa", _pkg_version("salsa"))
        return

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
        salsa_task(args.time, args.description, deliverables=dict(args.deliverable or []), pause=args.pause)
    elif args.command == "today":
        salsa_today(args.date)
    elif args.command == "edit":
        salsa_edit(args.date, args.editor)
    else:
        salsa_show()


if __name__ == "__main__":
    main()
