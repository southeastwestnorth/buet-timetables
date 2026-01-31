#!/usr/bin/env python3
import os
import re
import csv
from datetime import datetime
from collections import defaultdict, namedtuple
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import time
import pandas as pd
from ortools.sat.python import cp_model

# ------------------------------
# Paths
# ------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUT_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------------
# Constants
# ------------------------------

PERIOD_CONFIG = {
    1: {"label": "1st", "time": "8:00 - 8:50"},
    2: {"label": "2nd", "time": "9:00 - 9:50"},
    3: {"label": "3rd", "time": "10:00 - 10:50"},
    4: {"label": "4th", "time": "11:00 - 11:50"},
    5: {"label": "5th", "time": "12:00 - 12:50"},
    6: {"label": "6th", "time": "1:00 - 1:30"},
    7: {"label": "7th", "time": "2:00 - 2:50"},
    8: {"label": "8th", "time": "3:00 - 3:50"},
    9: {"label": "9th", "time": "4:00 - 4:50"},
}

BREAK_TIME = "1:30 - 2:00"

DAY_MAPPING = {
    1: "Sa",
    2: "Su",
    3: "Mo",
    4: "Tu",
    5: "We",
    6: "Th",
    7: "Fr",
}

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
# Data loading
# ------------------------------

def load_info_txt() -> Dict[str, str]:
    info = {
        'session_name': 'January 2025',
        'footer_right_text': 'aSc Timetables'
    }
    path = os.path.join(BASE_DIR, 'info.txt')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, val = line.split('=', 1)
                    info[key.strip()] = val.strip()
    return info

def load_teachers() -> Dict[str, dict]:
    df = pd.read_csv(os.path.join(DATA_DIR, 'teachers.csv'))
    # Be robust against extra columns by only using the ones we need.
    return {row['teacher_id']: {
        'name': row['name'],
        'seniority': int(row['seniority']),
        'max_load_day': int(row['max_load_day']),
        'max_load_week': int(row['max_load_week']),
    } for _, row in df[['teacher_id', 'name', 'seniority', 'max_load_day', 'max_load_week']].iterrows()}

def load_classes() -> Dict[str, dict]:
    df = pd.read_csv(os.path.join(DATA_DIR, 'classes.csv'))
    return {row['class_id']: {'name': row['name'], 'size': int(row['size'])} for _, row in df.iterrows()}

def load_rooms() -> Dict[str, dict]:
    df = pd.read_csv(os.path.join(DATA_DIR, 'rooms.csv'))
    df['type'] = df['type'].fillna('')
    return {row['room_id']: {
        'name': row['name'],
        'capacity': int(row['capacity']),
        'type': row['type']
    } for _, row in df.iterrows()}

def load_subjects() -> Dict[str, dict]:
    df = pd.read_csv(os.path.join(DATA_DIR, 'subjects.csv'))
    df['required_room_type'] = df['required_room_type'].fillna('')

    # Handle potentially missing 'viable_rooms' column gracefully
    if 'viable_rooms' not in df.columns:
        df['viable_rooms'] = ''
    df['viable_rooms'] = df['viable_rooms'].fillna('')

    # Handle 'is_optional' column gracefully
    if 'is_optional' not in df.columns:
        df['is_optional'] = 0
    df['is_optional'] = df['is_optional'].fillna(0)

    subjects_data = {}
    for _, row in df.iterrows():
        viable_rooms_str = str(row['viable_rooms']).strip()

        subjects_data[row['subject_id']] = {
            'name': row['name'],
            'duration': int(row['duration']),
            'required_room_type': row['required_room_type'],
            'viable_rooms': [r.strip() for r in viable_rooms_str.split(',') if r.strip()],
            'is_optional': bool(int(row['is_optional']))
        }
    return subjects_data

def load_timeslots() -> List[Timeslot]:
    df = pd.read_csv(os.path.join(DATA_DIR, 'timeslots.csv'))
    timeslots = [Timeslot(int(row['day']), int(row['period'])) for _, row in df.iterrows()]
    return sorted(timeslots)

def load_unavailability() -> Dict[str, set]:
    path = os.path.join(DATA_DIR, 'teacher_unavailability.csv')
    unavail = defaultdict(set)
    if os.path.exists(path):
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            unavail[row['teacher_id']].add(Timeslot(int(row['day']), int(row['period'])))
    return unavail

def load_teacher_preferences() -> Dict[str, set]:
    path = os.path.join(DATA_DIR, 'teacher_preferences.csv')
    prefs = defaultdict(set)
    if os.path.exists(path):
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            prefs[row['teacher_id']].add(Timeslot(int(row['day']), int(row['period'])))
    return prefs

def load_curriculum() -> List[Session]:
    # Defines the columns that are essential for scheduling. This makes the loader
    # robust against extra columns (like 'dept') being added to the CSV.
    required_cols = ['class_id', 'subject_id', 'teacher_id', 'periods_per_week']

    # 'room_id' is optional; we check for its existence later.
    all_possible_cols = required_cols + ['room_id']

    try:
        df_full = pd.read_csv(os.path.join(DATA_DIR, 'curriculum.csv'))
    except FileNotFoundError:
        return [] # Or handle with a log/error message

    # Filter the DataFrame to only include columns we care about, if they exist.
    existing_cols = [col for col in all_possible_cols if col in df_full.columns]
    df = df_full[existing_cols].copy()

    # Drop rows where essential data is missing to prevent crashes.
    df.dropna(subset=required_cols, inplace=True)

    # Ensure 'periods_per_week' is of integer type before use.
    df['periods_per_week'] = df['periods_per_week'].astype(int)

    sessions: List[Session] = []
    idx = 0
    for _, row in df.iterrows():
        num_sessions = row['periods_per_week']

        # Handle the optional 'room_id' column gracefully.
        fixed_room = None
        if 'room_id' in df.columns and pd.notna(row['room_id']) and str(row['room_id']).strip():
            fixed_room = str(row['room_id']).strip()

        for k in range(num_sessions):
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
# Home Room Assignment
# ------------------------------

def assign_home_rooms(classes: Dict[str, dict], rooms: Dict[str, dict]) -> Dict[str, str]:
    """Assigns a home room to each class section."""
    # Group rooms by name (e.g., 'r1', 'r2')
    rooms_by_name = defaultdict(list)
    for room_id, room_info in rooms.items():
        if room_info['type'] == 'Theory': # Only consider theory rooms as home rooms
            rooms_by_name[room_info['name']].append(room_id)

    # Sort room groups by name
    sorted_room_groups = [rooms_by_name[name] for name in sorted(rooms_by_name.keys())]
    for group in sorted_room_groups:
        group.sort()

    # Group classes by base name (e.g., '11A' -> '11', '1-1-A' -> '1-1')
    classes_by_base = defaultdict(list)
    for class_id in classes:
        # Find the last non-alphanumeric character to split the section from the base name
        parts = re.split(r'([^a-zA-Z0-9])', class_id)
        if len(parts) > 2:
            base_name = "".join(parts[:-2])
        else:
            # Handle cases like '11A' by removing the last character
            base_name = class_id[:-1]
        classes_by_base[base_name].append(class_id)

    # Sort class groups by name
    sorted_class_groups = [classes_by_base[name] for name in sorted(classes_by_base.keys())]
    for group in sorted_class_groups:
        group.sort()

    # Check for mismatches
    if len(sorted_class_groups) > len(sorted_room_groups):
        raise ValueError("Not enough room groups to assign to all class groups.")

    home_room_map = {}
    for i, class_group in enumerate(sorted_class_groups):
        room_group = sorted_room_groups[i]
        if len(class_group) != len(room_group):
            raise ValueError(f"Mismatch in size for class group {class_group[0][:-1]} ({len(class_group)} sections) and room group '{rooms[room_group[0]]['name']}' ({len(room_group)} rooms).")

        for class_id, room_id in zip(class_group, room_group):
            home_room_map[class_id] = room_id

    return home_room_map

# ------------------------------
# Timetable solver (OR-Tools)
# ------------------------------

class ORTimetableSolver:
    def __init__(self, sessions, timeslots, rooms, classes, teachers, subjects, unavailability, teacher_preferences, home_room_map, time_limit_sec=30):
        self.sessions = sessions
        self.timeslots = timeslots
        self.rooms = rooms
        self.classes = classes
        self.teachers = teachers
        self.subjects = subjects
        self.unavailability = unavailability
        self.teacher_preferences = teacher_preferences
        self.home_room_map = home_room_map
        self.time_limit_sec = time_limit_sec
        self.model = cp_model.CpModel()

        # Helper structure to hold all possible (session, timeslot, room) assignments for a session
        self.possible_assignments_for_session = defaultdict(list)

    def solve(self) -> Tuple[bool, Dict[str, Tuple[Timeslot, str]]]:
        assignment = self._create_decision_variables()
        session_starts_at = self._create_intermediate_variables(assignment)

        self._add_core_constraints(assignment, session_starts_at)
        self._add_structural_constraints(session_starts_at)
        self._add_scheduling_rules(session_starts_at)
        same_day_different_teacher_penalties = self._add_same_day_course_constraints(session_starts_at)
        self._add_soft_constraints(session_starts_at, same_day_different_teacher_penalties)
        
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_sec
        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            solution = {}
            for (session_id, t, r_id), var in assignment.items():
                if solver.Value(var):
                    solution[session_id] = (t, r_id)
            return True, solution
        else:
            return False, {}

    def _create_decision_variables(self) -> Dict:
        """Create decision variables only for valid assignments."""
        assignment = {}
        for s in self.sessions:
            subject = self.subjects[s.subject_id]
            is_lab = subject.get('required_room_type') == 'Lab' and subject.get('viable_rooms')

            # Determine the set of possible rooms for this session
            possible_rooms = []
            if is_lab:
                for r_id in subject['viable_rooms']:
                    # A lab can only be in a viable room that exists and has enough capacity
                    if r_id in self.rooms and self.classes[s.class_id]['size'] <= self.rooms[r_id]['capacity']:
                        possible_rooms.append(r_id)
            else:
                # Theory sessions are assigned to their designated home room
                home_room = self.home_room_map.get(s.class_id)
                if home_room:
                    possible_rooms.append(home_room)
                # If a class has no home room, it cannot be scheduled.

            # Create variables for each valid combination of (session, timeslot, room)
            for t in self.timeslots:
                for r_id in possible_rooms:
                    var = self.model.NewBoolVar(f'assign_{s.session_id}_{t.day}_{t.period}_{r_id}')
                    key = (s.session_id, t, r_id)
                    assignment[key] = var
                    self.possible_assignments_for_session[s.session_id].append(var)
        return assignment

    def _create_intermediate_variables(self, assignment: Dict) -> Dict:
        """Create helper variables to represent if a session starts at a given time."""
        session_starts_at = {}
        for s in self.sessions:
            for t in self.timeslots:
                var = self.model.NewBoolVar(f'starts_{s.session_id}_{t.day}_{t.period}')
                session_starts_at[(s.session_id, t)] = var

                # Gather all assignments for this session starting at this timeslot
                possible_assignments_at_t = []
                # This check is simpler if we iterate through the keys of the main dict
                for (session_id, timeslot, r_id), assign_var in assignment.items():
                    if session_id == s.session_id and timeslot == t:
                        possible_assignments_at_t.append(assign_var)

                # The 'starts' variable is true if any of its room-specific assignments are true
                if possible_assignments_at_t:
                    self.model.Add(sum(possible_assignments_at_t) == var)
                else:
                    self.model.Add(var == 0) # This timeslot is impossible for this session
        return session_starts_at

    def _add_core_constraints(self, assignment: Dict, session_starts_at: Dict):
        # Each session is scheduled exactly once in one of its possible slots/rooms
        for s in self.sessions:
            self.model.AddExactlyOne(self.possible_assignments_for_session[s.session_id])

        # Teacher, class, and room conflict constraints (duration-aware)
        for t in self.timeslots:
            # Teacher conflicts: at most one session taught by a teacher can be active
            for teacher_id in self.teachers:
                active_sessions = []
                for s in self.sessions:
                    if s.teacher_id == teacher_id:
                        duration = self.subjects[s.subject_id]['duration']
                        for i in range(duration):
                            start_t = Timeslot(t.day, t.period - i)
                            if (s.session_id, start_t) in session_starts_at:
                                active_sessions.append(session_starts_at[(s.session_id, start_t)])
                self.model.Add(sum(active_sessions) <= 1)

            # Class conflicts: at most one session for a class can be active
            for class_id in self.classes:
                active_sessions = []
                for s in self.sessions:
                    if s.class_id == class_id:
                        duration = self.subjects[s.subject_id]['duration']
                        for i in range(duration):
                            start_t = Timeslot(t.day, t.period - i)
                            if (s.session_id, start_t) in session_starts_at:
                                active_sessions.append(session_starts_at[(s.session_id, start_t)])
                self.model.Add(sum(active_sessions) <= 1)

            # Room conflicts: at most one lab session can be active in a physical room
            for r_id in self.rooms:
                active_sessions_in_room = []
                for s in self.sessions:
                    subject = self.subjects[s.subject_id]
                    # This constraint only applies to labs that could be in this room
                    if r_id not in subject.get('viable_rooms', []):
                        continue

                    duration = subject['duration']
                    for i in range(duration):
                        start_t = Timeslot(t.day, t.period - i)
                        key = (s.session_id, start_t, r_id)
                        if key in assignment:
                            active_sessions_in_room.append(assignment[key])
                self.model.Add(sum(active_sessions_in_room) <= 1)
        
        # Teacher weekly and daily load constraints
        for teacher_id, teacher_info in self.teachers.items():
            weekly_load_vars = []
            for s in self.sessions:
                if s.teacher_id == teacher_id:
                    for t in self.timeslots:
                        weekly_load_vars.append(session_starts_at[(s.session_id, t)] * self.subjects[s.subject_id]['duration'])
            self.model.Add(sum(weekly_load_vars) <= teacher_info['max_load_week'])

            for day in sorted(list(set(t.day for t in self.timeslots))):
                daily_load_vars = []
                for s in self.sessions:
                    if s.teacher_id == teacher_id:
                        for t in self.timeslots:
                            if t.day == day:
                                daily_load_vars.append(session_starts_at[(s.session_id, t)] * self.subjects[s.subject_id]['duration'])
                self.model.Add(sum(daily_load_vars) <= teacher_info['max_load_day'])

        # Teacher unavailability
        for s in self.sessions:
            for t in self.timeslots:
                if t in self.unavailability.get(s.teacher_id, set()):
                    self.model.Add(session_starts_at[(s.session_id, t)] == 0)

    def _add_structural_constraints(self, session_starts_at: Dict):
        # Prevent multi-period sessions from starting too late to finish
        for s in self.sessions:
            duration = self.subjects[s.subject_id]['duration']
            if duration > 1:
                for t_idx, t in enumerate(self.timeslots):
                    max_period_for_day = max(ts.period for ts in self.timeslots if ts.day == t.day)
                    if t.period > max_period_for_day - duration + 1:
                        self.model.Add(session_starts_at[(s.session_id, t)] == 0)

                    if t_idx + duration - 1 < len(self.timeslots):
                        end_t = self.timeslots[t_idx + duration - 1]
                        if t.day != end_t.day:
                             self.model.Add(session_starts_at[(s.session_id, t)] == 0)

        # Optional courses constraint: No main courses during optional course blocks
        optional_course_subjects = {'HUM101', 'HUM103'}
        main_classes = {'12A', '12B', '12C'}
        optional_classes = {'12A1', '12A2', '12B1', '12B2'}

        for t in self.timeslots:
            is_optional_slot = self.model.NewBoolVar(f'optional_slot_{t.day}_{t.period}')

            optional_sessions_at_t = [session_starts_at[(s.session_id, t)] for s in self.sessions if s.class_id in optional_classes]
            if optional_sessions_at_t:
                self.model.Add(sum(optional_sessions_at_t) > 0).OnlyEnforceIf(is_optional_slot)
                self.model.Add(sum(optional_sessions_at_t) == 0).OnlyEnforceIf(is_optional_slot.Not())

                for s in self.sessions:
                    if s.class_id in main_classes and s.subject_id not in optional_course_subjects:
                        self.model.AddImplication(is_optional_slot, session_starts_at[(s.session_id, t)].Not())

    def _add_scheduling_rules(self, session_starts_at: Dict):
        """Apply custom scheduling rules as hard constraints."""
        for s in self.sessions:
            subject = self.subjects[s.subject_id]
            is_lab = subject.get('required_room_type') == 'Lab'
            is_optional = subject.get('is_optional', False)
            is_theory = not is_lab and not is_optional

            for t in self.timeslots:
                # Rule 1: No class can be scheduled for period 6
                if t.period == 6:
                    self.model.Add(session_starts_at[(s.session_id, t)] == 0)

                # Rule 2: Lab classes can only be started at period 1, 4, or 7
                if is_lab and t.period not in [1, 4, 7]:
                    self.model.Add(session_starts_at[(s.session_id, t)] == 0)

                # Rule 3: Theory classes cant be scheduled to 7,8,9
                if is_theory and t.period in [7, 8, 9]:
                    self.model.Add(session_starts_at[(s.session_id, t)] == 0)

    def _add_same_day_course_constraints(self, session_starts_at: Dict):
        """
        Adds constraints to prevent the same course from being scheduled twice on the same day.
        - Hard constraint: If the teacher is the same.
        - Soft constraint: If the teacher is different.
        """
        sessions_by_class_subject = defaultdict(list)
        for s in self.sessions:
            sessions_by_class_subject[(s.class_id, s.subject_id)].append(s)

        same_day_different_teacher_penalties = []
        all_days = sorted(list(set(t.day for t in self.timeslots)))

        # Pre-calculate which day each session is on
        session_on_day = {}
        for s in self.sessions:
            for day in all_days:
                var = self.model.NewBoolVar(f'session_{s.session_id}_on_day_{day}')
                session_on_day[(s.session_id, day)] = var

                # The session is on this day if it starts at any timeslot on this day
                starts_on_day = [session_starts_at[(s.session_id, t)] for t in self.timeslots if t.day == day and (s.session_id, t) in session_starts_at]
                if starts_on_day:
                    self.model.Add(sum(starts_on_day) == var)
                else:
                    self.model.Add(var == 0) # This session can never be on this day

        for (class_id, subject_id), sessions_in_group in sessions_by_class_subject.items():
            if len(sessions_in_group) < 2:
                continue

            # Group sessions in this group by teacher
            sessions_by_teacher = defaultdict(list)
            for s in sessions_in_group:
                sessions_by_teacher[s.teacher_id].append(s)

            # Hard constraint: same teacher, same course, same class
            for teacher_id, same_teacher_sessions in sessions_by_teacher.items():
                if len(same_teacher_sessions) < 2:
                    continue

                for i in range(len(same_teacher_sessions)):
                    for j in range(i + 1, len(same_teacher_sessions)):
                        s1 = same_teacher_sessions[i]
                        s2 = same_teacher_sessions[j]

                        # The two sessions cannot be on the same day
                        for day in all_days:
                            self.model.Add(session_on_day[(s1.session_id, day)] + session_on_day[(s2.session_id, day)] <= 1)

            # Soft constraint: different teachers, same course, same class
            teacher_ids = list(sessions_by_teacher.keys())
            for i in range(len(teacher_ids)):
                for j in range(i + 1, len(teacher_ids)):
                    teacher1_sessions = sessions_by_teacher[teacher_ids[i]]
                    teacher2_sessions = sessions_by_teacher[teacher_ids[j]]

                    for s1 in teacher1_sessions:
                        for s2 in teacher2_sessions:
                            # For each day, if both are scheduled, add a penalty variable
                            for day in all_days:
                                both_on_day = self.model.NewBoolVar(f'both_on_day_{s1.session_id}_{s2.session_id}_{day}')
                                # Correct logic: A <=> B and C
                                self.model.Add(session_on_day[(s1.session_id, day)] + session_on_day[(s2.session_id, day)] == 2).OnlyEnforceIf(both_on_day)
                                self.model.Add(session_on_day[(s1.session_id, day)] + session_on_day[(s2.session_id, day)] < 2).OnlyEnforceIf(both_on_day.Not())

                                same_day_different_teacher_penalties.append(both_on_day)

        return same_day_different_teacher_penalties
    
    def _add_soft_constraints(self, session_starts_at: Dict, same_day_different_teacher_penalties: List):
        objective_terms = []

        # Teacher preferences (positive score)
        for s in self.sessions:
            teacher_id = s.teacher_id
            teacher_info = self.teachers.get(teacher_id)
            if not teacher_info: continue
            
            seniority = teacher_info['seniority']
            preferences = self.teacher_preferences.get(teacher_id, set())
            
            for t in preferences:
                if (s.session_id, t) in session_starts_at:
                    objective_terms.append(
                        session_starts_at[(s.session_id, t)] * seniority
                    )
        
        # Penalty for optional courses in late periods
        penalty_for_late_optional = -1000  # A large demerit
        for s in self.sessions:
            subject = self.subjects[s.subject_id]
            if subject.get('is_optional', False):
                for t in self.timeslots:
                    if t.period in [7, 8, 9]:
                        if (s.session_id, t) in session_starts_at:
                            objective_terms.append(
                                session_starts_at[(s.session_id, t)] * penalty_for_late_optional
                            )

        # Penalty for same course, different teacher on the same day
        penalty_same_day_course = -1000
        for penalty_var in same_day_different_teacher_penalties:
            objective_terms.append(penalty_var * penalty_same_day_course)

        if objective_terms:
            self.model.Maximize(sum(objective_terms))

# ------------------------------
# Output generation
# ------------------------------

def format_class_name(class_id: str) -> str:
    # Pattern 11A -> ME L-1/T-1 (Sec A)
    if len(class_id) >= 3 and class_id[0].isdigit() and class_id[1].isdigit():
        level = class_id[0]
        term = class_id[1]
        sec = class_id[2:]
        return f"ME L-{level}/T-{term} (Sec {sec})"
    return f"ME {class_id}"

def format_room_id(room_id: str, rooms: Dict[str, dict]) -> str:
    room_info = rooms.get(room_id, {})
    if room_info.get('type') == 'Theory':
        return f"ME {room_id}"
    return room_id

def write_home_rooms_csv(home_room_map: Dict[str, str], rooms: Dict[str, dict]):
    """Writes the home room assignments to a CSV file."""
    header = ['class_id', 'home_room']
    rows = []
    for class_id, room_id in sorted(home_room_map.items()):
        rows.append([class_id, room_id])
    path = os.path.join(OUT_DIR, 'homerooms.csv')
    write_csv(path, header, rows)

def create_output_tables(assignment: Dict[str, Tuple[Timeslot, str]], sessions: List[Session], teachers: Dict[str, dict], classes: Dict[str, dict], rooms: Dict[str, dict], subjects: Dict[str, dict], timeslots: List[Timeslot], home_room_map: Dict[str, str], info: Dict[str, str]):
    sessions_by_id = {s.session_id: s for s in sessions}
    days = sorted(list(set(t.day for t in timeslots)))
    periods = sorted(list(set(t.period for t in timeslots)))

    css = """
    <style>
        body { font-family: Arial, sans-serif; }
        .timetable { border-collapse: collapse; width: 100%; table-layout: fixed; }
        .timetable th, .timetable td { border: 1px solid black; padding: 5px; text-align: center; vertical-align: middle; height: 80px; position: relative; }
        .period-header { font-size: 14px; font-weight: bold; }
        .time-header { font-size: 10px; font-weight: normal; }
        .day-label { font-size: 40px; font-weight: normal; width: 80px; }
        .subject-id { font-size: 18px; font-weight: normal; display: block; margin-bottom: 5px; }
        .teacher-id { font-size: 10px; position: absolute; bottom: 5px; right: 5px; }
        .room-info { font-size: 10px; position: absolute; bottom: 5px; left: 5px; }
        .break-cell { width: 40px; }
        .home-room { text-align: right; font-size: 14px; margin-bottom: 5px; }
        .header-title { text-align: center; margin-bottom: 0; }
        .class-title { text-align: center; font-size: 48px; margin-top: 0; margin-bottom: 10px; }
        .footer { width: 100%; margin-top: 20px; font-size: 12px; }
        .footer-left { float: left; }
        .footer-right { float: right; }
        .clearfix::after { content: ""; clear: both; display: table; }
    </style>
    """

    generated_time = datetime.now().strftime("%d/%m/%Y")

    for class_id, cinfo in classes.items():
        # grid[day_idx][period_idx] = session_id or None
        grid = [[None for _ in periods] for _ in days]
        # To handle multi-period (colspan)
        covered = [[False for _ in periods] for _ in days]

        for sid, (t, r) in assignment.items():
            s = sessions_by_id.get(sid)
            if s and s.class_id == class_id:
                di, pi = days.index(t.day), periods.index(t.period)
                grid[di][pi] = sid

        html = f"<html><head>{css}</head><body>"
        html += f"<div class='header-title'>Final Term Routine (Term: {info.get('session_name', 'N/A')})</div>"
        html += f"<div class='class-title'>{format_class_name(class_id)}</div>"

        hr_id = home_room_map.get(class_id)
        if hr_id:
            formatted_hr = format_room_id(hr_id, rooms)
            html += f"<div class='home-room'>R#{formatted_hr}</div>"

        html += "<table class='timetable'>"

        # Header Row
        html += "<tr><th></th>"
        for p in periods:
            p_label = PERIOD_CONFIG.get(p, {}).get('label', f"{p}th")
            p_time = PERIOD_CONFIG.get(p, {}).get('time', '')
            html += f"<th><div class='period-header'>{p_label}</div><div class='time-header'>{p_time}</div></th>"
            if p == 6:
                html += f"<th rowspan='{len(days) + 1}' class='break-cell'>Break<br><br><div class='time-header'>{BREAK_TIME}</div></th>"
        html += "</tr>"

        # Data Rows
        for d_idx, d in enumerate(days):
            html += "<tr>"
            html += f"<td class='day-label'>{DAY_MAPPING.get(d, str(d))}</td>"
            for p_idx, p in enumerate(periods):
                if covered[d_idx][p_idx]:
                    continue

                sid = grid[d_idx][p_idx]
                if sid:
                    s = sessions_by_id[sid]
                    duration = subjects[s.subject_id]['duration']
                    colspan = duration

                    # Ensure colspan doesn't exceed periods or cross period 6/7 boundary if that's a thing
                    # But usually labs are either 1-3, 4-6, or 7-9, so they don't cross period 6/7 boundary.

                    for i in range(colspan):
                        if p_idx + i < len(periods):
                            covered[d_idx][p_idx + i] = True

                    t_val, cell_r_id = assignment[sid]

                    room_info_display = ""
                    subject = subjects[s.subject_id]
                    if subject.get('required_room_type') == 'Lab':
                        room_name = rooms.get(cell_r_id, {}).get('name', cell_r_id)
                        room_info_display = f"<div class='room-info'>{room_name} #{cell_r_id}</div>"

                    html += f"<td colspan='{colspan}'>"
                    html += f"<span class='subject-id'>{s.subject_id}</span>"
                    html += f"<div class='teacher-id'>{s.teacher_id}</div>"
                    html += room_info_display
                    html += "</td>"
                else:
                    html += "<td></td>"
            html += "</tr>"

        html += "</table>"

        # Footer
        html += f"<div class='footer clearfix'>"
        html += f"<div class='footer-left'>Timetable generated:{generated_time}</div>"
        html += f"<div class='footer-right'>{info.get('footer_right_text', '') or 'aSc Timetables'}</div>"
        html += "</div>"

        html += "</body></html>"

        with open(os.path.join(OUT_DIR, f'class_{class_id}_timetable.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    for teacher_id, tinfo in teachers.items():
        grid = [[None for _ in periods] for _ in days]
        covered = [[False for _ in periods] for _ in days]

        for sid, (t, r) in assignment.items():
            s = sessions_by_id.get(sid)
            if s and s.teacher_id == teacher_id:
                di, pi = days.index(t.day), periods.index(t.period)
                grid[di][pi] = sid

        html = f"<html><head>{css}</head><body>"
        html += f"<div class='header-title'>Teacher Routine (Term: {info.get('session_name', 'N/A')})</div>"
        html += f"<div class='class-title'>{teachers.get(teacher_id, {}).get('name', teacher_id)} ({teacher_id})</div>"
        html += "<table class='timetable'>"

        # Header Row
        html += "<tr><th></th>"
        for p in periods:
            p_label = PERIOD_CONFIG.get(p, {}).get('label', f"{p}th")
            p_time = PERIOD_CONFIG.get(p, {}).get('time', '')
            html += f"<th><div class='period-header'>{p_label}</div><div class='time-header'>{p_time}</div></th>"
            if p == 6:
                html += f"<th rowspan='{len(days) + 1}' class='break-cell'>Break<br><br><div class='time-header'>{BREAK_TIME}</div></th>"
        html += "</tr>"

        # Data Rows
        for d_idx, d in enumerate(days):
            html += "<tr>"
            html += f"<td class='day-label'>{DAY_MAPPING.get(d, str(d))}</td>"
            for p_idx, p in enumerate(periods):
                if covered[d_idx][p_idx]:
                    continue

                sid = grid[d_idx][p_idx]
                if sid:
                    s = sessions_by_id[sid]
                    duration = subjects[s.subject_id]['duration']
                    colspan = duration
                    for i in range(colspan):
                        if p_idx + i < len(periods):
                            covered[d_idx][p_idx + i] = True

                    t_val, cell_r_id = assignment[sid]
                    formatted_room = format_room_id(cell_r_id, rooms)

                    html += f"<td colspan='{colspan}'>"
                    html += f"<span class='subject-id'>{s.subject_id}</span>"
                    html += f"<div class='teacher-id'>{s.class_id}</div>"
                    html += f"<div class='room-info'>{formatted_room}</div>"
                    html += "</td>"
                else:
                    html += "<td></td>"
            html += "</tr>"
        html += "</table>"
        html += f"<div class='footer clearfix'><div class='footer-left'>Timetable generated:{generated_time}</div><div class='footer-right'>{info.get('footer_right_text', '') or 'aSc Timetables'}</div></div>"
        html += "</body></html>"

        with open(os.path.join(OUT_DIR, f'teacher_{teacher_id}_timetable.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    combined_rows = [['session_id', 'class', 'subject', 'teacher', 'day', 'period', 'room']]
    for sid, (t, r) in sorted(assignment.items(), key=lambda x: (x[1][0].day, x[1][0].period)):
        s = sessions_by_id.get(sid)
        if s:
            combined_rows.append([
                sid, s.class_id, subjects.get(s.subject_id, {}).get('name', 'N/A'),
                teachers.get(s.teacher_id, {}).get('name', 'N/A'), t.day, t.period, r
            ])
    write_csv(os.path.join(OUT_DIR, 'all_assignments.csv'), combined_rows[0], combined_rows[1:])

# ------------------------------
# Main
# ------------------------------

def run():
    # generate_sample_data() # Use existing data
    info = load_info_txt()
    optional_included = False
    teachers = load_teachers()
    classes = load_classes()
    rooms = load_rooms()
    subjects = load_subjects()
    timeslots = load_timeslots()
    unavailability = load_unavailability()
    teacher_preferences = load_teacher_preferences()
    sessions = load_curriculum()
    
    # Filter classes to only those present in the curriculum
    active_class_ids = {s.class_id for s in sessions}
    active_classes = {cid: cinfo for cid, cinfo in classes.items() if cid in active_class_ids}

    try:
        home_room_map = assign_home_rooms(active_classes, rooms)
    except ValueError as e:
        return {'status': f"ERROR: {e}", 'sessions_total': 0, 'sessions_scheduled': 0, 'output_dir': OUT_DIR, 'data_dir': DATA_DIR}

    if not optional_included:
        optional_subject_ids = {
            subject_id for subject_id, subject_data in subjects.items()
            if subject_data.get('is_optional', False)
        }
        sessions = [
            s for s in sessions if s.subject_id not in optional_subject_ids
        ]

    # After loading and filtering, if there are no sessions, it's impossible to
    # generate a timetable. This can happen if curriculum.csv is empty or malformed.
    if not sessions:
        status = "WARNING: No valid session data found. Cannot generate a timetable."
        return {
            'status': status, 'sessions_total': 0,
            'sessions_scheduled': 0, 'output_dir': OUT_DIR,
            'data_dir': DATA_DIR,
        }

    solver = ORTimetableSolver(
        sessions, timeslots, rooms, classes, teachers, subjects, 
        unavailability, teacher_preferences, home_room_map
    )
    success, assignment = solver.solve()
    
    status = "SUCCESS: Timetable generated." if success else "WARNING: No solution found."
    if success:
        create_output_tables(assignment, sessions, teachers, classes, rooms, subjects, timeslots, home_room_map, info)
        write_home_rooms_csv(home_room_map, rooms)

    return {
        'status': status, 'sessions_total': len(sessions),
        'sessions_scheduled': len(assignment), 'output_dir': OUT_DIR,
        'data_dir': DATA_DIR,
    }

if __name__ == '__main__':
    start_time = time.time()
    res = run()
    end_time = time.time()
    print("\n--- Summary ---")
    for key, value in res.items():
        print(f"{key}: {value}")
    print(f"Total time: {end_time - start_time:.2f} seconds")
