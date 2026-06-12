from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction, AutoAssignStrategy, ExecutionStatus
from app.models.assignment import Assignment
from app.repositories.assignment_repository import AssignmentRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.assignment import (
    AssignByFilterRequest,
    AssignmentStatusUpdate,
    AutoAssignmentRequest,
)
from app.services.activity_service import ActivityService

FACET_FILTER_KEYS = [
    "technology", "priority", "release_version", "execution_type", "product_line",
    "section_id", "sdk_type", "product_type", "deployment_status", "test_case_status", "suite_id",
]

# Max rows returned in the by-filter preview list (for checkbox selection).
PREVIEW_LIMIT = 1000


def _refresh_assignment_register(db: Session) -> None:
    """Keep the maintained assignment Excel on disk in sync (best-effort)."""
    from app.services.assignment_export_service import AssignmentExportService

    AssignmentExportService(db).save_to_disk()

COMPLETED_STATUSES = {ExecutionStatus.PASSED, ExecutionStatus.FAILED}


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AssignmentRepository(db)
        self.test_cases = TestCaseRepository(db)
        self.users = UserRepository(db)
        self.activity = ActivityService(db)

    def list(self, filters: dict, page: int, page_size: int) -> tuple[list[Assignment], int]:
        query = self.repo.build_query(filters)
        return self.repo.paginate(query, page, page_size)

    def get(self, assignment_id: int) -> Assignment:
        a = self.repo.get_with_relations(assignment_id)
        if not a:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
        return a

    def _validate_targets(self, test_case_ids: list[int], assignee_ids: list[int]) -> None:
        existing_tc = {tc.id for tc in self.test_cases.list(limit=100000)}
        missing_tc = set(test_case_ids) - existing_tc
        if missing_tc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown test case ids: {sorted(missing_tc)}"
            )
        for uid in set(assignee_ids):
            if not self.users.get(uid):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown assignee id: {uid}")

    def create_single(self, test_case_id: int, assigned_to: int, assigned_by: int, remarks: str | None) -> Assignment:
        self._validate_targets([test_case_id], [assigned_to])
        a = Assignment(
            test_case_id=test_case_id,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            remarks=remarks,
            status=ExecutionStatus.NOT_STARTED,
        )
        self.repo.add(a)
        self.activity.log(
            user_id=assigned_by, action=ActivityAction.ASSIGN, entity_type="assignment", entity_id=a.id,
            details=f"test_case={test_case_id} -> user={assigned_to}",
        )
        self.db.commit()
        return self.get(a.id)

    def create_bulk(self, test_case_ids: list[int], assigned_to: int, assigned_by: int, remarks: str | None) -> int:
        self._validate_targets(test_case_ids, [assigned_to])
        created = 0
        for tc_id in test_case_ids:
            a = Assignment(
                test_case_id=tc_id, assigned_to=assigned_to, assigned_by=assigned_by,
                remarks=remarks, status=ExecutionStatus.NOT_STARTED,
            )
            self.repo.add(a)
            created += 1
        self.activity.log(
            user_id=assigned_by, action=ActivityAction.ASSIGN, entity_type="assignment",
            details=f"bulk {created} test cases -> user={assigned_to}",
        )
        self.db.commit()
        return created

    def auto_assign(self, payload: AutoAssignmentRequest, assigned_by: int) -> dict[int, int]:
        self._validate_targets(payload.test_case_ids, payload.assignee_ids)
        mapping = self._compute_distribution(payload)
        for tc_id, user_id in mapping.items():
            a = Assignment(
                test_case_id=tc_id, assigned_to=user_id, assigned_by=assigned_by,
                status=ExecutionStatus.NOT_STARTED,
            )
            self.repo.add(a)
        self.activity.log(
            user_id=assigned_by, action=ActivityAction.ASSIGN, entity_type="assignment",
            details=f"auto-assign strategy={payload.strategy.value} count={len(mapping)}",
        )
        self.db.commit()
        return mapping

    def _compute_distribution(self, payload: AutoAssignmentRequest) -> dict[int, int]:
        strategy = payload.strategy
        assignees = payload.assignee_ids
        tc_ids = payload.test_case_ids
        mapping: dict[int, int] = {}

        if strategy == AutoAssignStrategy.ROUND_ROBIN:
            for i, tc_id in enumerate(tc_ids):
                mapping[tc_id] = assignees[i % len(assignees)]

        elif strategy == AutoAssignStrategy.EQUAL_DISTRIBUTION:
            load = self.repo.active_load_per_assignee()
            counts = {uid: load.get(uid, 0) for uid in assignees}
            for tc_id in tc_ids:
                target = min(counts, key=counts.get)
                mapping[tc_id] = target
                counts[target] += 1

        elif strategy == AutoAssignStrategy.TECHNOLOGY_BASED:
            tech_groups: dict[str, list[int]] = defaultdict(list)
            for tc in self.test_cases.list(limit=100000):
                if tc.id in tc_ids:
                    tech_groups[tc.technology or "UNKNOWN"].append(tc.id)
            sorted_techs = sorted(tech_groups)
            for idx, tech in enumerate(sorted_techs):
                owner = assignees[idx % len(assignees)]
                for tc_id in tech_groups[tech]:
                    mapping[tc_id] = owner

        elif strategy == AutoAssignStrategy.PRIORITY_BASED:
            priority_map = {tc.id: (tc.priority or "P9") for tc in self.test_cases.list(limit=100000)}
            ordered = sorted(tc_ids, key=lambda i: priority_map.get(i, "P9"))
            for i, tc_id in enumerate(ordered):
                mapping[tc_id] = assignees[i % len(assignees)]

        return mapping

    def assign_by_filter(self, req: AssignByFilterRequest, assigned_by: int) -> dict:
        """Assign every test case matching the given filters/search/Case IDs to one member.

        Keeps a single current owner per test case (re-running reassigns). Use dry_run to
        preview the matched set before committing.
        """
        filters = {key: getattr(req, key) for key in FACET_FILTER_KEYS}
        query = self.test_cases.build_assignment_query(filters, req.case_ids, req.search)
        matched_cases = query.order_by(None).all()
        matched = len(matched_cases)

        existing_map: dict[int, Assignment] = {}
        if matched_cases:
            tc_ids = [tc.id for tc in matched_cases]
            for a in self.db.query(Assignment).filter(Assignment.test_case_id.in_(tc_ids)).all():
                existing_map.setdefault(a.test_case_id, a)

        if req.dry_run:
            # Return a selectable list (capped) plus the current owner for each row.
            preview_cases = matched_cases[:PREVIEW_LIMIT]
            name_by_id: dict[int, str] = {}
            items = []
            for tc in preview_cases:
                owner = existing_map.get(tc.id)
                owner_name = None
                if owner:
                    if owner.assigned_to not in name_by_id:
                        u = self.users.get(owner.assigned_to)
                        name_by_id[owner.assigned_to] = u.name if u else f"#{owner.assigned_to}"
                    owner_name = name_by_id[owner.assigned_to]
                items.append({
                    "case_id": tc.case_id, "title": tc.title,
                    "section_id": tc.section_id, "current_assignee": owner_name,
                })
            return {
                "matched": matched, "assigned": 0, "reassigned": 0, "dry_run": True,
                "truncated": matched > len(items), "items": items,
            }

        if not req.assigned_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="assigned_to is required to assign."
            )
        if not self.users.get(req.assigned_to):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown assignee id: {req.assigned_to}"
            )
        if matched == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No test cases match the given criteria."
            )

        assigned = reassigned = 0
        for tc in matched_cases:
            existing = existing_map.get(tc.id)
            if existing:
                if existing.assigned_to != req.assigned_to:
                    existing.assigned_to = req.assigned_to
                    existing.assigned_by = assigned_by
                    reassigned += 1
                existing.status = req.status
                if req.eta is not None:
                    existing.eta = req.eta
            else:
                self.repo.add(
                    Assignment(
                        test_case_id=tc.id, assigned_to=req.assigned_to,
                        assigned_by=assigned_by, status=req.status, eta=req.eta,
                    )
                )
                assigned += 1

        self.activity.log(
            user_id=assigned_by, action=ActivityAction.ASSIGN, entity_type="assignment",
            details=f"by-filter matched={matched} assigned={assigned} reassigned={reassigned} -> user={req.assigned_to}",
        )
        self.db.commit()
        _refresh_assignment_register(self.db)
        return {
            "matched": matched, "assigned": assigned, "reassigned": reassigned,
            "dry_run": False, "truncated": False, "items": [],
        }

    def update_status(self, assignment_id: int, payload: AssignmentStatusUpdate, user_id: int) -> Assignment:
        a = self.get(assignment_id)
        old_status = a.status
        data = payload.model_dump(exclude_unset=True)
        new_status = data.get("status")

        for field in ("comments", "evidence_link", "defect_info", "execution_date", "eta", "remarks"):
            if field in data:
                setattr(a, field, data[field])

        if new_status is not None and new_status != old_status:
            a.status = new_status
            if new_status in COMPLETED_STATUSES:
                a.completed_date = datetime.now(timezone.utc)
            self.activity.log(
                user_id=user_id, action=ActivityAction.STATUS_CHANGE, entity_type="assignment",
                entity_id=a.id, details=f"{old_status} -> {new_status}",
            )
        else:
            self.activity.log(
                user_id=user_id, action=ActivityAction.UPDATE, entity_type="assignment", entity_id=a.id
            )
        self.db.commit()
        _refresh_assignment_register(self.db)
        return self.get(a.id)

    def delete(self, assignment_id: int, user_id: int) -> None:
        a = self.get(assignment_id)
        self.repo.delete(a)
        self.activity.log(
            user_id=user_id, action=ActivityAction.DELETE, entity_type="assignment", entity_id=assignment_id
        )
        self.db.commit()
