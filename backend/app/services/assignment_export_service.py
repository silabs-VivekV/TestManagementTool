from __future__ import annotations

import io
import os

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deadline import deadline_status
from app.models.assignment import Assignment
from app.models.test_case import TestCase
from app.models.user import User

# Output column order for the maintained register.
EXPORT_COLUMNS = [
    "Case ID", "Title", "Priority", "Technology", "Section ID", "Release_Version",
    "Test Case Execution Type", "Product_line", "SDK_Type", "Automation_Deployment_Status",
    "Product Type", "Test Case Status", "Suite ID",
    "Assignee", "Current Status", "Comments", "Assigned Date", "ETA", "Completed Date",
    "Deadline",
]


class AssignmentExportService:
    """Builds an Excel register of every current assignment with status & comments."""

    def __init__(self, db: Session):
        self.db = db

    def build_dataframe(self) -> pd.DataFrame:
        rows = (
            self.db.query(Assignment, TestCase, User)
            .join(TestCase, Assignment.test_case_id == TestCase.id)
            .join(User, Assignment.assigned_to == User.id)
            .order_by(User.name, TestCase.case_id)
            .all()
        )
        records = []
        for a, tc, u in rows:
            records.append(
                {
                    "Case ID": tc.case_id,
                    "Title": tc.title,
                    "Priority": tc.priority,
                    "Technology": tc.technology,
                    "Section ID": tc.section_id,
                    "Release_Version": tc.release_version,
                    "Test Case Execution Type": tc.execution_type,
                    "Product_line": tc.product_line,
                    "SDK_Type": tc.sdk_type,
                    "Automation_Deployment_Status": tc.deployment_status,
                    "Product Type": tc.product_type,
                    "Test Case Status": tc.test_case_status,
                    "Suite ID": tc.suite_id,
                    "Assignee": u.name,
                    "Current Status": a.status,
                    "Comments": a.comments,
                    "Assigned Date": a.assigned_date.strftime("%Y-%m-%d %H:%M") if a.assigned_date else None,
                    "ETA": a.eta.strftime("%Y-%m-%d") if a.eta else None,
                    "Completed Date": a.completed_date.strftime("%Y-%m-%d %H:%M") if a.completed_date else None,
                    "Deadline": deadline_status(a.eta, a.status, a.completed_date),
                }
            )
        return pd.DataFrame(records, columns=EXPORT_COLUMNS)

    def to_bytes(self) -> bytes:
        df = self.build_dataframe()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Assignments", index=False)
        return buffer.getvalue()

    def save_to_disk(self) -> str | None:
        """Refresh the maintained file on disk. Never raises (file may be open in Excel)."""
        path = settings.ASSIGNMENT_SHEET_OUTPUT
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(self.to_bytes())
            return path
        except Exception:  # noqa: BLE001
            return None
