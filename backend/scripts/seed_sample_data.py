"""Seed sample users and test cases for local development.

Run from the backend/ directory:  python -m scripts.seed_sample_data
"""
import random

from app.core.database import SessionLocal
from app.core.enums import UserRole
from app.core.init_db import init
from app.core.security import hash_password
from app.models.test_case import TestCase
from app.models.user import User

TECHNOLOGIES = ["WLAN STA", "BLE", "BTC", "Concurrent STA + AP"]
PRIORITIES = ["P0", "P1", "P2", "P3"]
RELEASES = ["R1.0", "R1.1", "R2.0"]
EXEC_TYPES = ["Manual", "Automated"]
PRODUCT_LINES = ["Connectivity", "Platform"]

SAMPLE_USERS = [
    ("Tina Lead", "lead@example.com", UserRole.TEAM_LEAD),
    ("Mark Member", "mark@example.com", UserRole.TEAM_MEMBER),
    ("Nina Member", "nina@example.com", UserRole.TEAM_MEMBER),
    ("Omar Member", "omar@example.com", UserRole.TEAM_MEMBER),
]


def run(num_cases: int = 500) -> None:
    init()
    db = SessionLocal()
    try:
        for name, email, role in SAMPLE_USERS:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(name=name, email=email, role=role, hashed_password=hash_password("password123")))
        db.commit()

        existing = db.query(TestCase).count()
        if existing >= num_cases:
            print(f"Already have {existing} test cases; skipping case generation.")
            return

        batch = []
        for i in range(existing + 1, num_cases + 1):
            batch.append(
                TestCase(
                    case_id=f"TC-{i:05d}",
                    title=f"Verify {random.choice(TECHNOLOGIES)} scenario #{i}",
                    priority=random.choice(PRIORITIES),
                    technology=random.choice(TECHNOLOGIES),
                    release_version=random.choice(RELEASES),
                    execution_type=random.choice(EXEC_TYPES),
                    product_line=random.choice(PRODUCT_LINES),
                    suite_id=f"SUITE-{random.randint(1, 20)}",
                )
            )
            if len(batch) >= 1000:
                db.bulk_save_objects(batch)
                db.commit()
                batch = []
        if batch:
            db.bulk_save_objects(batch)
            db.commit()
        print(f"Seeded users and {num_cases} test cases.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
