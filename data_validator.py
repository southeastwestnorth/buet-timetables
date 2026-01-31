import pandas as pd
import logging
from collections import defaultdict

# --- Configuration ---
DATA_DIR = 'data/'
LOG_FILE = 'warnings.log'

# --- Setup Logging ---
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='w'
)

def load_data_files():
    """Loads all necessary CSV files into a dictionary of pandas DataFrames."""
    files_to_load = {
        'teachers.csv': ['teacher_id', 'name', 'seniority', 'max_load_day', 'max_load_week'],
        'subjects.csv': None, # Load all columns
        'curriculum.csv': ['class_id', 'subject_id', 'teacher_id', 'periods_per_week'],
        'classes.csv': None,
        'rooms.csv': None,
        'subjects_of_all_semester.csv': None,
        'timeslots.csv': None,
    }
    data = {}
    success = True
    for filename, use_cols in files_to_load.items():
        try:
            path = f"{DATA_DIR}{filename}"
            full_df = pd.read_csv(path)

            # If specific columns are defined, filter the DataFrame.
            if use_cols:
                # Ensure all required columns exist in the loaded CSV.
                if not all(col in full_df.columns for col in use_cols):
                    missing_cols = [col for col in use_cols if col not in full_df.columns]
                    logging.error(f"CRITICAL: The file '{filename}' is missing required columns: {missing_cols}.")
                    success = False
                    continue # Skip to the next file
                df = full_df[use_cols].copy()
            else:
                df = full_df

            # For curriculum, drop rows where essential data is missing.
            if filename == 'curriculum.csv':
                df.dropna(subset=['class_id', 'subject_id', 'teacher_id', 'periods_per_week'], inplace=True)
                df['periods_per_week'] = df['periods_per_week'].astype(int)

            data[filename] = df
        except FileNotFoundError:
            logging.error(f"CRITICAL: The file '{filename}' was not found in the '{DATA_DIR}' directory.")
            success = False
        except Exception as e:
            logging.error(f"CRITICAL: Failed to load or process '{filename}': {e}")
            success = False
    return data, success

def check_referential_integrity(datasets):
    """Checks for broken references in curriculum.csv."""
    logging.info("--- Running Referential Integrity Checks ---")
    curriculum_df = datasets['curriculum.csv']
    teachers_df = datasets['teachers.csv']
    classes_df = datasets['classes.csv']
    subjects_df = datasets['subjects.csv']

    teacher_ids = set(teachers_df['teacher_id'])
    class_ids = set(classes_df['class_id'])
    subject_ids = set(subjects_df['subject_id'])

    found_issues = False
    for index, row in curriculum_df.iterrows():
        if row['teacher_id'] not in teacher_ids:
            logging.warning(f"Referential Integrity: In curriculum.csv row {index + 2}, teacher_id '{row['teacher_id']}' not found in teachers.csv.")
            found_issues = True

        if row['class_id'] not in class_ids:
            logging.warning(f"Referential Integrity: In curriculum.csv row {index + 2}, class_id '{row['class_id']}' not found in classes.csv.")
            found_issues = True

        if row['subject_id'] not in subject_ids:
            logging.warning(f"Referential Integrity: In curriculum.csv row {index + 2}, subject_id '{row['subject_id']}' not found in subjects.csv.")
            found_issues = True

    if not found_issues:
        logging.info("Referential Integrity: All checks passed.")
    else:
        print("Referential integrity issues found. Check the log file.")

def check_duplicate_ids(datasets):
    """Checks for duplicate primary keys in data files."""
    logging.info("--- Running Duplicate ID Checks ---")

    files_and_keys = {
        'teachers.csv': 'teacher_id',
        'subjects.csv': 'subject_id',
        'rooms.csv': 'room_id',
        'classes.csv': 'class_id'
    }

    found_issues = False
    for filename, key in files_and_keys.items():
        df = datasets[filename]
        duplicates = df[df.duplicated(subset=[key], keep=False)]
        if not duplicates.empty:
            found_issues = True
            for index, row in duplicates.iterrows():
                logging.error(f"Duplicate ID: In {filename}, duplicate {key} '{row[key]}' found at row {index + 2}.")

    if not found_issues:
        logging.info("Duplicate ID Checks: All primary keys are unique.")
    else:
        print("Duplicate ID issues found. Check the log file.")

def check_teacher_workload(datasets, days_per_week):
    """Validates teacher weekly and daily workload."""
    logging.info("--- Running Teacher Workload Validation ---")

    curriculum_df = datasets['curriculum.csv']
    teachers_df = datasets['teachers.csv']
    subjects_df = datasets['subjects.csv']

    # Merge data to get subject durations
    merged_df = pd.merge(curriculum_df, subjects_df, on='subject_id')

    found_issues = False
    for teacher_id, teacher_info in teachers_df.set_index('teacher_id').iterrows():
        max_week = teacher_info['max_load_week']
        max_day = teacher_info['max_load_day']

        teacher_schedule = merged_df[merged_df['teacher_id'] == teacher_id]

        # 1. Weekly Load Check
        total_weekly_load = (teacher_schedule['periods_per_week'] * teacher_schedule['duration']).sum()
        if total_weekly_load > max_week:
            logging.error(f"Teacher Workload (Weekly): Teacher '{teacher_id}' is overloaded. Assigned: {total_weekly_load} hrs, Max: {max_week} hrs.")
            found_issues = True

        # 2. Daily Load Check (Impossible Scenarios)
        courses = []
        for _, row in teacher_schedule.iterrows():
            # Create a list of all individual class sessions for the teacher
            for _ in range(row['periods_per_week']):
                courses.append(row['duration'])

        # This is a complex combinatorial problem (bin packing).
        # We'll use a greedy heuristic for a simplified check:
        # If any single course is larger than the daily max, it's impossible.
        for course_duration in courses:
            if course_duration > max_day:
                logging.error(f"Teacher Workload (Daily): Teacher '{teacher_id}' has a course of duration {course_duration} hrs, which exceeds their daily limit of {max_day} hrs.")
                found_issues = True

        # Improved Daily Load Heuristic:
        # If a teacher has more courses than days in a week, they must double up.
        # This check verifies if doubling up on the two SHORTEST courses would
        # exceed the daily limit. This is a strong indicator of an impossible schedule.
        if len(courses) > days_per_week:
            courses.sort() # Sort ascending to find the shortest courses
            # Check if the two shortest courses together exceed the daily max
            if (courses[0] + courses[1]) > max_day:
                logging.error(
                    f"Teacher Workload (Daily): Teacher '{teacher_id}' has {len(courses)} courses to teach in "
                    f"{days_per_week} days, forcing multiple classes on at least one day. "
                    f"Their two shortest courses ({courses[0]} + {courses[1]} hrs) exceed the daily limit of {max_day} hrs."
                )
                found_issues = True

    if not found_issues:
        logging.info("Teacher Workload Validation: All checks passed.")
    else:
        print("Teacher workload issues found. Check the log file.")

def check_course_credits(datasets):
    """Validates that theory course assignments in curriculum match their credit hours."""
    logging.info("--- Running Course Credit Validation ---")

    curriculum_df = datasets['curriculum.csv']
    subjects_df = datasets['subjects.csv']
    subjects_all_sem_df = datasets['subjects_of_all_semester.csv']

    # Filter for theory courses (assuming they have no required_room_type)
    theory_subjects = subjects_df[subjects_df['required_room_type'].isnull()]
    theory_subject_ids = set(theory_subjects['subject_id'])

    # Map subject_id to credit
    credit_map = subjects_all_sem_df.set_index('subject_id')['credit'].to_dict()

    found_issues = False

    # Group curriculum by class and subject
    grouped = curriculum_df.groupby(['class_id', 'subject_id'])

    for (class_id, subject_id), group in grouped:
        if subject_id in theory_subject_ids:
            total_periods = group['periods_per_week'].sum()
            expected_credit = credit_map.get(subject_id)

            if expected_credit is not None and total_periods != expected_credit:
                logging.warning(
                    f"Course Credit: Mismatch for class '{class_id}' and subject '{subject_id}'. "
                    f"Assigned periods: {total_periods}, Expected credit hours: {expected_credit}."
                )
                found_issues = True

    if not found_issues:
        logging.info("Course Credit Validation: All theory course credits are consistent.")
    else:
        print("Course credit validation issues found. Check the log file.")

def main():
    """Main function to run all data validation checks."""
    print("Starting data validation...")
    logging.info("--- Starting Data Validation ---")

    datasets, files_loaded = load_data_files()
    if not files_loaded:
        print(f"Critical error: One or more data files could not be loaded. Check '{LOG_FILE}' for details.")
        return

    check_referential_integrity(datasets)
    check_duplicate_ids(datasets)

    # Calculate days per week from timeslots.csv
    days_per_week = datasets['timeslots.csv']['day'].nunique()
    logging.info(f"Dynamically determined {days_per_week} working days per week from timeslots.csv.")

    check_teacher_workload(datasets, days_per_week)
    check_course_credits(datasets)

    print(f"All data files loaded successfully. See '{LOG_FILE}' for the full report.")
    logging.info("--- Data Validation Complete ---")

if __name__ == "__main__":
    main()
