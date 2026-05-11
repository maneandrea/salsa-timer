import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from salsa.types import LogEntry

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
    files = sorted(
        [f for f in os.listdir(BASE_DIR) if f.endswith(".jsonl")], reverse=True
    )
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
                    description=raw["description"],
                    datetime=datetime.fromisoformat(raw["datetime"]),
                    event=raw["event"],
                )
            )

        return entries


def append_data(path: Path, data: list[LogEntry]) -> None:
    with open(path, "a+") as f:
        # Convert datetime objects to isoformat for JSON serialization
        lines = [
            json.dumps(
                {
                    "event": entry["event"],
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
