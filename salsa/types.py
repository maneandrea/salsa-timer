from datetime import datetime, timedelta
from enum import Enum
from typing import TypedDict
from uuid import UUID


class Event(Enum):
    START = "START"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class LogEntry(TypedDict):
    task_id: UUID
    event: Event
    datetime: datetime
    description: str


class SessionEntry(TypedDict):
    start: datetime
    end: datetime | None
    description: str
    duration: timedelta
    task_id: UUID
    paused: bool
    current: datetime | None
