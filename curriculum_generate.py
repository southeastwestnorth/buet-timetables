import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

SUFFIXES = ["A", "B", "C"]
INPUT_CSV = os.path.join(DATA_DIR, "curriculum_unformated.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "curriculum.csv")

with open(INPUT_CSV, newline="", encoding="utf-8-sig") as f_in, \
     open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:

    reader = csv.DictReader(f_in)
    fieldnames = [f.strip() for f in reader.fieldnames]
    writer = csv.DictWriter(f_out, fieldnames=fieldnames)
    writer.writeheader()

    for row in reader:
        # Strip whitespace from keys
        row = {k.strip(): v for k, v in row.items()}
        base_class = row["class_id"]
        for s in SUFFIXES:
            new_row = dict(row)
            new_row["class_id"] = f"{base_class}{s}"
            writer.writerow(new_row)
