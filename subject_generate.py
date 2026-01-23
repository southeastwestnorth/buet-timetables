
#!/usr/bin/env python3
import argparse
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

INPUT_CSV = os.path.join(DATA_DIR, "subjects_of_all_semester.csv")

def lt_to_class_id(lt: str) -> int:
    """
    Convert L-T like '1-1' -> 11, '1-2' -> 12, '2-1' -> 21, etc.
    """
    lt = str(lt).strip()
    return int(lt.replace("-", ""))


def generate_outputs(
    input_csv: str,
    lt_list=None,
    outdir=".",
    name_mode="code",          # "code" => name=subject_id, "title" => name=full title from source
    expand_by="section count", # column used to repeat rows in curriculum_unformated
    teacher_placeholder="blank"
):
    # Load
    df = pd.read_csv(input_csv)
    df.columns = [c.strip() for c in df.columns]

    # Validate required columns
    required = {"L-T", "subject_id", "duration", "required_room_type", "viable_rooms", "is_optional"}
    missing = sorted([c for c in required if c not in df.columns])
    if missing:
        raise ValueError(f"Missing required columns in input CSV: {missing}")

    # Filter by L-T if specified
    if lt_list:
        lt_set = {x.strip() for x in lt_list}
        df = df[df["L-T"].astype(str).str.strip().isin(lt_set)].copy()

    # Add class_id
    df["class_id"] = df["L-T"].apply(lt_to_class_id)

    # ---------- subjects.csv ----------


    subjects = pd.DataFrame({
        "class_id": df["class_id"].astype(int),
        "subject_id": df["subject_id"].fillna("").astype(str).str.strip(),
        "name": df["name"].fillna("").astype(str).str.strip(),
        "duration": pd.to_numeric(df["duration"], errors="coerce").fillna(0).astype(int),
        "required_room_type": df["required_room_type"].fillna("").astype(str).str.strip(),
        "viable_rooms": df["viable_rooms"].fillna("").astype(str).str.strip(),
        "is_optional": pd.to_numeric(df["is_optional"], errors="coerce").fillna(0).astype(int),
    }).sort_values(["class_id", "subject_id"], kind="stable").reset_index(drop=True)


    # ---------- curriculum_unformated.csv ----------
    # Repeat each subject row by section count (or whatever expand_by is)
    #repeat_counts = pd.to_numeric(df[expand_by], errors="coerce").fillna(1).astype(int).clip(lower=1)
    repeat_counts = [3] * len(df)
    rows = []
    for (_, r), n in zip(df.iterrows(), repeat_counts):
        for _ in range(n):
            rows.append({
                "class_id": int(r["class_id"]),
                "subject_id": str(r["subject_id"]).strip(),
                "teacher_id": teacher_placeholder,  # literal "blank"
                "periods_per_week": 1,
                "room_id": ""  # stays empty
            })

    curriculum = (
        pd.DataFrame(rows)
        .sort_values(["class_id", "subject_id"], kind="stable")
        .reset_index(drop=True)
    )

    # Write outputs
    os.makedirs(outdir, exist_ok=True)
    subjects_path = os.path.join(outdir, "subjects.csv")
    curriculum_path = os.path.join(outdir, "curriculum_unformated.csv")

    subjects.to_csv(subjects_path, index=False)
    curriculum.to_csv(curriculum_path, index=False)

    print(f"✅ Wrote: {subjects_path} ({len(subjects)} rows)")
    print(f"✅ Wrote: {curriculum_path} ({len(curriculum)} rows)")


def main():
    parser = argparse.ArgumentParser(
        description="Generate subjects.csv and curriculum_unformated.csv from subjects_of_all_semester(s).csv"
    )
    parser.add_argument(
        "--name-mode",
        choices=["code", "title"],
        default="title",
        help="code => name=subject_id (matches your example), title => name=full 'name' column"
    )
    parser.add_argument(
        "--teacher-placeholder",
        default="blank",
        help="Value to put in teacher_id (default: 'blank')"
    )

    args = parser.parse_args()
    generate_outputs(
        input_csv=INPUT_CSV,
        lt_list=['1-1','1-2','2-1','3-1'],
        outdir=DATA_DIR,
        name_mode=args.name_mode,
        teacher_placeholder=args.teacher_placeholder
    )


if __name__ == "__main__":
    main()
