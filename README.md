Salsa
-----

Simple CLI to annotate timesheets. It works by annotating datetimes and logging them in a `.jsonl` file in the user's `$HOME`. As simple as that. Features will be added as needed. Have fun!

## Usage

Start a task
```bash
$ salsa start "My new task"
Started: My new task
```
check the current status
```bash
$ salsa status
● active My new task (1 min 23 sec)
```
stop it when you are done
```bash
$ salsa stop
Stopped: My new task
```
and browse old logs
```bash
$ salsa log --since "yesterday"  # defaults to "today"
2026-05-11 13:18:02 - 13:19:35 | 0:01:33 | My new task
```