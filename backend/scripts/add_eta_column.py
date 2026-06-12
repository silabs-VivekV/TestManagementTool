"""One-off migration: add the `eta` (target deadline) column to assignments.

Idempotent — safe to run multiple times.
"""

from sqlalchemy import inspect, text

from app.core.database import engine


def main() -> None:
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("assignments")}
    if "eta" in cols:
        print("Column 'eta' already exists — nothing to do.")
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE assignments ADD COLUMN eta DATE"))
    print("Added 'eta' column to assignments.")


if __name__ == "__main__":
    main()
