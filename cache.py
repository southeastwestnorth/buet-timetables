#!/usr/bin/env python3
import os
import csv
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import time
import pandas as pd

# ------------------------------
# Paths
# ------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------------
# Data models
# ------------------------------
Timeslot = namedtuple('Timeslot', ['day', 'period'])

@dataclass(frozen=True)
class Session:
    session_id: str
    class_id: str
    subject_id: str
    teacher_id: str
    room_id: Optional[str]  # Preferred / fixed room (optional)

# ------------------------------
# Helpers
# ------------------------------

def write_csv(path: str, header: List[str], rows: List[List]):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

# ------------------------------
# Sample data generation
# ------------------------------

def generate_sample_data():
    """Create a small, solvable dataset similar to school timetabling."""
    teachers_path = os.path.join(DATA_DIR, 'teachers.csv')
    classes_path = os.path.join(DATA_DIR, 'classes.csv')
    rooms_path = os.path.join(DATA_DIR, 'rooms.csv')
    subjects_path = os.path.join(DATA_DIR, 'subjects.csv')
    curriculum_path = os.path.join(DATA_DIR, 'curriculum.csv')
    timeslots_path = os.path.join(DATA_DIR, 'timeslots.csv')
    unavail_path = os.path.join(DATA_DIR, 'teacher_unavailability.csv')

    if not os.path.exists(teachers_path):
        write_csv(teachers_path, ['teacher_id', 'name'], [
            ['T1', 'Rahman'],
            ['T2', 'Akter'],
            ['T3', 'Saha'],
        ])

    if not os.path.exists(classes_path):
        write_csv(classes_path, ['class_id', 'name', 'size'], [
            ['C7A', 'Class 7A', '28'],
            ['C7B', 'Class 7B', '26'],
        ])

    if not os.path.exists(rooms_path):
        write_csv(rooms_path, ['room_id', 'name', 'capacity'], [
            ['R1', 'Room 1', '30'],
            ['R2', 'Room 2', '30'],
            ['Lab', 'Science Lab', '28'],
        ])

    if not os.path.exists(subjects_path):
        write_csv(subjects_path, ['subject_id', 'name'], [
            ['Math', 'Mathematics'],
            ['Sci', 'Science'],
            ['Eng', 'English'],
        ])

    if not os.path.exists(curriculum_path):
        # class_id, subject_id, teacher_id, periods_per_week, room_id(optional)
        write_csv(curriculum_path, ['class_id', 'subject_id', 'teacher_id', 'periods_per_week', 'room_id'], [
            ['C7A', 'Math', 'T1', '4', ''],
            ['C7A', 'Sci', 'T2', '3', 'Lab'],
            ['C7A', 'Eng', 'T3', '3', ''],
            ['C7B', 'Math', 'T1', '4', ''],
            ['C7B', 'Sci', 'T2', '3', 'Lab'],
            ['C7B', 'Eng', 'T3', '3', ''],
        ])

    if not os.path.exists(timeslots_path):
        # 5 days x 6 periods
        rows = []
        for d in range(1, 6):  # Mon..Fri
            for p in range(1, 7):  # 6 periods/day
                rows.append([str(d), str(p)])
        write_csv(timeslots_path, ['day', 'period'], rows)

    if not os.path.exists(unavail_path):
        # teacher_id, day, period (example: T2 unavailable day 5, period 6)
        write_csv(unavail_path, ['teacher_id', 'day', 'period'], [
            ['T2', '5', '6']
        ])

# ------------------------------
# Data loading
# ------------------------------

def load_teachers():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'teachers.csv'))
    return {row['teacher_id']: row['name'] for _, row in df.iterrows()}


def load_classes():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'classes.csv'))
    return {row['class_id']: {'name': row['name'], 'size': int(row['size'])} for _, row in df.iterrows()}


def load_rooms():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'rooms.csv'))
    return {row['room_id']: {'name': row['name'], 'capacity': int(row['capacity'])} for _, row in df.iterrows()}


def load_subjects():
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'subjects.csv'))
    return {row['subject_id']: row['name'] for _, row in df.iterrows()}


def load_timeslots() -> List[Timeslot]:
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'timeslots.csv'))
    timeslots = []
    for _, row in df.iterrows():
        timeslots.append(Timeslot(int(row['day']), int(row['period'])))
    return timeslots


def load_unavailability() -> Dict[str, set]:
    import pandas as pd
    path = os.path.join(DATA_DIR, 'teacher_unavailability.csv')
    unavail = defaultdict(set)
    if os.path.exists(path):
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            unavail[row['teacher_id']].add(Timeslot(int(row['day']), int(row['period'])))
    return unavail


def load_curriculum() -> List[Session]:
    import pandas as pd
    df = pd.read_csv(os.path.join(DATA_DIR, 'curriculum.csv'))
    sessions: List[Session] = []
    idx = 0
    for _, row in df.iterrows():
        periods = int(row['periods_per_week'])
        fixed_room = row['room_id'] if (isinstance(row['room_id'], str) and row['room_id'].strip()) else None
        for k in range(periods):
            idx += 1
            sessions.append(Session(
                session_id=f'S{idx}',
                class_id=row['class_id'],
                subject_id=row['subject_id'],
                teacher_id=row['teacher_id'],
                room_id=fixed_room
            ))
    return sessions

# ------------------------------
# Timetable solver (backtracking with MRV)
# ------------------------------

class TimetableSolver:
    def __init__(self, sessions: List[Session], timeslots: List[Timeslot], rooms: Dict[str, dict], classes: Dict[str, dict], teachers: Dict[str, str], subjects: Dict[str, str], unavailability: Dict[str, set], time_limit_sec: int = 20):
        self.sessions = sessions
        self.timeslots = timeslots
        self.room_ids = list(rooms.keys())
        self.rooms = rooms
        self.classes = classes
        self.teachers = teachers
        self.subjects = subjects
        self.unavailability = unavailability
        self.time_limit_sec = time_limit_sec
        self.start_time = None

        # Assignments
        self.assignment: Dict[str, Tuple[Timeslot, str]] = {}  # session_id -> (timeslot, room_id)

        # Indexes to detect conflicts quickly
        self.teacher_busy: Dict[Tuple[str, Timeslot], bool] = {}
        self.class_busy: Dict[Tuple[str, Timeslot], bool] = {}
        self.room_busy: Dict[Tuple[str, Timeslot], bool] = {}

        # Precompute possible domains per session (timeslot, room)
        self.initial_domains: Dict[str, List[Tuple[Timeslot, str]]] = self._compute_initial_domains()

    def _compute_initial_domains(self) -> Dict[str, List[Tuple[Timeslot, str]]]:
        domains = {}
        for s in self.sessions:
            domain = []
            for t in self.timeslots:
                # Teacher availability
                if t in self.unavailability.get(s.teacher_id, set()):
                    continue
                # Rooms (respect fixed room and capacity)
                candidate_rooms = [s.room_id] if s.room_id else self.room_ids
                for r in candidate_rooms:
                    # Capacity check
                    if self.classes[s.class_id]['size'] <= self.rooms[r]['capacity']:
                        domain.append((t, r))
            domains[s.session_id] = domain
        return domains

    def _time_exceeded(self) -> bool:
        return (time.time() - self.start_time) > self.time_limit_sec

    def _is_consistent(self, s: Session, t: Timeslot, r: str) -> bool:
        if self.teacher_busy.get((s.teacher_id, t)):
            return False
        if self.class_busy.get((s.class_id, t)):
            return False
        if self.room_busy.get((r, t)):
            return False
        return True

    def _place(self, s: Session, t: Timeslot, r: str):
        self.assignment[s.session_id] = (t, r)
        self.teacher_busy[(s.teacher_id, t)] = True
        self.class_busy[(s.class_id, t)] = True
        self.room_busy[(r, t)] = True

    def _remove(self, s: Session, t: Timeslot, r: str):
        del self.assignment[s.session_id]
        del self.teacher_busy[(s.teacher_id, t)]
        del self.class_busy[(s.class_id, t)]
        del self.room_busy[(r, t)]

    def _select_unassigned_session(self, unassigned_ids: List[str]) -> str:
        # Minimum Remaining Values (MRV) heuristic using current domain filtering
        # Filter domain based on current busy maps
        best_id = None
        best_size = 10**9
        for sid in unassigned_ids:
            s = next(x for x in self.sessions if x.session_id == sid)
            pruned = 0
            for (t, r) in self.initial_domains[sid]:
                if not self._is_consistent(s, t, r):
                    pruned += 1
            domain_size = len(self.initial_domains[sid]) - pruned
            if domain_size < best_size:
                best_size = domain_size
                best_id = sid
        return best_id

    def solve(self) -> Tuple[bool, Dict[str, Tuple[Timeslot, str]]]:
        self.start_time = time.time()
        unassigned_ids = [s.session_id for s in self.sessions]
        sessions_by_id = {s.session_id: s for s in self.sessions}

        def backtrack() -> bool:
            if self._time_exceeded():
                return False
            if not unassigned_ids:
                return True
            sid = self._select_unassigned_session(unassigned_ids)
            s = sessions_by_id[sid]
            # Order values: simple ordering by day then period
            domain = sorted(self.initial_domains[sid], key=lambda x: (x[0].day, x[0].period))
            # Try each feasible value
            for (t, r) in domain:
                if self._time_exceeded():
                    return False
                if self._is_consistent(s, t, r):
                    self._place(s, t, r)
                    unassigned_ids.remove(sid)
                    if backtrack():
                        return True
                    unassigned_ids.append(sid)
                    self._remove(s, t, r)
            return False

        success = backtrack()
        return success, self.assignment

# ------------------------------
# Output generation
# ------------------------------

def create_output_tables(assignment: Dict[str, Tuple[Timeslot, str]], sessions: List[Session], teachers: Dict[str, str], classes: Dict[str, dict], rooms: Dict[str, dict], subjects: Dict[str, str], timeslots: List[Timeslot]):
    # Build indices
    sessions_by_id = {s.session_id: s for s in sessions}

    # Determine grid size
    days = sorted(set(t.day for t in timeslots))
    periods = sorted(set(t.period for t in timeslots))

    # Tables per class
    for class_id, cinfo in classes.items():
        grid = [["" for _ in periods] for _ in days]
        for sid, (t, r) in assignment.items():
            s = sessions_by_id[sid]
            if s.class_id == class_id:
                subj = subjects[s.subject_id]
                teacher = teachers[s.teacher_id]
                cell = f"{subj}\n({teacher}) @ {r}"
                di = days.index(t.day)
                pi = periods.index(t.period)
                grid[di][pi] = cell
        # Write CSV
        csv_path = os.path.join(OUT_DIR, f'class_{class_id}_timetable.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Day/Period'] + [str(p) for p in periods]
            writer.writerow(header)
            for d_i, d in enumerate(days):
                writer.writerow([str(d)] + grid[d_i])
        # Write simple HTML
        html_path = os.path.join(OUT_DIR, f'class_{class_id}_timetable.html')
        html = [
            '<html><head><meta charset="utf-8"><style>table{border-collapse:collapse;}td,th{border:1px solid #999;padding:6px;vertical-align:top;white-space:pre-wrap;}</style></head><body>',
            f'<h2>Class {cinfo["name"]} Timetable</h2>',
            '<table>',
            '<tr><th>Day/Period</th>' + ''.join([f'<th>{p}</th>' for p in periods]) + '</tr>'
        ]
        for d_i, d in enumerate(days):
            html.append('<tr>')
            html.append(f'<th>{d}</th>')
            for p_i, p in enumerate(periods):
                html.append(f'<td>{grid[d_i][p_i]}</td>')
            html.append('</tr>')
        html.append('</table></body></html>')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))

    # Tables per teacher
    for teacher_id, tname in teachers.items():
        grid = [["" for _ in periods] for _ in days]
        for sid, (t, r) in assignment.items():
            s = sessions_by_id[sid]
            if s.teacher_id == teacher_id:
                subj = subjects[s.subject_id]
                cell = f"{subj}\n{classes[s.class_id]['name']} @ {r}"
                di = days.index(t.day)
                pi = periods.index(t.period)
                grid[di][pi] = cell
        # Write CSV
        csv_path = os.path.join(OUT_DIR, f'teacher_{teacher_id}_timetable.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Day/Period'] + [str(p) for p in periods]
            writer.writerow(header)
            for d_i, d in enumerate(days):
                writer.writerow([str(d)] + grid[d_i])
        # Write HTML
        html_path = os.path.join(OUT_DIR, f'teacher_{teacher_id}_timetable.html')
        html = [
            '<html><head><meta charset="utf-8"><style>table{border-collapse:collapse;}td,th{border:1px solid #999;padding:6px;vertical-align:top;white-space:pre-wrap;}</style></head><body>',
            f'<h2>Teacher {tname} Timetable</h2>',
            '<table>',
            '<tr><th>Day/Period</th>' + ''.join([f'<th>{p}</th>' for p in periods]) + '</tr>'
        ]
        for d_i, d in enumerate(days):
            html.append('<tr>')
            html.append(f'<th>{d}</th>')
            for p_i, p in enumerate(periods):
                html.append(f'<td>{grid[d_i][p_i]}</td>')
            html.append('</tr>')
        html.append('</table></body></html>')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(html))

    # Combined assignments CSV
    combined_rows = [['session_id', 'class', 'subject', 'teacher', 'day', 'period', 'room']]
    for sid, (t, r) in sorted(assignment.items(), key=lambda x: (x[1][0].day, x[1][0].period)):
        s = sessions_by_id[sid]
        combined_rows.append([
            sid,
            s.class_id,
            subjects[s.subject_id],
            teachers[s.teacher_id],
            t.day,
            t.period,
            r
        ])
    with open(os.path.join(OUT_DIR, 'all_assignments.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(combined_rows)

# ------------------------------
# README
# ------------------------------

def write_readme():
    content = f"""
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
"""
    with open(os.path.join(BASE_DIR, 'README_TIMETABLER.md'), 'w', encoding='utf-8') as f:
        f.write(content)

# ------------------------------
# Main
# ------------------------------

def run():
    generate_sample_data()
    teachers = load_teachers()
    classes = load_classes()
    rooms = load_rooms()
    subjects = load_subjects()
    timeslots = load_timeslots()
    unavailability = load_unavailability()
    sessions = load_curriculum()

    solver = TimetableSolver(sessions, timeslots, rooms, classes, teachers, subjects, unavailability, time_limit_sec=20)
    success, assignment = solver.solve()

    if not success:
        status = "WARNING: No complete solution found within time limit. Partial assignments (if any) exported."
    else:
        status = "SUCCESS: Timetable generated."

    # Export whatever we have
    create_output_tables(assignment, sessions, teachers, classes, rooms, subjects, timeslots)
    write_readme()

    # Summary
    info = {
        'status': status,
        'sessions_total': len(sessions),
        'sessions_scheduled': len(assignment),
        'output_dir': OUT_DIR,
        'data_dir': DATA_DIR,
    }
    return info

if __name__ == '__main__':
    res = run()
    print(res)
