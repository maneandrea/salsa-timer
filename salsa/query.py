import os
from collections import defaultdict
from collections.abc import Callable
from copy import copy
from datetime import date, datetime, timedelta
from math import ceil, floor
from time import sleep
from typing import Literal
from uuid import UUID

import plotext as plt
import pyperclip

from salsa.types import EntryEvent, LogEntry, SessionEntry, SessionTask, TaskEvent
from salsa.utils import (
    format_td,
    format_td_approx,
    format_td_num,
    get_all_paths,
    get_group,
    get_last_entry,
    get_log_iter,
    get_log_iter_range,
    get_today_path,
)

MAX_DESC_LEN = 50
FENCE = "│"
CROSS_FENCE = "┼"
DASH = "─"


def _rule(template: str) -> str:
    """Builds a continuous horizontal rule from a column template, crossing at each fence."""
    return "".join(CROSS_FENCE if ch == FENCE else DASH for ch in template)


def _dim_row(*cells: str) -> str:
    """Joins cells into a dim row, keeping the fence separators at full brightness."""
    return "\033[2m" + f" \033[0m{FENCE}\033[2m ".join(cells) + "\033[0m"


def _weekday(weekday: int) -> str:
    """Formats a weekday"""
    return {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}[weekday]


def _duration_color(duration: timedelta) -> tuple[str, str]:
    """Colors in green entries over 9 hours and in red entries below 7 hours"""
    hours = duration.total_seconds() / 3600
    if hours >= 9:
        return "\033[32m", "\033[0m"
    elif hours <= 7:
        return "\033[31m", "\033[0m"
    else:
        return "", ""


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
    if end is None:
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


def salsa_log(since: date | None = None, of: tuple[date, int] | None = None, detailed: bool = False) -> None:
    """Print log entries since a given date (YYYY-MM-DD). Defaults to today.

    Args:
        since (date | None): Lower bound date.
        of (date | None): Exact date to show. Mutually exclusive with since.
        detailed (bool): When True, prints individual events below each session row.
    """

    start = date.today()
    duration = 1
    is_since = False
    if since is not None and of is None:
        start = since
        is_since = True
    elif since is None and of is not None:
        (start, duration) = of
    elif since is not None and of is not None:
        raise ValueError("since and of are mutually exclusive")

    grouped: dict[UUID, list[LogEntry]] = defaultdict(list)
    if is_since:
        for e in get_log_iter():
            if e.datetime.date() >= start:
                grouped[e.entry_id].append(e)
            else:
                break
    else:
        entries = get_log_iter_range(start, duration)
        if entries is not None:
            for entry in entries:
                grouped[entry.entry_id].append(entry)

    sessions: list[tuple[SessionEntry, list[LogEntry]]] = []
    for group in grouped.values():
        session = _compute_session(group)
        if session:
            sessions.append((session, sorted(group, key=LogEntry.sort_key)))

    if not sessions:
        if since is not None:
            print(f"No entries since {start.isoformat()}.")
        else:
            print(f"No entries at {start.isoformat()}.")
        return

    ENTRY_W = 7
    TIME_W = len("%Y-%m-%d %H:%M:%S") + len("%H:%M:%S") + 5
    DUR_W = 8
    header = f"{'ENTRY':<{ENTRY_W}} {FENCE} {'TIME':<{TIME_W}} {FENCE} {'DURATION':<{DUR_W}} {FENCE} {'DESCRIPTION':<{MAX_DESC_LEN}}"
    print(header)
    print(_rule(header))
    current_weekday = None
    for sess, events in sessions:
        line_weekday = sess.start.weekday()
        start = sess.start.strftime("%Y-%m-%d %H:%M:%S")
        end = sess.end.strftime("%H:%M:%S") if sess.end else ("paused… " if sess.paused() else "running…")
        time_str = f"{start} - {end}"
        duration_str = format_td_num(sess.duration)
        dur_col_s, dur_col_e = _duration_color(sess.duration)
        task_id_str = f"{sess.entry_id.hex[:6]}…"
        if current_weekday != line_weekday:
            current_weekday = line_weekday
            first_column = f"\033[1m{_weekday(current_weekday):>{ENTRY_W}}\033[0m"
            task_id_pending = True
        else:
            first_column = f"\033[2m{task_id_str:<{ENTRY_W}}\033[0m"
            task_id_pending = False
        print(
            f"{first_column} {FENCE} {time_str:<{TIME_W}} {FENCE} {dur_col_s}{duration_str:<{DUR_W}}{dur_col_e} {FENCE}"
        )

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
            if task_id_pending:
                first_task_column = f"{task_id_str:<{ENTRY_W}}"
                task_id_pending = False
            else:
                first_task_column = blank_entry
            print(_dim_row(first_task_column, f"{task_time_str:<{TIME_W}}", f"{task_dur_str:<{DUR_W}}", display))

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


def _salsa_status(on_active: Callable[[timedelta, timedelta, UUID], None]) -> None:
    last = get_last_entry([EntryEvent.START, EntryEvent.STOP, EntryEvent.PAUSE, EntryEvent.RESUME, TaskEvent.dummy()])
    if not last:
        print("\033[31m● \033[1mstopped\033[0m (last task: none)")
        return

    event = last.event
    entry_id = last.entry_id
    group = get_group(entry_id)
    session = _compute_session(group)
    description = session.tasks[-1].task.description if session and session.tasks else "none"
    accumulated_td = session.duration if session else timedelta(0)
    task_td = session.tasks[-1].duration if session and session.tasks else timedelta(0)
    match event:
        case EntryEvent.START | EntryEvent.RESUME | TaskEvent():
            duration = format_td(accumulated_td)
            task_duration = format_td(task_td)
            print(
                f"\033[32m● \033[1mrunning\033[0m ({entry_id.hex[:6]}…) {FENCE} \033[1mTotal\033[0m: {duration:<20} "
                f"{FENCE} \033[1mLast task\033[0m: {task_duration:<20}",
                end="",
                flush=True,
            )
            try:
                on_active(accumulated_td, task_td, entry_id)
            except KeyboardInterrupt:
                print("")
                return
        case EntryEvent.PAUSE:
            duration = format_td(accumulated_td)
            task_duration = format_td(task_td)
            print(
                f"\033[33m● \033[1mpaused \033[0m ({entry_id.hex[:6]}…) {FENCE} \033[1mTotal\033[0m: {duration:<20} "
                f"{FENCE} \033[1mLast task\033[0m: {task_duration:<20}"
            )
        case _:
            print(f"\033[31m● \033[1mstopped\033[0m (last task: {description})")


def salsa_status() -> None:
    _salsa_status(lambda _, __, ___: print(""))


def salsa_show() -> None:

    def _go(acc_duration: timedelta, task_duration: timedelta, entry_id: UUID) -> None:
        reference = datetime.now()
        while True:
            sleep(1)
            duration_td = acc_duration + (datetime.now() - reference)
            task_duration_td = task_duration + (datetime.now() - reference)
            duration = format_td(duration_td)
            task_duration_f = format_td(task_duration_td)
            print(
                f"\r\033[32m● \033[1mrunning\033[0m ({entry_id.hex[:6]}…) {FENCE} \033[1mTotal\033[0m: {duration:<20} "
                f"{FENCE} \033[1mLast task\033[0m: {task_duration_f:<20}",
                end="",
                flush=True,
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


def salsa_today(override_date: date | None) -> None:
    """Prints a description of every task done today, along with its duration."""
    last = get_last_entry(
        [EntryEvent.START, EntryEvent.STOP, EntryEvent.PAUSE, EntryEvent.RESUME, TaskEvent.dummy()], override_date
    )
    if not last:
        if override_date is not None:
            print(f"No entries on {override_date.strftime('%Y-%m-%d')}")
        else:
            print("No entries today.")
        return

    group = get_group(last.entry_id)
    session = _compute_session(group)
    if not session:
        return

    sentences = []
    rows = []
    n_tasks = len([t for t in session.tasks if t.end is not None])
    plural = "s" if n_tasks > 1 else ""
    finished_tasks = [t.duration for t in session.tasks if t.end]
    total_line = f"Completed {n_tasks} task{plural}. Total: {format_td(sum(finished_tasks, timedelta(0)))}"
    print(total_line)
    print("—" * len(total_line))
    for sess_task in session.tasks:
        if sess_task.end is None:
            continue
        duration = format_td_approx(sess_task.duration)
        deliverable_str = ", ".join([f"{k}: {v}" for k, v in sess_task.task.deliverables.items()])
        rows.append((sess_task.task.description, datetime.today().strftime("%d/%m/%Y"), duration, deliverable_str))
        sentences.append(sess_task.task.description.strip(" .") + ".")
    print(" ".join(sentences))
    print("—" * len(total_line))
    pyperclip.copy("\n".join(["\t".join(cols) for cols in rows]))
    print("Content copied to clipboard ✓")


def salsa_last() -> None:
    """Prints the latest completed task"""
    last = get_last_entry([EntryEvent.START, EntryEvent.STOP, EntryEvent.PAUSE, EntryEvent.RESUME, TaskEvent.dummy()])
    if not last:
        print("No entries today.")
        return

    group = get_group(last.entry_id)
    session = _compute_session(group)
    finished_tasks = [t for t in session.tasks if t.end] if session is not None else []
    if not finished_tasks:
        print("No finished tasks today.")
        return
    last_task = max(finished_tasks, key=lambda t: t.end.timestamp() if t.end else 0)
    print(f"\033[1mDuration     {FENCE}\033[0m", format_td(last_task.duration))
    print(f"\033[1mDescription  {FENCE}\033[0m", last_task.task.description)
    print(
        f"\033[1mDeliverables {FENCE}\033[0m", ", ".join([f"{k}: {d}" for k, d in last_task.task.deliverables.items()])
    )


def salsa_stats(of: tuple[date, int], until: date | None = None) -> None:
    """Prints hours worked in a period against the targeted hours, and the gap between them.

    The target is 8 hours for every Monday through Friday in the period.

    Args:
        of (tuple[date, int]): start date and length in days of the period.
    """
    start, duration = of
    if until and until > start:
        duration = (until - start).days + 1

    grouped: dict[UUID, list[LogEntry]] = defaultdict(list)
    for entry in get_log_iter_range(start, duration):
        grouped[entry.entry_id].append(entry)

    work_dict: dict[date, timedelta] = {}
    workdays = 0
    past = 0
    futures = 0
    today = datetime.today().date()
    for d in range(duration):
        current = start + timedelta(days=d)
        if current.weekday() < 5:
            workdays += 1
            if current >= today:
                futures += 1
            else:
                work_dict[current] = timedelta(0)
                past += 1

    worked = timedelta(0)
    worked_not_today = timedelta(0)
    for group in grouped.values():
        session = _compute_session(group)
        if session:
            worked += session.duration
            if session.start.date() < datetime.today().date():
                work_dict[session.start.date()] += session.duration
                worked_not_today += session.duration

    target = timedelta(hours=8 * workdays)
    diff = worked - target
    diff_not_today = worked_not_today - target

    end = start + timedelta(days=duration - 1)
    period_line = "Period  "
    rest_line = f" {start.isoformat()} — {end.isoformat()}"
    print(f"\033[1m{period_line}\033[0m{FENCE}{rest_line}")
    print(DASH * len(period_line) + CROSS_FENCE + DASH * len(rest_line))
    print(f"\033[1mWorked  {FENCE}\033[0m", format_td(worked))
    print(f"\033[1mTarget  {FENCE}\033[0m", format_td(target))
    if diff < timedelta(0):
        print(f"\033[1mMissing {FENCE}\033[0m \033[1;31m{format_td(-diff)}\033[0m")
    else:
        print(f"\033[1mExtra   {FENCE}\033[0m \033[1;32m{format_td(diff)}\033[0m")
    if past > 0:
        print(f"\033[1mAverage {FENCE}\033[0m {worked.total_seconds() / past / 3600:.3f} hours / day")

    if futures > 0 and diff_not_today < timedelta(0):
        print(f"\033[1mAim to  {FENCE}\033[0m {-diff_not_today.total_seconds() / futures / 3600:.3f} hours / day")

    print(DASH * len(period_line) + DASH + DASH * len(rest_line))
    cumulative: dict[date, timedelta] = {}
    accumulator = timedelta(hours=8)
    for day, dur in work_dict.items():
        accumulator += dur - timedelta(hours=8)
        cumulative[day] = copy(accumulator)

    _plot_work(work_dict, cumulative)


def _plot_work(work_dict: dict[date, timedelta], cumulative: dict[date, timedelta]) -> None:
    """Plots daily worked hours as bars and the cumulative balance against the 8 hour target as a line.

    Bars reaching the 8 hour target are green, the ones below it are red.

    Args:
        work_dict (dict[date, timedelta]): Hours worked per day.
        cumulative (dict[date, timedelta]): Running balance against the target at each day.
    """
    days = sorted(work_dict)
    if not days:
        return

    positions = list(range(1, len(days) + 1))
    labels = [f"{_weekday(day.weekday())} {day.day:02d}" for day in days]
    hours = [work_dict[day].total_seconds() / 3600 for day in days]
    balances = [cumulative[day].total_seconds() / 3600 for day in days]

    green = plt.marker("full", plt.pixel(foreground="green"))
    red = plt.marker("full", plt.pixel(foreground="red"))
    bar_markers = [green if h >= 7.9 else red for h in hours]

    fig = plt.figure
    fig.clear()
    fig.theme("simple")
    fig.plot_size(height=20)
    fig.title("Hours per day (bars) · Cumulative balance vs 8h (line)")
    fig.draw(fig.bar(positions, hours, marker=bar_markers, width=0.6))
    fig.ruler("x").ticks(positions, labels)
    y_upper = max(8.0, *hours, *balances)
    fig.ruler("y").lim(0, y_upper)
    fig.ruler("y").ticks(_hour_ticks(y_upper))
    bars_only = fig.build().copy()

    balance_line = fig.signal(positions, balances, marker=plt.marker("braille", plt.pixel(foreground="blue")))
    balance_line.lines()
    fig.draw(balance_line)
    combined = fig.build()
    _paint_under_line(bars_only, combined, line_color="blue", bar_colors=["green", "red"])
    combined.print()


def _paint_under_line(bars_only: plt.matrix, combined: plt.matrix, line_color: str, bar_colors: list[str]) -> None:
    """Gives the line cells drawn over a bar the bar color as background, so the line doesn't cut holes in the bars.

    plotext replaces the whole cell pixel when a marker lands on it, so the bar color is recovered from a render
    of the same figure without the line.

    Args:
        bars_only (plt.matrix): Rendered figure with the bars only.
        combined (plt.matrix): Rendered figure with bars and line, same size as `bars_only`. Modified in place.
        line_color (str): Color name of the line.
        bar_colors (list[str]): Color names of the bars.
    """
    # Pixels read back as RGB: map them to the names so repainted cells keep the terminal palette shades
    bar_color_map = {plt.pixel(foreground=name).foreground(): name for name in bar_colors}
    for row in range(combined.height()):
        for col in range(combined.width()):
            bar_color = bar_color_map.get(bars_only.get(row, col).foreground())
            if bar_color is None or combined.get(row, col).foreground() == bars_only.get(row, col).foreground():
                continue
            combined._set_pixel(col, row, plt.pixel(foreground=line_color, background=bar_color))


def _hour_ticks(upper: float) -> list[float]:
    """Builds evenly spaced hour ticks from 0 up to `upper`, always including the 8 hour target and
    with higher density around 8.

    The step is always a divisor or a multiple of 8, so the target falls on the regular grid.

    Args:
        upper (float): Upper limit of the axis.

    Returns:
        list[float]: Tick positions.
    """
    if upper <= 12:
        step = 4
    elif upper <= 24:
        step = 8
    else:
        step = 8 * ceil(upper / 40)
    return list({float(t) for t in range(0, floor(upper) + 1, step)} | {7.0, 8.0, 9.0, upper})
