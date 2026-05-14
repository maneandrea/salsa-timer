import argparse
import json
import os
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterator
from uuid import UUID

from salsa.types import Event, LogEntry

BASE_DIR = os.path.expanduser("~/.local/share/salsa")


def get_today_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(BASE_DIR, exist_ok=True)
    return Path(BASE_DIR) / f"{today}.jsonl"


def get_all_paths() -> list[Path]:
    os.makedirs(BASE_DIR, exist_ok=True)
    names = [f for f in os.listdir(BASE_DIR) if f.endswith(".jsonl")]
    return [Path(BASE_DIR) / name for name in names]


def get_log_iter() -> Iterator[LogEntry]:
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
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        entries = []
        for line in f.readlines():
            raw = json.loads(line)
            entries.append(
                LogEntry(
                    task_id=UUID(raw["task_id"]),
                    description=raw["description"],
                    datetime=datetime.fromisoformat(raw["datetime"]),
                    event=Event(raw["event"]),
                )
            )

        return entries


def get_last_entry(expected_states: list[Event]) -> None | LogEntry:
    path = get_today_path()
    data = load_data(path)
    if data and data[-1]["event"] in expected_states:
        return data[-1]
    return None


def get_group(task_id: UUID) -> list[LogEntry]:
    entries = []
    group_day = None
    for entry in get_log_iter():
        if group_day and entry["datetime"].date() != group_day:
            break
        if entry["task_id"] == task_id:
            group_day = entry["datetime"].date()
            entries.append(entry)

    return entries


def is_stopped() -> bool:
    path = get_today_path()
    data = load_data(path)
    if data and data[-1]["event"] != Event.STOP:
        return False
    return True


def append_data(path: Path, data: list[LogEntry]) -> None:
    with open(path, "a+") as f:
        # Convert datetime objects to isoformat for JSON serialization
        lines = [
            json.dumps(
                {
                    "task_id": entry["task_id"].hex,
                    "event": entry["event"].value,
                    "datetime": entry["datetime"].isoformat(),
                    "description": entry["description"],
                },
                indent=None,
                separators=(",", ":"),
            )
            for entry in data
        ]
        for line in lines:
            f.write(line + "\n")


def format_td(delta: timedelta) -> str:
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


def format_td_num(td):
    total_sec = int(td.total_seconds())
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def valid_time(time_str):
    """Parses a time string in HH:MM format."""
    try:
        return time.strptime(time_str, "%H:%M")
    except ValueError:
        msg = f"Not a valid time: '{time_str}'. Expected HH:MM."
        raise argparse.ArgumentTypeError(msg)


def coalesce_time(override_time: time | None) -> datetime:
    now = datetime.now()
    if override_time is None:
        return now
    return datetime.combine(now.date(), override_time)
