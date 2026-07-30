import os
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime, timedelta
from time import sleep
from typing import Literal
from uuid import UUID

from salsa.types import EntryEvent, LogEntry, SessionEntry, SessionTask, TaskEvent
from salsa.utils import (
    format_td,
    format_td_num,
    get_all_paths,
    get_group,
    get_last_entry,
    get_log_iter,
    get_today_path,
)

MAX_DESC_LEN = 50
FENCE = "│"


def _rule(template: str) -> str:
    """Builds a continuous horizontal rule from a column template, crossing at each fence."""
    return "".join("┼" if ch == FENCE else "─" for ch in template)


def _dim_row(*cells: str) -> str:
    """Joins cells into a dim row, keeping the fence separators at full brightness."""
    return "\033[2m" + f" \033[0m{FENCE}\033[2m ".join(cells) + "\033[0m"


def _compute_session(group: list[LogEntry]) -> SessionEntry | None:
    accumulator = timedelta(0)
    task_accumulator = timedelta(0)
    tasks: list[SessionTask] = []
    start = None
    end = None
    entry_id = None
    active_start = None
    active_task_start = None

    for e in sorted(group, key=LogEntry.sort_key):
        if isinstance(e.event, EntryEvent):
            if e.event == EntryEvent.START:
                start = e.datetime
                entry_id = e.entry_id
            elif e.event == EntryEvent.STOP:
                end = e.datetime

            if e.event in (EntryEvent.START, EntryEvent.RESUME):
                active_start = e.datetime
                active_task_start = e.datetime
            else:
                if active_start:
                    accumulator += e.datetime - active_start
                if active_task_start:
                    task_accumulator += e.datetime - active_task_start
                active_start = None
                active_task_start = None
        else:
            if active_task_start:
                task_accumulator += e.datetime - active_task_start
                active_task_start = e.datetime
            else:
                print("error: no active task to save")
                continue
            tasks.append(SessionTask(duration=task_accumulator, end=e.datetime, task=e.event))
            task_accumulator = timedelta(0)

    if active_start:
        accumulator += datetime.now() - active_start
    if active_task_start:
        task_accumulator += datetime.now() - active_task_start
    tasks.append(SessionTask(duration=task_accumulator, end=None, task=TaskEvent(description="", deliverables={})))

    if start and entry_id:
        return SessionEntry(
            entry_id=entry_id,
            start=start,
            end=end,
            active_start=active_start,
            duration=accumulator,
            tasks=tasks,
            current_task_duration=task_accumulator,
        )
    return


def salsa_log(since: str | None = None, detailed: bool = False) -> None:
    """Print log entries since a given date (YYYY-MM-DD). Defaults to today.

    Args:
        since (str | None): Lower bound date string. Accepts ISO date, "today",
            "yesterday", "this week", or "this month".
        detailed (bool): When True, prints individual events below each session row.
    """
    today = date.today()

    if since is None or since == "today":
        since_dt = today
    elif since == "yesterday":
        since_dt = today - timedelta(days=1)
    elif since == "this week":
        since_dt = today - timedelta(days=today.weekday())
    elif since == "this month":
        since_dt = today.replace(day=1)
    else:
        since_dt = date.fromisoformat(since)

    grouped: dict[UUID, list[LogEntry]] = defaultdict(list)
    for e in get_log_iter():
        if e.datetime.date() >= since_dt:
            grouped[e.entry_id].append(e)
        else:
            break

    sessions: list[tuple[SessionEntry, list[LogEntry]]] = []
    for group in grouped.values():
        session = _compute_session(group)
        if session:
            sessions.append((session, sorted(group, key=LogEntry.sort_key)))

    if not sessions:
        print(f"No entries since {since_dt.isoformat()}.")
        return

    ENTRY_W = 7
    TIME_W = len("%Y-%m-%d %H:%M:%S") + len("%H:%M:%S") + 5
    DUR_W = 8
    header = f"{'ENTRY':<{ENTRY_W}} {FENCE} {'TIME':<{TIME_W}} {FENCE} {'DURATION':<{DUR_W}} {FENCE} {'DESCRIPTION':<{MAX_DESC_LEN}}"
    print(header)
    print(_rule(header))
    for sess, events in sessions:
        start = sess.start.strftime("%Y-%m-%d %H:%M:%S")
        end = sess.end.strftime("%H:%M:%S") if sess.end else ("paused… " if sess.paused() else "running…")
        time_str = f"{start} - {end}"
        duration_str = format_td_num(sess.duration)
        task_id_str = f"{sess.entry_id.hex[:6]}…"
        print(f"{task_id_str:<{ENTRY_W}} {FENCE} {time_str:<{TIME_W}} {FENCE} {duration_str:<{DUR_W}} {FENCE}")

        blank_entry = " " * ENTRY_W

        for i, sess_task in enumerate(sess.tasks):
            tree = "└─" if i == len(sess.tasks) - 1 else "├─"
            task_time_str = (
                f"{tree} Task {i + 1:d} ─ {sess_task.end.strftime('%H:%M:%S') if sess_task.end else 'open…'}"
            )
            task_dur_str = format_td_num(sess_task.duration)
            display = sess_task.task.display()
            if len(display) > MAX_DESC_LEN:
                display = display[: MAX_DESC_LEN - 1] + "…"
            print(_dim_row(blank_entry, f"{task_time_str:<{TIME_W}}", f"{task_dur_str:<{DUR_W}}", display))

        if detailed:
            label = " events "
            dashes = TIME_W - len(label) + 2
            left = 3
            time_rule = f"{'─' * left}{label}{'─' * (dashes - left)}"
            print(
                f"\033[2m{blank_entry} \033[0m├\033[2m{time_rule}\033[0m┤"
                f"\033[2m {' ' * DUR_W} \033[0m{FENCE}\033[2m\033[0m"
            )
            for i, ev in enumerate(events):
                tree = "└─" if i == len(events) - 1 else "├─"
                ts = f"{tree} {ev.datetime.strftime('%H:%M:%S')}"
                event_label = ev.event.debug().split(" ")[0]
                print(_dim_row(blank_entry, f"{ts:<{TIME_W}}", f"{'':<{DUR_W}}", event_label))


def _salsa_status(on_active: Callable[[timedelta, str, UUID], None]) -> None:
    last = get_last_entry([EntryEvent.START, EntryEvent.STOP, EntryEvent.PAUSE, EntryEvent.RESUME, TaskEvent.dummy()])
    if not last:
        print("\033[31m● \033[1mstopped\033[0m (last task: none)")
        return

    event = last.event
    task_id = last.entry_id
    group = get_group(task_id)
    session = _compute_session(group)
    description = session.tasks[-1].task.description if session and session.tasks else "none"
    accumulated_td = session.duration if session else timedelta(0)
    match event:
        case EntryEvent.START | EntryEvent.RESUME | TaskEvent():
            duration = format_td(accumulated_td)
            task_label = f"{description} " if description else ""
            print(f"\033[32m● \033[1mrunning\033[0m {task_label}({task_id.hex[:6]}…) | {duration}", end="", flush=True)
            try:
                on_active(accumulated_td, description, task_id)
            except KeyboardInterrupt:
                print("")
                return
        case EntryEvent.PAUSE:
            accumulated = format_td(accumulated_td)
            print(f"\033[33m● \033[1mpaused\033[0m {description} ({task_id.hex[:6]}…) | {accumulated}")
        case _:
            print(f"\033[31m● \033[1mstopped\033[0m (last task: {description})")


def salsa_status() -> None:
    _salsa_status(lambda _, __, ___: print(""))


def salsa_show() -> None:

    def _go(acc_duration: timedelta, description: str, task_id: UUID) -> None:
        reference = datetime.now()
        task_label = f"{description} " if description else ""
        while True:
            sleep(1)
            duration_td = acc_duration + (datetime.now() - reference)
            duration = format_td(duration_td)
            print(
                f"\r\033[32m● \033[1mrunning\033[0m {task_label}({task_id.hex[:6]}…) | {duration}", end="", flush=True
            )

    _salsa_status(_go)


def salsa_clear(scope: Literal["all", "today"]):
    if scope == "all":
        confirm = input("This will delete ALL log entries. Type 'yes' to confirm: ")

        if confirm.strip().lower() != "yes":
            print("Aborted.")
            return

        for path in get_all_paths():
            os.remove(path)

    else:  # scope == "today"
        os.remove(get_today_path())


def salsa_today() -> None:
    """Prints a description of every task done today, along with its duration."""
    last = get_last_entry([EntryEvent.START, EntryEvent.STOP, EntryEvent.PAUSE, EntryEvent.RESUME, TaskEvent.dummy()])
    if not last:
        print("No entries today.")
        return

    group = get_group(last.entry_id)
    session = _compute_session(group)
    if not session:
        return

    sentences = []
    n_tasks = len(session.tasks)
    plural = "s" if n_tasks > 1 else ""
    finished_tasks = [t.duration for t in session.tasks if t.end]
    total_line = f"Completed {n_tasks} task{plural}. Total: {format_td(sum(finished_tasks, timedelta(0)))}"
    print(total_line)
    print("—" * len(total_line))
    for sess_task in session.tasks:
        if sess_task.end is None:
            continue
        duration = format_td_num(sess_task.duration)
        print(f" * {duration} — {sess_task.task.display()}")
        sentences.append(sess_task.task.description.strip(" .") + ".")
    print("—" * len(total_line))
    print(" ".join(sentences))
