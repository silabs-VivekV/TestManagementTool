"""Import the Master Project List Excel/CSV directly into the database.

Usage (from backend/ directory):
    python -m scripts.import_master_list "C:\\Users\\viverma\\Desktop\\Master_Project_List.xlsx"
"""
import sys
from pathlib import Path

from app.core.database import SessionLocal
from app.core.init_db import init
from app.models.user import User
from app.services.import_service import ImportService

DEFAULT_PATH = r"C:\Users\viverma\Desktop\Master_Project_List.xlsx"


def run(path: str) -> None:
    file_path = Path(path)
    if not file_path.exists():
        raise SystemExit(f"File not found: {file_path}")

    init()  # ensure tables exist + admin seeded
    db = SessionLocal()
    try:
        admin = db.query(User).order_by(User.id.asc()).first()
        admin_id = admin.id if admin else None
        content = file_path.read_bytes()
        result = ImportService(db).import_file(file_path.name, content, admin_id)
        print("=" * 60)
        print("IMPORT SUMMARY")
        print("=" * 60)
        print(f"  Total rows scanned : {result.total_rows}")
        print(f"  Imported           : {result.imported}")
        print(f"  Skipped duplicates : {result.skipped_duplicates}")
        print(f"  Failed             : {result.failed}")
        if result.errors:
            print(f"\n  First {min(len(result.errors), 10)} issues:")
            for err in result.errors[:10]:
                print(f"    row {err.row}: case_id={err.case_id} -> {err.reason}")
    finally:
        db.close()


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH)
