from datetime import datetime
from typing import Literal, TypedDict


class LogEntry(TypedDict):
    event: Literal["start", "end"]
    datetime: datetime
    description: str
