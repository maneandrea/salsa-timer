import argparse
import json
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator
from uuid import UUID

from salsa.types import EntryEvent, Event, LogEntry, parse_event

BASE_DIR = os.path.expanduser("~/.local/share/salsa")


def get_today_path(override_date: date | None = None) -> Path:
    """Returns today's (or the passed date's) log file path, creating the base directory if needed."""
    today = datetime.now().strftime("%Y-%m-%d") if override_date is None else override_date
    os.makedirs(BASE_DIR, exist_ok=True)
    return Path(BASE_DIR) / f"{today}.jsonl"


def get_all_paths() -> list[Path]:
    """Returns the paths of all log files in the base directory."""
    os.makedirs(BASE_DIR, exist_ok=True)
    names = [f for f in os.listdir(BASE_DIR) if f.endswith(".jsonl")]
    return [Path(BASE_DIR) / name for name in names]


def get_log_iter() -> Iterator[LogEntry]:
    """Iterates over all log entries, most recent day and entry first.

    Files that fail to load are skipped silently.

    Yields:
        LogEntry: entries in reverse chronological order.
    """
    if not os.path.exists(BASE_DIR):
        return
    files = sorted([f for f in os.listdir(BASE_DIR) if f.endswith(".jsonl")], reverse=True)
    for fname in files:
        path = Path(BASE_DIR) / fname
        try:
            data = load_data(path)
        except Exception:
            continue
        yield from reversed(data)


def load_data(path: Path) -> list[LogEntry]:
    """Loads log entries from a JSONL file.

    Args:
        path (Path): path to the JSONL log file.

    Returns:
        list[LogEntry]: parsed entries in file order, or an empty list if
            the file doesn't exist.
    """
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        entries = []
        for line in f.readlines():
            raw = json.loads(line)
            entries.append(
                LogEntry(
                    entry_id=UUID(raw["entry_id"]),
                    datetime=datetime.fromisoformat(raw["datetime"]),
                    event=parse_event(raw["event"]),
                )
            )

        return entries


def get_last_entry(expected_states: list[Event], override_date: date | None = None) -> None | LogEntry:
    """Returns today's last log entry if it matches one of the expected states.

    Args:
        expected_states (list[Event]): events to match against the last entry.
        override_date (date | None): point to a date other than today

    Returns:
        None | LogEntry: the last entry, or None if there isn't one or it
            doesn't match.
    """
    path = get_today_path(override_date)
    data = load_data(path)
    if data and data[-1].event.matches(expected_states):
        return data[-1]
    return None


def get_group(entry_id: UUID) -> list[LogEntry]:
    """Returns all entries sharing entry_id within the day they first appear.

    Args:
        entry_id (UUID): identifier of the entry group to collect.

    Returns:
        list[LogEntry]: entries in the group, in log order.
    """
    entries = []
    group_day = None
    for entry in get_log_iter():
        if group_day and entry.datetime.date() != group_day:
            break
        if entry.entry_id == entry_id:
            group_day = entry.datetime.date()
            entries.append(entry)

    return entries


def is_stopped() -> bool:
    """Returns whether today's last event is STOP (True if there are no entries yet)."""
    path = get_today_path()
    data = load_data(path)
    if data and data[-1].event != EntryEvent.STOP:
        return False
    return True


def _serialize_entries(data: list[LogEntry]) -> list[str]:
    """Serializes log entries to compact JSON lines.

    Args:
        data (list[LogEntry]): entries to serialize.

    Returns:
        list[str]: one JSON string per entry.
    """
    return [
        json.dumps(
            {
                "entry_id": entry.entry_id.hex,
                "event": entry.event.serialize(),
                "datetime": entry.datetime.isoformat(),
            },
            indent=None,
            separators=(",", ":"),
        )
        for entry in data
    ]


def write_data(path: Path, data: list[LogEntry]) -> None:
    """Overwrites path with the serialized entries."""
    with open(path, "w") as f:
        for line in _serialize_entries(data):
            f.write(line + "\n")


def append_data(path: Path, data: list[LogEntry]) -> None:
    """Appends the serialized entries to path."""
    with open(path, "a+") as f:
        for line in _serialize_entries(data):
            f.write(line + "\n")


def format_td(delta: timedelta) -> str:
    """Formats a timedelta as a human-readable duration, e.g. "1 hr 2 min 3 sec".

    Zero-valued larger units (hours, then minutes) are omitted; seconds are
    always shown if nothing else is.

    Args:
        delta (timedelta): duration to format.

    Returns:
        str: human-readable duration.
    """
    total_seconds = int(delta.total_seconds())

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []

    if hours:
        parts.append(f"{hours} hr")
    if minutes:
        parts.append(f"{minutes} min")
    if seconds or not parts:
        parts.append(f"{seconds} sec")

    return " ".join(parts)


def format_td_num(td: timedelta) -> str:
    """Formats a timedelta as HH:MM:SS."""
    total_sec = int(td.total_seconds())
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_td_approx(td: timedelta) -> str:
    """Formats a timedelta as HH:MM:SS rounding to the closest minute."""
    total_sec = int(td.total_seconds())
    hours, remainder = divmod(total_sec, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}"


def valid_time(time_str: str) -> time:
    """Parses a time string in HH:MM format."""
    try:
        return time.strptime(time_str, "%H:%M")
    except ValueError:
        msg = f"Not a valid time: '{time_str}'. Expected HH:MM."
        raise argparse.ArgumentTypeError(msg)


def valid_date(date_str: str) -> date:
    """Parses a date string in YYYY-MM-DD format or words like 'yesterday' or '3 days ago'."""
    if date_str == "yesterday":
        dt = datetime.today() - timedelta(days=1)
        return dt.date()
    elif date_str == "today":
        return datetime.today().date()
    elif m := re.match(r"(\d+) days ago", date_str):
        dt = datetime.today() - timedelta(days=int(m.group(1)))
        return dt.date()
    try:
        return date.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        msg = f"Not a valid date: '{date_str}'. Expected YYYY-MM-DD."
        raise argparse.ArgumentTypeError(msg)


def coalesce_time(override_time: time | None) -> datetime:
    """Returns override_time combined with today's date, or now if override_time is None."""
    now = datetime.now()
    if override_time is None:
        return now
    return datetime.combine(now.date(), override_time)
