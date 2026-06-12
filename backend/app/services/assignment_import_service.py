from __future__ import annotations

import re

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, ExecutionStatus
from app.core.security import hash_password
from app.models.assignment import Assignment
from app.models.test_case import TestCase
from app.models.user import User
from app.services.activity_service import ActivityService
from app.services.import_service import ImportService

# Column header aliases (matched case-insensitively, trimmed).
CASE_ID_ALIASES = ["case id", "case_id", "caseid", "column1", "id", "master project tc id", "master_project_tc_id"]
ASSIGNEE_ALIASES = ["assignee", "assigned to", "assignee name", "owner", "assigned_to"]
STATUS_ALIASES = ["status", "execution status", "execution_status"]
COMMENTS_ALIASES = ["comments", "comment", "remarks"]
ETA_ALIASES = ["eta", "deadline", "due date", "due_date", "target date", "target_date", "target"]

# Free-text status -> ExecutionStatus.
STATUS_MAP = {
    "": ExecutionStatus.NOT_STARTED,
    "not started": ExecutionStatus.NOT_STARTED,
    "not_started": ExecutionStatus.NOT_STARTED,
    "new": ExecutionStatus.NOT_STARTED,
    "to do": ExecutionStatus.NOT_STARTED,
    "todo": ExecutionStatus.NOT_STARTED,
    "in progress": ExecutionStatus.IN_PROGRESS,
    "in_progress": ExecutionStatus.IN_PROGRESS,
    "wip": ExecutionStatus.IN_PROGRESS,
    "blocked": ExecutionStatus.BLOCKED,
    "block": ExecutionStatus.BLOCKED,
    "pass": ExecutionStatus.PASSED,
    "passed": ExecutionStatus.PASSED,
    "fail": ExecutionStatus.FAILED,
    "failed": ExecutionStatus.FAILED,
    "needs review": ExecutionStatus.NEEDS_REVIEW,
    "needs_review": ExecutionStatus.NEEDS_REVIEW,
    "review": ExecutionStatus.NEEDS_REVIEW,
}

DEFAULT_IMPORTED_PASSWORD = "Welcome@123"


class AssignmentImportService:
    """Assign test cases to team members from an Excel/CSV sheet.

    Expected columns (header names are flexible): Case ID, Assignee, Status, Comments.
    Unknown assignees are auto-created as TEAM_MEMBER users. Each test case keeps a
    single current owner: re-importing reassigns/updates the existing assignment.
    """

    def __init__(self, db: Session):
        self.db = db
        self.activity = ActivityService(db)

    def _resolve(self, headers: list[str], aliases: list[str]) -> str | None:
        normalized = {h.strip().lower(): h for h in headers}
        for alias in aliases:
            if alias in normalized:
                return normalized[alias]
        return None

    def _user_lookup(self) -> dict[str, User]:
        users = self.db.query(User).all()
        lookup: dict[str, User] = {}
        for u in users:
            lookup[u.name.strip().lower()] = u
            lookup[u.email.strip().lower()] = u
        return lookup

    @staticmethod
    def _email_for(name: str, taken: set[str]) -> str:
        slug = re.sub(r"[^a-z0-9]+", ".", name.strip().lower()).strip(".") or "member"
        email = f"{slug}@team-tracker.com"
        i = 2
        while email in taken:
            email = f"{slug}{i}@team-tracker.com"
            i += 1
        return email

    @staticmethod
    def _parse_date(raw):
        value = str(raw).strip()
        if not value or value.lower() in {"nan", "nat", "none"}:
            return None
        try:
            ts = pd.to_datetime(value, errors="coerce", dayfirst=False)
            if pd.isna(ts):
                return None
            return ts.date()
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _clean_case_id(raw: str) -> str:
        value = str(raw).strip()
        if value.endswith(".0"):  # pandas may read ints as floats
            value = value[:-2]
        # "C19673" (Master Project TC Id) -> "19673" to match stored Case ID.
        if re.fullmatch(r"[Cc]\d+", value):
            value = value[1:]
        return value

    def import_assignments(self, filename: str, content: bytes, user_id: int) -> dict:
        df = ImportService(self.db)._read_dataframe(filename, content)
        df.columns = [str(c).strip() for c in df.columns]
        headers = list(df.columns)

        case_col = self._resolve(headers, CASE_ID_ALIASES)
        assignee_col = self._resolve(headers, ASSIGNEE_ALIASES)
        status_col = self._resolve(headers, STATUS_ALIASES)
        comments_col = self._resolve(headers, COMMENTS_ALIASES)
        eta_col = self._resolve(headers, ETA_ALIASES)

        if not case_col or not assignee_col:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Missing required columns. Need a Case ID column and an Assignee column.",
            )

        user_lookup = self._user_lookup()
        taken_emails = {u.email.strip().lower() for u in user_lookup.values() if "@" in (u.email or "")}

        errors: list[dict] = []
        assigned = reassigned = updated = users_created = 0
        created_user_names: list[str] = []

        for idx, row in df.iterrows():
            row_num = int(idx) + 2
            case_id = self._clean_case_id(row.get(case_col, ""))
            assignee_name = str(row.get(assignee_col, "")).strip()

            if not case_id:
                errors.append({"row": row_num, "case_id": None, "reason": "Missing Case ID"})
                continue
            if not assignee_name:
                errors.append({"row": row_num, "case_id": case_id, "reason": "Missing Assignee"})
                continue

            tc = self.db.query(TestCase).filter_by(case_id=case_id).first()
            if not tc:
                errors.append({"row": row_num, "case_id": case_id, "reason": "Case ID not found in system"})
                continue

            user = user_lookup.get(assignee_name.lower())
            if not user:
                email = self._email_for(assignee_name, taken_emails)
                user = User(
                    name=assignee_name,
                    email=email,
                    hashed_password=hash_password(DEFAULT_IMPORTED_PASSWORD),
                )
                self.db.add(user)
                self.db.flush()
                user_lookup[assignee_name.lower()] = user
                user_lookup[email] = user
                taken_emails.add(email)
                users_created += 1
                created_user_names.append(assignee_name)

            raw_status = str(row.get(status_col, "")).strip().lower() if status_col else ""
            exec_status = STATUS_MAP.get(raw_status, ExecutionStatus.NOT_STARTED)
            comments = str(row.get(comments_col, "")).strip() if comments_col else ""
            comments = comments or None
            eta = self._parse_date(row.get(eta_col, "")) if eta_col else None

            existing = (
                self.db.query(Assignment).filter(Assignment.test_case_id == tc.id).first()
            )
            if existing:
                changed = False
                if existing.assigned_to != user.id:
                    existing.assigned_to = user.id
                    existing.assigned_by = user_id
                    reassigned += 1
                    changed = True
                existing.status = exec_status
                if comments is not None:
                    existing.comments = comments
                if eta is not None:
                    existing.eta = eta
                if not changed:
                    updated += 1
            else:
                self.db.add(
                    Assignment(
                        test_case_id=tc.id,
                        assigned_to=user.id,
                        assigned_by=user_id,
                        status=exec_status,
                        comments=comments,
                        eta=eta,
                    )
                )
                assigned += 1

        self.activity.log(
            user_id=user_id,
            action=ActivityAction.ASSIGN,
            entity_type="assignment",
            details=(
                f"sheet={filename} assigned={assigned} reassigned={reassigned} "
                f"updated={updated} users_created={users_created} failed={len(errors)}"
            ),
        )
        self.db.commit()
        from app.services.assignment_export_service import AssignmentExportService

        AssignmentExportService(self.db).save_to_disk()

        return {
            "total_rows": int(len(df)),
            "assigned": assigned,
            "reassigned": reassigned,
            "updated": updated,
            "users_created": users_created,
            "failed": len(errors),
            "created_users": created_user_names,
            "errors": errors[:200],
        }
