from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.test_case import TestCase
from app.repositories.base import BaseRepository


class TestCaseRepository(BaseRepository[TestCase]):
    def __init__(self, db: Session):
        super().__init__(TestCase, db)

    def get_by_case_id(self, case_id: str) -> TestCase | None:
        return self.db.query(TestCase).filter(TestCase.case_id == case_id).first()

    def existing_case_ids(self, case_ids: list[str]) -> set[str]:
        if not case_ids:
            return set()
        rows = (
            self.db.query(TestCase.case_id)
            .filter(TestCase.case_id.in_(case_ids))
            .all()
        )
        return {r[0] for r in rows}

    # All facet columns usable for filter-based assignment.
    ASSIGN_FILTER_COLUMNS = {
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

    def build_assignment_query(
        self, filters: dict, case_ids: list[str] | None, search: str | None
    ) -> Query:
        """Query test cases by any combination of facet filters, explicit Case IDs, and search."""
        q = self.db.query(TestCase)
        for key, column in self.ASSIGN_FILTER_COLUMNS.items():
            values = filters.get(key)
            if values:
                if isinstance(values, str):
                    values = [values]
                q = q.filter(column.in_(values))
        if case_ids:
            cleaned = [c.strip() for c in case_ids if c and c.strip()]
            if cleaned:
                q = q.filter(TestCase.case_id.in_(cleaned))
        if search:
            like = f"%{search.strip()}%"
            q = q.filter((TestCase.title.ilike(like)) | (TestCase.case_id.ilike(like)))
        return q

    def build_query(self, filters: dict) -> Query:
        q = self.db.query(TestCase)
        field_map = {
            "technology": TestCase.technology,
            "priority": TestCase.priority,
            "release_version": TestCase.release_version,
            "execution_type": TestCase.execution_type,
            "product_line": TestCase.product_line,
        }
        for key, column in field_map.items():
            value = filters.get(key)
            if value:
                q = q.filter(column == value)
        search = filters.get("search")
        if search:
            like = f"%{search}%"
            q = q.filter((TestCase.title.ilike(like)) | (TestCase.case_id.ilike(like)))
        return q

    def paginate(self, query: Query, page: int, page_size: int) -> tuple[list[TestCase], int]:
        total = query.order_by(None).with_entities(func.count(TestCase.id)).scalar() or 0
        items = (
            query.order_by(TestCase.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def bulk_insert(self, objects: list[TestCase]) -> None:
        self.db.bulk_save_objects(objects)
        self.db.flush()
