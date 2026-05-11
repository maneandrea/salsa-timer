import os
from datetime import date, datetime, timedelta
from typing import Literal

from salsa.utils import format_td, get_all_paths, get_log_iter, get_today_path

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

    entries = []
    for e in get_log_iter():
        if e["datetime"].date() >= since_dt:
            entries.append(e)
        else:
            break
    sessions = []
    current = None
    for entry in reversed(entries):
        if entry["event"] == "start":
            if current is None:
                current = {
                    "start": entry["datetime"],
                    "description": entry["description"],
                }
            else:
                # orphan start, treat as instant session
                sessions.append(
                    {
                        "start": entry["datetime"],
                        "end": entry["datetime"],
                        "description": entry["description"],
                    }
                )
                current = None
        elif entry["event"] == "end":
            if current is not None:
                current["end"] = entry["datetime"]
                sessions.append(current)
                current = None
            else:
                # orphan end, ignore
                pass
    if current is not None:
        # running session
        current["end"] = None
        sessions.append(current)
    if not sessions:
        print(f"No entries since {since_dt.isoformat()}.")
        return
    for sess in sessions:
        start = sess["start"].strftime("%Y-%m-%d %H:%M:%S")
        end = sess["end"].strftime("%H:%M:%S") if sess["end"] else "running…"
        if sess["end"]:
            duration = str(sess["end"] - sess["start"]).split(".")[0]
        else:
            duration = str(datetime.now() - sess["start"]).split(".")[0]
        desc = sess["description"]
        if len(desc) > MAX_DESC_LEN:
            desc = desc[: MAX_DESC_LEN - 1] + "…"

        print(f"{start} - {end} | {duration} | {desc}")


def salsa_status() -> None:
    active = None
    last_desc = "none"
    duration_td = timedelta(0)
    for entry in get_log_iter():
        if entry["event"] == "start":
            active = entry
            last_desc = entry["description"]
            duration_td = datetime.now() - entry["datetime"]
            break
        elif entry["event"] == "end":
            last_desc = entry["description"]
            break
    if active:
        duration = format_td(duration_td)
        print(f"\033[32m● \033[1mactive\033[0m {active['description']} ({duration})")
    else:
        print(f"\033[31m● \033[1midle\033[0m (last task: {last_desc})")


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
