"""One-off backfill: populate TestCase.test_case_status from the generated
Master_Project_List.xlsx by matching Case ID.

The existing test cases were imported before the "Test Case Status" field existed,
and later imports skip already-present Case IDs (so the column stayed empty).
This updates existing rows in place without touching assignments.

Run:  .\.venv\Scripts\python.exe -m scripts.backfill_test_case_status
"""

import pandas as pd

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.test_case import TestCase


def main() -> None:
    path = settings.MASTER_LIST_OUTPUT
    df = pd.read_excel(path, dtype=str).fillna("")
    if "Case ID" not in df.columns or "Test Case Status" not in df.columns:
        raise SystemExit(f"Required columns not found in {path}")

    status_by_case: dict[str, str] = {}
    for _, row in df.iterrows():
        case_id = str(row["Case ID"]).strip()
        status = str(row["Test Case Status"]).strip()
        if case_id and status:
            status_by_case[case_id] = status

    db = SessionLocal()
    try:
        updated = 0
        for tc in db.query(TestCase).all():
            new_status = status_by_case.get(str(tc.case_id).strip())
            if new_status and tc.test_case_status != new_status:
                tc.test_case_status = new_status
                updated += 1
        db.commit()
        print(f"Loaded {len(status_by_case)} statuses from sheet.")
        print(f"Updated {updated} test cases.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
