from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.deadline import LATE, ON_TIME, ON_TRACK, OVERDUE, deadline_status
from app.core.enums import ActivityAction, ExecutionStatus
from app.models.activity_log import ActivityLog
from app.models.assignment import Assignment
from app.models.test_case import TestCase
from app.models.user import User
from app.schemas.analytics import (
    AssigneePivotRow,
    AssignmentMatrix,
    AssignmentMatrixRow,
    AssignmentMatrixSection,
    ReleasePivotRow,
    TechnologyPivotRow,
    WeeklyBucket,
    WeeklyProgress,
    WeeklyProgressRow,
)

COMPLETED = [ExecutionStatus.PASSED, ExecutionStatus.FAILED]
COMPLETED_VALUES = {ExecutionStatus.PASSED.value, ExecutionStatus.FAILED.value}
UNSPECIFIED_RELEASE = "Unspecified"
UNSPECIFIED_SECTION = "Unspecified"


def _release_sort_key(value: str) -> tuple:
    # Keep quarter-like values (e.g. 25Q4) sorted naturally, push catch-alls to the end.
    if value == UNSPECIFIED_RELEASE:
        return (2, value)
    if value.lower() == "legacy":
        return (1, value)
    return (0, value)


def _status_summary(by_status: dict[str, int]) -> str:
    # Single status -> just the label; mixed -> "STATUS (n)" pieces, biggest first.
    items = sorted(by_status.items(), key=lambda kv: (-kv[1], kv[0]))
    if len(items) == 1:
        return items[0][0]
    return ", ".join(f"{status} ({count})" for status, count in items)


# Fixed display order for deadline categories.
_DEADLINE_ORDER = [ON_TIME, ON_TRACK, LATE, OVERDUE]


def _deadline_summary(by_deadline: dict[str, int]) -> str:
    parts = [f"{cat} ({by_deadline[cat]})" for cat in _DEADLINE_ORDER if by_deadline.get(cat)]
    return ", ".join(parts)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _apply_filters(self, query, filters: dict):
        field_map = {
            "technology": TestCase.technology,
            "priority": TestCase.priority,
            "release_version": TestCase.release_version,
            "execution_type": TestCase.execution_type,
            "product_line": TestCase.product_line,
        }
        for key, column in field_map.items():
            if filters.get(key):
                query = query.filter(column == filters[key])
        if filters.get("assignee"):
            query = query.filter(Assignment.assigned_to == filters["assignee"])
        return query

    def pivot_by_technology(self, filters: dict) -> list[TechnologyPivotRow]:
        q = (
            self.db.query(
                TestCase.technology,
                func.count(Assignment.id),
                func.sum(case((Assignment.status == ExecutionStatus.PASSED, 1), else_=0)),
                func.sum(case((Assignment.status == ExecutionStatus.FAILED, 1), else_=0)),
                func.sum(case((Assignment.status == ExecutionStatus.BLOCKED, 1), else_=0)),
            )
            .join(Assignment, Assignment.test_case_id == TestCase.id)
            .group_by(TestCase.technology)
        )
        q = self._apply_filters(q, filters)
        rows = q.all()
        return [
            TechnologyPivotRow(
                technology=tech or "UNKNOWN",
                total=total,
                passed=int(passed or 0),
                failed=int(failed or 0),
                blocked=int(blocked or 0),
            )
            for tech, total, passed, failed, blocked in rows
        ]

    def pivot_by_release(self, filters: dict) -> list[ReleasePivotRow]:
        q = (
            self.db.query(
                TestCase.release_version,
                func.count(Assignment.id),
                func.sum(case((Assignment.status.in_(COMPLETED), 1), else_=0)),
                func.sum(case((Assignment.status == ExecutionStatus.PASSED, 1), else_=0)),
                func.sum(case((Assignment.status == ExecutionStatus.FAILED, 1), else_=0)),
            )
            .join(Assignment, Assignment.test_case_id == TestCase.id)
            .group_by(TestCase.release_version)
        )
        q = self._apply_filters(q, filters)
        result = []
        for version, total, completed, passed, failed in q.all():
            total = int(total or 0)
            completed = int(completed or 0)
            passed = int(passed or 0)
            failed = int(failed or 0)
            result.append(
                ReleasePivotRow(
                    release_version=version or "UNSPECIFIED",
                    total=total,
                    completed=completed,
                    completion_pct=round((completed / total * 100), 2) if total else 0.0,
                    pass_rate=round((passed / completed * 100), 2) if completed else 0.0,
                    fail_rate=round((failed / completed * 100), 2) if completed else 0.0,
                )
            )
        return result

    def assignment_matrix(self, filters: dict) -> AssignmentMatrix:
        q = (
            self.db.query(
                User.id,
                User.name,
                TestCase.section_id,
                TestCase.release_version,
                Assignment.status,
                Assignment.eta,
                Assignment.completed_date,
            )
            .join(Assignment, Assignment.assigned_to == User.id)
            .join(TestCase, TestCase.id == Assignment.test_case_id)
        )
        q = self._apply_filters(q, filters)

        today = date.today()
        columns: set[str] = set()
        column_totals: dict[str, int] = {}
        grand_total = 0
        # assignee_id -> aggregate dict
        agg: dict[int, dict] = {}

        for uid, name, section_id, release, status, eta, completed in q.all():
            release = (release or "").strip() or UNSPECIFIED_RELEASE
            section = (section_id or "").strip() or UNSPECIFIED_SECTION
            status_val = status.value if hasattr(status, "value") else str(status)
            deadline_cat = deadline_status(eta, status, completed, today)
            columns.add(release)
            column_totals[release] = column_totals.get(release, 0) + 1
            grand_total += 1

            row = agg.setdefault(
                uid,
                {
                    "assignee_id": uid,
                    "assignee_name": name,
                    "total": 0,
                    "by_release": {},
                    "by_status": {},
                    "by_deadline": {},
                    "sections": {},
                },
            )
            row["total"] += 1
            row["by_release"][release] = row["by_release"].get(release, 0) + 1
            row["by_status"][status_val] = row["by_status"].get(status_val, 0) + 1
            row["by_deadline"][deadline_cat] = row["by_deadline"].get(deadline_cat, 0) + 1
            sec = row["sections"].setdefault(
                section,
                {"section_id": section, "total": 0, "by_release": {}, "by_status": {}, "by_deadline": {}},
            )
            sec["total"] += 1
            sec["by_release"][release] = sec["by_release"].get(release, 0) + 1
            sec["by_status"][status_val] = sec["by_status"].get(status_val, 0) + 1
            sec["by_deadline"][deadline_cat] = sec["by_deadline"].get(deadline_cat, 0) + 1

        ordered_columns = sorted(columns, key=_release_sort_key)

        rows: list[AssignmentMatrixRow] = []
        for row in sorted(agg.values(), key=lambda r: r["assignee_name"].lower()):
            sections = [
                AssignmentMatrixSection(
                    section_id=sec["section_id"],
                    total=sec["total"],
                    by_release=sec["by_release"],
                    by_status=sec["by_status"],
                    status_summary=_status_summary(sec["by_status"]),
                    by_deadline=sec["by_deadline"],
                    deadline_summary=_deadline_summary(sec["by_deadline"]),
                )
                for sec in sorted(row["sections"].values(), key=lambda s: s["section_id"].lower())
            ]
            rows.append(
                AssignmentMatrixRow(
                    assignee_id=row["assignee_id"],
                    assignee_name=row["assignee_name"],
                    total=row["total"],
                    by_release=row["by_release"],
                    by_status=row["by_status"],
                    status_summary=_status_summary(row["by_status"]),
                    by_deadline=row["by_deadline"],
                    deadline_summary=_deadline_summary(row["by_deadline"]),
                    sections=sections,
                )
            )

        return AssignmentMatrix(
            columns=ordered_columns,
            rows=rows,
            column_totals=column_totals,
            grand_total=grand_total,
        )

    def weekly_progress(self, weeks: int = 8) -> WeeklyProgress:
        weeks = max(1, min(weeks, 26))
        today = datetime.now(timezone.utc).date()
        current_monday = today - timedelta(days=today.weekday())
        week_starts = [current_monday - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
        keys = [d.isoformat() for d in week_starts]
        valid = set(keys)
        buckets = [WeeklyBucket(key=d.isoformat(), label=d.strftime("%b %d")) for d in week_starts]

        # Every team member who currently owns at least one assignment (board stays stable).
        members = (
            self.db.query(User.id, User.name)
            .join(Assignment, Assignment.assigned_to == User.id)
            .distinct()
            .all()
        )
        rows_map: dict[int, dict] = {
            uid: {
                "assignee_id": uid,
                "assignee_name": name,
                "by_week": {k: 0 for k in keys},
                "total": 0,
                "on_time": 0,
                "late": 0,
                "overdue": 0,
            }
            for uid, name in members
        }
        week_totals = {k: 0 for k in keys}
        grand_total = 0

        # A test case "progressed" when its status changed to Passed/Failed (completed) that week.
        logs = (
            self.db.query(ActivityLog.timestamp, ActivityLog.details, Assignment.assigned_to)
            .join(Assignment, Assignment.id == ActivityLog.entity_id)
            .filter(ActivityLog.action == ActivityAction.STATUS_CHANGE.value)
            .filter(ActivityLog.entity_type == "assignment")
            .all()
        )
        for ts, details, assigned_to in logs:
            if not ts or not details:
                continue
            new_status = details.split("->")[-1].strip()
            if new_status not in COMPLETED_VALUES:
                continue
            day = ts.date()
            monday = (day - timedelta(days=day.weekday())).isoformat()
            if monday not in valid:
                continue
            row = rows_map.get(assigned_to)
            if row is None:
                continue
            row["by_week"][monday] += 1
            row["total"] += 1
            week_totals[monday] += 1
            grand_total += 1

        # Deadline outcome per member (current snapshot, vs each assignment's ETA).
        today_date = today
        total_on_time = total_late = total_overdue = 0
        for assigned_to, eta, status, completed in self.db.query(
            Assignment.assigned_to, Assignment.eta, Assignment.status, Assignment.completed_date
        ).all():
            row = rows_map.get(assigned_to)
            if row is None:
                continue
            cat = deadline_status(eta, status, completed, today_date)
            if cat == ON_TIME:
                row["on_time"] += 1
                total_on_time += 1
            elif cat == LATE:
                row["late"] += 1
                total_late += 1
            elif cat == OVERDUE:
                row["overdue"] += 1
                total_overdue += 1

        rows = [
            WeeklyProgressRow(**row)
            for row in sorted(rows_map.values(), key=lambda r: r["assignee_name"].lower())
        ]
        return WeeklyProgress(
            weeks=buckets,
            rows=rows,
            week_totals=week_totals,
            grand_total=grand_total,
            total_on_time=total_on_time,
            total_late=total_late,
            total_overdue=total_overdue,
        )

    def pivot_by_assignee(self, filters: dict) -> list[AssigneePivotRow]:
        q = (
            self.db.query(
                User.id,
                User.name,
                func.count(Assignment.id),
                func.sum(case((Assignment.status.in_(COMPLETED), 1), else_=0)),
            )
            .join(Assignment, Assignment.assigned_to == User.id)
            .join(TestCase, TestCase.id == Assignment.test_case_id)
            .group_by(User.id, User.name)
        )
        q = self._apply_filters(q, filters)
        result = []
        for uid, name, total, completed in q.all():
            total = int(total or 0)
            completed = int(completed or 0)
            result.append(
                AssigneePivotRow(
                    assignee_id=uid, assignee_name=name,
                    assigned=total, completed=completed, pending=total - completed,
                )
            )
        return result
