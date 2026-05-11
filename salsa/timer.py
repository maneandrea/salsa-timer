from datetime import datetime

from salsa.query import get_most_recent_description
from salsa.types import LogEntry
from salsa.utils import append_data, get_today_path, load_data


def salsa_start(description: str | None) -> None:
    path = get_today_path()
    data = load_data(path)
    # Check if last event is a 'start' without a matching 'end'
    running = False
    for entry in reversed(data):
        if entry["event"] == "start":
            running = True
            break
        elif entry["event"] == "end":
            break
    if running:
        print("A session is already running. Stop it first.")
        return
    if not description:
        description = get_most_recent_description()
    if not description:
        print("Must provide a description for the first entry.")
        return
    entry = LogEntry(
        event="start",
        datetime=datetime.now(),
        description=description,
    )
    append_data(path, [entry])
    print(f"Started: {description}")


def salsa_stop() -> None:
    path = get_today_path()
    data = load_data(path)
    # Find if there is a running session (last unmatched 'start')
    running = False
    # Use the most recent description for the end event
    description = None
    for entry in reversed(data):
        if entry["event"] == "start":
            running = True
            description = entry["description"]
            break
        if entry["event"] == "end":
            break
    if not running:
        print("No running session to stop.")
        return
    entry = LogEntry(
        event="end",
        datetime=datetime.now(),
        description=description or "",
    )
    append_data(path, [entry])
    print(f"Stopped: {description}")
