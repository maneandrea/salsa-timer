"""Core data types shared across salsa: log events, log entries, and session summaries."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import NotRequired, Self, TypedDict
from uuid import UUID

type Event = TaskEvent | EntryEvent
# Plain (de)serialized shape of a TaskEvent, used where a TypedDict is preferred over a functional alias.
TaskEventDict = TypedDict("TaskEventDict", {"description": str, "deliverables": dict[str, str]})


class EventSerialized(TypedDict):
    """Wire format for an `Event`, discriminated by the `__event__` key.

    Attributes:
        __event__ (str): Discriminant identifying the event kind (e.g. "TASK", "START").
        description (NotRequired[str]): Task description, present only for TASK events.
        deliverables (NotRequired[dict[str, str]]): Task deliverables, present only for TASK events.
    """

    __event__: str
    description: NotRequired[str]
    deliverables: NotRequired[dict[str, str]]


class EntryEvent(Enum):
    """A timekeeping event marking a transition in a work session's lifecycle."""

    START = "START"
    STOP = "STOP"
    PAUSE = "PAUSE"
    RESUME = "RESUME"

    def debug(self) -> str:
        """Return a human-readable label for debugging/logging purposes."""
        return f"{self.value} event"

    def verb(self) -> str:
        """Return the lowercase verb form of the event (e.g. "start")."""
        return self.value.lower()

    def past_verb(self) -> str:
        """Return the past-tense, capitalized verb form of the event (e.g. "Started")."""
        past_verbs = {
            EntryEvent.START: "Started",
            EntryEvent.STOP: "Stopped",
            EntryEvent.PAUSE: "Paused",
            EntryEvent.RESUME: "Resumed",
        }
        return past_verbs[self]

    def serialize(self) -> EventSerialized:
        """Serialize this event to its wire format."""
        return {"__event__": self.value}

    def matches(self, events: list[Event]) -> bool:
        """Check whether this exact event is present among a list of events."""
        return any(isinstance(e, EntryEvent) and e == self for e in events)


@dataclass
class TaskEvent:
    """An event recording that a task with deliverables was registered during a session.

    Attributes:
        description (str): Free-text description of the task.
        deliverables (dict[str, str]): Mapping of deliverable name to its value/description.
    """

    description: str
    deliverables: dict[str, str]

    @classmethod
    def dummy(cls) -> Self:
        """Build an empty placeholder `TaskEvent`."""
        return cls("", {})

    def debug(self) -> str:
        """Return a human-readable label for debugging/logging purposes."""
        return "TASK event"

    def display(self) -> str:
        """Render this task event for display to the user."""
        if self.deliverables:
            deliverables_str = [f"{key}: {val}" for key, val in self.deliverables.items()]
            return f"{self.description} [deliverables => {', '.join(deliverables_str)}]"
        else:
            return self.description

    def verb(self) -> str:
        """Return the present-tense verb phrase describing this event."""
        return "register tasks for"

    def past_verb(self) -> str:
        """Return the past-tense verb phrase describing this event."""
        return "Registered task"

    def serialize(self) -> EventSerialized:
        """Serialize this event to its wire format."""
        return {"__event__": "TASK", "description": self.description, "deliverables": self.deliverables}

    def matches(self, events: list[Event]) -> bool:
        """Check whether a `TaskEvent` is present among a list of events."""
        return any(isinstance(e, TaskEvent) for e in events)


def parse_event(raw: EventSerialized) -> Event:
    """Deserialize a wire-format event back into an `Event`.

    Args:
        raw (EventSerialized): Serialized event, discriminated by its `__event__` key.

    Returns:
        Event: A `TaskEvent` when the discriminant is "TASK", otherwise the matching `EntryEvent`.

    Raises:
        ValueError: If the discriminant is not "TASK" and does not match any `EntryEvent` value.
    """
    discriminant = raw["__event__"]
    if discriminant == "TASK":
        desc = raw.get("description", "<missing description>")
        deli = raw.get("deliverables", {})
        return TaskEvent(description=desc, deliverables=deli)
    else:
        return EntryEvent(discriminant)


@dataclass
class LogEntry:
    """A single timestamped occurrence of an `Event` in the log.

    Attributes:
        entry_id (UUID): Unique identifier of this log entry.
        event (Event): The event that occurred.
        datetime (datetime): When the event occurred.
    """

    entry_id: UUID
    event: Event
    datetime: datetime

    def display(self) -> str:
        """Render this log entry for display to the user, blank for `EntryEvent`s."""
        if isinstance(self.event, EntryEvent):
            return ""
        else:
            return self.event.display()

    def sort_key(self) -> tuple[datetime, int]:
        if self.event == EntryEvent.STOP:
            weight = 2
        elif self.event == EntryEvent.PAUSE:
            weight = 1
        else:
            weight = 0

        return (self.datetime, weight)


@dataclass
class SessionTask:
    duration: timedelta
    end: datetime | None
    task: TaskEvent


@dataclass
class SessionEntry:
    """A summary of a work session, aggregated from its underlying log entries.

    Attributes:
        entry_id (UUID): Unique identifier of the session's starting log entry.
        start (datetime): When the session started.
        end (datetime | None): When the session ended, or `None` if still ongoing.
        active_start (datetime | None): When the current active (non-paused) period began,
            or `None` if the session is currently paused.
        duration (timedelta): Total accumulated active duration of the session.
        tasks (list[SessionTask]): Registered tasks paired with the elapsed
            duration and end time at which each was registered.
        current_task_duration (timedelta): Time elapsed since the last registered task.
    """

    entry_id: UUID
    start: datetime
    end: datetime | None
    active_start: datetime | None
    duration: timedelta
    tasks: list[SessionTask]
    current_task_duration: timedelta

    def paused(self) -> bool:
        """Check whether the session is currently paused."""
        return self.active_start is None
