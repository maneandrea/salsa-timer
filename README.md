Salsa
-----

Simple CLI to annotate timesheets. It works by annotating datetimes and logging them in a `.jsonl` file under `~/.local/share/salsa`. As simple as that. Features will be added as needed. Have fun!

## Usage

Start your day
```bash
$ salsa start
Started day: (30f16b…)
```
register a task as you complete it, optionally attaching deliverables as evidence
```bash
$ salsa task "Wrote the onboarding doc" --deliverable pr salsa#7
Registered task: Wrote the onboarding doc [deliverables: pr] (30f16b…)
```
check the current status
```bash
$ salsa status
● running (30f16b…) | 2 hr 54 min 24 sec
```
stop when you are done for the day; `stop` takes a description too, since it registers one last task before ending the session
```bash
$ salsa stop "My new task"
Registered task: My new task (30f16b…)
Stopped: (30f16b…)
```
and browse old logs
```bash
$ salsa log --since "yesterday"  # defaults to "today"
ENTRY   │ TIME                           │ DURATION │ DESCRIPTION
────────┼────────────────────────────────┼──────────┼───────────────────────────────────────────────────
30f16b… │ 2026-07-30 13:18:02 - 14:02:10 │ 00:44:08 │
        │ ├─ Task 1 ─ 13:45:00           │ 00:26:58 │ Wrote the onboarding doc [deliverables: pr]
        │ └─ Task 2 ─ 14:02:10           │ 00:17:10 │ My new task
```
pass `--detailed` to also see the raw events (start/pause/resume/task/stop) behind each session