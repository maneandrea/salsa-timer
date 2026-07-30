from datetime import datetime, time
from uuid import uuid4

from salsa.types import EntryEvent, Event, LogEntry, TaskEvent
from salsa.utils import (
    append_data,
    coalesce_time,
    get_last_entry,
    get_today_path,
    is_stopped,
    load_data,
    write_data,
)


def _transition(expected: list[Event], new_event: Event, when: datetime) -> None:
    """Appends new_event as a continuation of today's last entry, if eligible.

    Looks up today's last log entry and checks it against expected; if it
    matches, appends new_event under the same entry_id. Otherwise prints a
    message and does nothing.

    Args:
        expected (list[Event]): events the last entry must match for the
            transition to be allowed.
        new_event (Event): event to append.
        when (datetime): timestamp to record the event at.
    """
    last_entry = get_last_entry(expected)
    if not last_entry:
        print(f"No session to {new_event.verb()}.")
        return
    entry_id = last_entry.entry_id
    entry = LogEntry(
        entry_id=entry_id,
        event=new_event,
        datetime=when,
    )
    append_data(get_today_path(), [entry])
    display = entry.display()
    if display:
        display += " "
    print(f"{new_event.past_verb()}: {display}({entry_id.hex[:6]}…)")


def salsa_start(override_time: time | None) -> None:
    """Starts a new day's session, if none is already running."""
    if not is_stopped():
        print("A session is already running. Stop it first.")
        return
    entry_id = uuid4()
    entry = LogEntry(
        entry_id=entry_id,
        event=EntryEvent.START,
        datetime=coalesce_time(override_time),
    )
    append_data(get_today_path(), [entry])
    print(f"Started day: ({entry_id.hex[:6]}…)")


def salsa_pause(override_time: time | None) -> None:
    """Pauses the running session or entry."""
    _transition(
        [EntryEvent.START, EntryEvent.RESUME, TaskEvent.dummy()], EntryEvent.PAUSE, coalesce_time(override_time)
    )


def salsa_stop(override_time: time | None, description: str, deliverables: dict[str, str]) -> None:
    """Stops the running entry, ending the day. The final task and the stop share the same timestamp."""
    when = coalesce_time(override_time)
    event = TaskEvent(description=description, deliverables=deliverables)
    _transition([EntryEvent.START, EntryEvent.RESUME, TaskEvent.dummy()], event, when)
    _transition([TaskEvent.dummy()], EntryEvent.STOP, when)


def salsa_resume(override_time: time | None) -> None:
    """Resumes a paused session."""
    _transition([EntryEvent.PAUSE], EntryEvent.RESUME, coalesce_time(override_time))


def salsa_undo() -> None:
    """Removes today's last log entry. Undoing a stop also undoes its paired final task."""
    path = get_today_path()
    data = load_data(path)
    if not data:
        print("Nothing to undo.")
        return
    undo_count = 2 if data[-1].event == EntryEvent.STOP and len(data) >= 2 else 1
    removed = data[-undo_count:]
    write_data(path, data[:-undo_count])
    labels = ", ".join(f"{r.event.debug()} ({r.entry_id.hex[:6]}…)" for r in removed)
    print(f"Undone: {labels}")


def salsa_task(override_time: time | None, description: str, deliverables: dict[str, str]) -> None:
    """Logs a new task under the running session."""
    event = TaskEvent(description=description, deliverables=deliverables)
    _transition([EntryEvent.START, EntryEvent.RESUME, TaskEvent.dummy()], event, coalesce_time(override_time))
