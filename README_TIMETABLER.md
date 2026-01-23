
# Timetabler (Python) — Minimal aSc-like Core

This folder contains a minimal, **run-ready** school timetabling tool implemented in pure Python (no external solvers). It supports:

- Classes, teachers, rooms, subjects
- Weekly timeslots (e.g., 5 days × 6 periods)
- Curriculum with required periods per week
- Teacher unavailability
- Room capacity checks and fixed-room assignments
- Automatic schedule generation (backtracking + MRV)
- Exports per-class and per-teacher timetables (CSV & HTML) and a combined assignment CSV

> Note: This is an educational, minimal alternative capturing **core features** of timetable generation. It is **not a full clone** of aSc Timetables.

## How to run

1. Ensure you have Python 3.9+ and `pandas` installed.
2. From this directory, run:

```bash
python main.py
```

The program will generate sample data under `./data` (if not present), solve a timetable, and write outputs to `./output`.

## Input CSVs (in `data/`)

- `teachers.csv`: `teacher_id,name`
- `classes.csv`: `class_id,name,size`
- `rooms.csv`: `room_id,name,capacity`
- `subjects.csv`: `subject_id,name`
- `curriculum.csv`: `class_id,subject_id,teacher_id,periods_per_week,room_id` (room_id optional/fixed)
- `timeslots.csv`: `day,period` (integers)
- `teacher_unavailability.csv`: `teacher_id,day,period`

You can edit these to match your school.

## Outputs (in `output/`)

- `class_<CLASSID>_timetable.csv` and `.html`
- `teacher_<TEACHERID>_timetable.csv` and `.html`
- `all_assignments.csv` (flat list of all scheduled sessions)

## Extending

- Soft constraints (e.g., avoid last period) — add a score function for value ordering.
- Split subjects into double periods — treat as grouped sessions.
- Subject/teacher load balancing by day — implement additional heuristics.
- GUI — can be added using Tkinter or a lightweight web UI (Flask) in a future step.

Licensed under MIT for your convenience.
