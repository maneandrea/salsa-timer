from datetime import datetime
from uuid import uuid4

from salsa.query import get_most_recent_description
from salsa.types import Event, LogEntry
from salsa.utils import (
    append_data,
    get_last_entry,
    get_today_path,
    is_stopped,
)


def salsa_start(description: str | None) -> None:
    if not is_stopped():
        print("A session is already running. Stop it first.")
        return
    if not description:
        description = get_most_recent_description()
    if not description:
        print("Must provide a description for the first entry.")
        return
    task_id = uuid4()
    entry = LogEntry(
        task_id=task_id,
        event=Event.START,
        datetime=datetime.now(),
        description=description,
    )
    append_data(get_today_path(), [entry])
    print(f"Started: {description} ({task_id.hex[:6]}…)")


def salsa_pause() -> None:
    last_entry = get_last_entry([Event.START, Event.RESUME])
    if not last_entry:
        print("No running session to pause.")
        return
    task_id = last_entry["task_id"]
    description = last_entry["description"]
    entry = LogEntry(
        task_id=last_entry["task_id"],
        event=Event.PAUSE,
        datetime=datetime.now(),
        description=description,
    )
    append_data(get_today_path(), [entry])
    print(f"Paused: {description} ({task_id.hex[:6]}…)")


def salsa_stop() -> None:
    last_entry = get_last_entry([Event.START, Event.RESUME])
    if not last_entry:
        print("No running session to pause.")
        return
    task_id = last_entry["task_id"]
    description = last_entry["description"]
    entry = LogEntry(
        task_id=last_entry["task_id"],
        event=Event.STOP,
        datetime=datetime.now(),
        description=description,
    )
    append_data(get_today_path(), [entry])
    print(f"Stopped: {description} ({task_id.hex[:6]}…)")


def salsa_resume() -> None:
    last_entry = get_last_entry([Event.PAUSE])
    if not last_entry:
        print("No paused session to resume.")
        return
    task_id = last_entry["task_id"]
    description = last_entry["description"]
    entry = LogEntry(
        task_id=last_entry["task_id"],
        event=Event.RESUME,
        datetime=datetime.now(),
        description=description,
    )
    append_data(get_today_path(), [entry])
    print(f"Resumed: {description} ({task_id.hex[:6]}…)")
