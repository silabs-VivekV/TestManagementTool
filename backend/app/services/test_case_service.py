from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.models.test_case import TestCase
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate
from app.services.activity_service import ActivityService


class TestCaseService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = TestCaseRepository(db)
        self.activity = ActivityService(db)

    def list(self, filters: dict, page: int, page_size: int) -> tuple[list[TestCase], int]:
        query = self.repo.build_query(filters)
        return self.repo.paginate(query, page, page_size)

    def facets(self) -> dict[str, list[str]]:
        """Distinct, non-empty values per filterable field (for dynamic dropdowns)."""
        columns = {
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
        result: dict[str, list[str]] = {}
        for name, column in columns.items():
            rows = (
                self.db.query(column)
                .filter(column.isnot(None), column != "")
                .distinct()
                .all()
            )
            result[name] = sorted({r[0] for r in rows})
        return result

    def get(self, test_case_id: int) -> TestCase:
        tc = self.repo.get(test_case_id)
        if not tc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")
        return tc

    def create(self, payload: TestCaseCreate, user_id: int) -> TestCase:
        if self.repo.get_by_case_id(payload.case_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"Case ID '{payload.case_id}' already exists"
            )
        tc = TestCase(**payload.model_dump())
        self.repo.add(tc)
        self.activity.log(
            user_id=user_id, action=ActivityAction.CREATE, entity_type="test_case", entity_id=tc.id
        )
        self.db.commit()
        self.db.refresh(tc)
        return tc

    def update(self, test_case_id: int, payload: TestCaseUpdate, user_id: int) -> TestCase:
        tc = self.get(test_case_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(tc, field, value)
        self.activity.log(
            user_id=user_id, action=ActivityAction.UPDATE, entity_type="test_case", entity_id=tc.id
        )
        self.db.commit()
        self.db.refresh(tc)
        return tc

    def delete(self, test_case_id: int, user_id: int) -> None:
        tc = self.get(test_case_id)
        self.repo.delete(tc)
        self.activity.log(
            user_id=user_id, action=ActivityAction.DELETE, entity_type="test_case", entity_id=test_case_id
        )
        self.db.commit()
