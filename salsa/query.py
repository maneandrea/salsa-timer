import os
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime, timedelta
from time import sleep
from typing import Literal
from uuid import UUID

from salsa.types import Event, LogEntry, SessionEntry
from salsa.utils import (
    format_td,
    format_td_num,
    get_all_paths,
    get_last_entry,
    get_log_iter,
    get_today_path,
)

MAX_DESC_LEN = 50


def get_most_recent_description() -> str | None:
    for entry in get_log_iter():
        if entry["description"]:
            return entry["description"]
    return


def salsa_log(since: str | None = None) -> None:
    """Print log entries since a given date (YYYY-MM-DD). Defaults to today."""
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
        if e["datetime"].date() >= since_dt:
            grouped[e["task_id"]].append(e)
        else:
            break

    sessions: list[SessionEntry] = []
    for group in grouped.values():
        current = None
        accumulator = timedelta(0)
        start = None
        end = None
        task_id = None
        description = None
        paused = True
        for e in sorted(group, key=lambda x: x["datetime"]):
            if e["event"] == Event.START:
                start = e["datetime"]
                task_id = e["task_id"]
                description = e["description"]
            elif e["event"] == Event.STOP:
                end = e["datetime"]

            if e["event"] in (Event.START, Event.RESUME):
                current = e["datetime"]
                paused = False
            elif current:
                accumulator += e["datetime"] - current
                current = None
                paused = True
            else:
                continue
        if start and task_id and description:
            sessions.append(
                SessionEntry(
                    start=start,
                    end=end,
                    task_id=task_id,
                    duration=accumulator,
                    description=description,
                    paused=paused,
                    current=current,
                )
            )

    if not sessions:
        print(f"No entries since {since_dt.isoformat()}.")
        return

    TASK_W = 7
    TIME_W = len("%Y-%m-%d %H:%M:%S") + len("%H:%M:%S") + 5
    DUR_W = 8
    print(f"{'TASK':<{TASK_W}} | {'TIME':<{TIME_W}} | {'DURATION':<{DUR_W}} | {'DESCRIPTION':<{MAX_DESC_LEN}}")
    print(f"{'-' * TASK_W} + {'-' * TIME_W} + {'-' * DUR_W} + {'-' * MAX_DESC_LEN}")
    for sess in sessions:
        start = sess["start"].strftime("%Y-%m-%d %H:%M:%S")
        end = sess["end"].strftime("%H:%M:%S") if sess["end"] else ("paused… " if sess["paused"] else "running…")
        if sess["end"] or sess["paused"]:
            duration = sess["duration"]
        elif sess["current"]:
            duration = sess["duration"] + datetime.now() - sess["current"]
        else:
            duration = datetime.now() - sess["start"]
        desc = sess["description"]
        if len(desc) > MAX_DESC_LEN:
            desc = desc[: MAX_DESC_LEN - 1] + "…"

        duration_str = format_td_num(duration)
        task_id_str = f"{sess['task_id'].hex[:6]}…"
        print(f"{task_id_str} | {start} - {end} | {duration_str} | {desc}")


def _salsa_status(on_active: Callable[[LogEntry], None]) -> None:
    last = get_last_entry([Event.START, Event.STOP, Event.PAUSE, Event.RESUME])
    if not last:
        print("\033[31m● \033[1mstopped\033[0m (last task: none)")
        return

    event = last["event"]
    duration_td = datetime.now() - last["datetime"]
    task_id = last["task_id"]
    description = last["description"]
    match event:
        case Event.START | Event.RESUME:
            duration = format_td(duration_td)
            print(
                f"\033[32m● \033[1mrunning\033[0m {description} ({task_id.hex[:6]}…) | {duration}", end="", flush=True
            )
            try:
                on_active(last)
            except KeyboardInterrupt:
                print("")
                return
        case Event.PAUSE:
            duration = format_td(duration_td)
            print(f"\033[33m● \033[1mpaused\033[0m {description} ({task_id.hex[:6]}…)")
        case _:
            print(f"\033[31m● \033[1mstopped\033[0m (last task: {description})")


def salsa_status() -> None:
    _salsa_status(lambda _: print(""))


def salsa_show() -> None:

    def _go(entry):

        task_id = entry["task_id"]
        description = entry["description"]
        while True:
            sleep(1)
            duration_td = datetime.now() - entry["datetime"]
            duration = format_td(duration_td)
            print(
                f"\r\033[32m● \033[1mrunning\033[0m {description} ({task_id.hex[:6]}…) | {duration}", end="", flush=True
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
