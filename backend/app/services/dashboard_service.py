from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.enums import ExecutionStatus
from app.models.assignment import Assignment
from app.models.jira_ticket import JiraTicket
from app.models.test_case import TestCase
from app.models.user import User
from app.repositories.assignment_repository import AssignmentRepository
from app.schemas.dashboard import (
    DashboardSummary,
    ExecutiveDashboard,
    ReleaseProgressItem,
    StatusCount,
    TeamLeadDashboard,
    TeamMemberDashboard,
    WorkloadItem,
)

COMPLETED = [ExecutionStatus.PASSED, ExecutionStatus.FAILED]

TC_FILTER_COLUMNS = {
    "technology": TestCase.technology,
    "priority": TestCase.priority,
    "release_version": TestCase.release_version,
    "execution_type": TestCase.execution_type,
    "product_line": TestCase.product_line,
    "section_id": TestCase.section_id,
    "sdk_type": TestCase.sdk_type,
    "product_type": TestCase.product_type,
    "deployment_status": TestCase.deployment_status,
    "test_case_status": TestCase.test_case_status,
    "suite_id": TestCase.suite_id,
}


class DashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.assignments = AssignmentRepository(db)

    def summary(self, filters: dict) -> DashboardSummary:
        """Counts for the subset of test cases matching the given filters.

        Supports questions like "how many Automatable cases in 26Q2 are pending".
        Each filter narrows the test-case set; status counts come from those cases'
        assignments (a case with no assignment is counted as 'unassigned').
        """
        def _norm(value):
            """Normalize a filter value into a list of non-empty strings (or None)."""
            if value is None:
                return None
            values = value if isinstance(value, (list, tuple, set)) else [value]
            cleaned = [str(v) for v in values if v not in (None, "")]
            return cleaned or None

        applied: dict[str, str] = {}
        tc_filter_q = self.db.query(TestCase.id)
        for key, column in TC_FILTER_COLUMNS.items():
            values = _norm(filters.get(key))
            if values:
                applied[key] = ", ".join(values)
                tc_filter_q = tc_filter_q.filter(column.in_(values))
        tc_subquery = tc_filter_q.subquery()
        tc_ids_select = self.db.query(tc_subquery.c.id)

        total = tc_filter_q.count()

        assignment_q = self.db.query(Assignment).filter(
            Assignment.test_case_id.in_(tc_ids_select)
        )
        if filters.get("assignee"):
            assignment_q = assignment_q.filter(Assignment.assigned_to == filters["assignee"])

        status_counts: dict[str, int] = {
            status: count
            for status, count in (
                assignment_q.with_entities(Assignment.status, func.count(Assignment.id))
                .group_by(Assignment.status)
                .all()
            )
        }
        assigned = (
            assignment_q.with_entities(func.count(func.distinct(Assignment.test_case_id))).scalar()
            or 0
        )

        passed = status_counts.get(ExecutionStatus.PASSED, 0)
        failed = status_counts.get(ExecutionStatus.FAILED, 0)
        blocked = status_counts.get(ExecutionStatus.BLOCKED, 0)
        in_progress = status_counts.get(ExecutionStatus.IN_PROGRESS, 0)
        not_started = status_counts.get(ExecutionStatus.NOT_STARTED, 0)
        needs_review = status_counts.get(ExecutionStatus.NEEDS_REVIEW, 0)
        completed = passed + failed
        total_assignments = sum(status_counts.values())
        pending = total_assignments - completed
        unassigned = max(total - assigned, 0)
        remaining = total - completed
        pass_rate = round((passed / completed * 100), 2) if completed else 0.0

        return DashboardSummary(
            filters_applied=applied,
            total_test_cases=total,
            assigned=assigned,
            unassigned=unassigned,
            not_started=not_started,
            in_progress=in_progress,
            blocked=blocked,
            passed=passed,
            failed=failed,
            needs_review=needs_review,
            completed=completed,
            pending=pending,
            remaining=remaining,
            pass_rate=pass_rate,
        )

    def executive(self) -> ExecutiveDashboard:
        total_tc = self.db.query(func.count(TestCase.id)).scalar() or 0
        by_status = self.assignments.count_by_status()
        assigned = sum(by_status.values())
        passed = by_status.get(ExecutionStatus.PASSED, 0)
        failed = by_status.get(ExecutionStatus.FAILED, 0)
        blocked = by_status.get(ExecutionStatus.BLOCKED, 0)
        completed = passed + failed
        pending = assigned - completed
        pass_rate = round((passed / completed * 100), 2) if completed else 0.0
        return ExecutiveDashboard(
            total_test_cases=total_tc,
            assigned=assigned,
            completed=completed,
            pending=pending,
            blocked=blocked,
            failed=failed,
            passed=passed,
            pass_rate=pass_rate,
        )

    def team_lead(self) -> TeamLeadDashboard:
        workload_rows = (
            self.db.query(
                User.id,
                User.name,
                func.count(Assignment.id),
                func.sum(
                    case((Assignment.status.in_(COMPLETED), 1), else_=0)
                ),
            )
            .join(Assignment, Assignment.assigned_to == User.id)
            .group_by(User.id, User.name)
            .all()
        )
        workload = []
        for uid, name, total, completed in workload_rows:
            completed = int(completed or 0)
            workload.append(
                WorkloadItem(
                    assignee_id=uid, assignee_name=name, total=total,
                    completed=completed, pending=total - completed,
                )
            )

        by_status = self.assignments.count_by_status()
        distribution = [StatusCount(status=str(s), count=c) for s, c in by_status.items()]

        release_rows = (
            self.db.query(
                TestCase.release_version,
                func.count(Assignment.id),
                func.sum(case((Assignment.status.in_(COMPLETED), 1), else_=0)),
            )
            .join(Assignment, Assignment.test_case_id == TestCase.id)
            .group_by(TestCase.release_version)
            .all()
        )
        release_progress = []
        for version, total, completed in release_rows:
            completed = int(completed or 0)
            release_progress.append(
                ReleaseProgressItem(
                    release_version=version or "UNSPECIFIED",
                    total=total,
                    completed=completed,
                    completion_pct=round((completed / total * 100), 2) if total else 0.0,
                )
            )

        return TeamLeadDashboard(
            team_workload=workload,
            assignment_distribution=distribution,
            execution_progress=distribution,
            release_progress=release_progress,
        )

    def team_member(self, user_id: int) -> TeamMemberDashboard:
        by_status = self.assignments.count_by_status(assigned_to=user_id)
        total = sum(by_status.values())
        passed = by_status.get(ExecutionStatus.PASSED, 0)
        failed = by_status.get(ExecutionStatus.FAILED, 0)
        completed = passed + failed
        in_progress = by_status.get(ExecutionStatus.IN_PROGRESS, 0)
        blocked = by_status.get(ExecutionStatus.BLOCKED, 0)
        open_defects = (
            self.db.query(func.count(JiraTicket.id))
            .filter(JiraTicket.created_by == user_id, JiraTicket.status != "Closed")
            .scalar()
            or 0
        )
        breakdown = [StatusCount(status=str(s), count=c) for s, c in by_status.items()]
        return TeamMemberDashboard(
            my_assignments=total,
            my_completed=completed,
            my_in_progress=in_progress,
            my_open_defects=open_defects,
            my_blocked=blocked,
            status_breakdown=breakdown,
        )
