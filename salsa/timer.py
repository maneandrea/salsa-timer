from datetime import time
from uuid import uuid4

from salsa.query import get_most_recent_description
from salsa.types import Event, LogEntry
from salsa.utils import (
    append_data,
    coalesce_time,
    get_last_entry,
    get_today_path,
    is_stopped,
    load_data,
    write_data,
)


def _transition(expected: list[Event], new_event: Event, verb: str, override_time: time | None) -> None:
    last_entry = get_last_entry(expected)
    if not last_entry:
        print(f"No session to {verb}.")
        return
    task_id = last_entry["task_id"]
    entry = LogEntry(
        task_id=task_id,
        event=new_event,
        datetime=coalesce_time(override_time),
        description=last_entry["description"],
    )
    append_data(get_today_path(), [entry])
    print(f"{verb.capitalize()}d: {last_entry['description']} ({task_id.hex[:6]}…)")


def salsa_start(description: str | None, override_time: time | None) -> None:
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
        datetime=coalesce_time(override_time),
        description=description,
    )
    append_data(get_today_path(), [entry])
    print(f"Started: {description} ({task_id.hex[:6]}…)")


def salsa_pause(override_time: time | None) -> None:
    _transition([Event.START, Event.RESUME], Event.PAUSE, "pause", override_time)


def salsa_stop(override_time: time | None) -> None:
    _transition([Event.START, Event.RESUME], Event.STOP, "stop", override_time)


def salsa_resume(override_time: time | None) -> None:
    _transition([Event.PAUSE], Event.RESUME, "resume", override_time)


def salsa_undo() -> None:
    path = get_today_path()
    data = load_data(path)
    if not data:
        print("Nothing to undo.")
        return
    removed = data[-1]
    write_data(path, data[:-1])
    print(f"Undone: {removed['event'].value} {removed['description']} ({removed['task_id'].hex[:6]}…)")
