from sqlalchemy import func
from sqlalchemy.orm import Query, Session, joinedload

from app.core.enums import ExecutionStatus
from app.models.assignment import Assignment
from app.repositories.base import BaseRepository


class AssignmentRepository(BaseRepository[Assignment]):
    def __init__(self, db: Session):
        super().__init__(Assignment, db)

    def get_with_relations(self, id: int) -> Assignment | None:
        return (
            self.db.query(Assignment)
            .options(joinedload(Assignment.test_case), joinedload(Assignment.assignee))
            .filter(Assignment.id == id)
            .first()
        )

    def build_query(self, filters: dict) -> Query:
        q = self.db.query(Assignment).options(
            joinedload(Assignment.test_case), joinedload(Assignment.assignee)
        )
        if filters.get("assigned_to"):
            q = q.filter(Assignment.assigned_to == filters["assigned_to"])
        if filters.get("status"):
            q = q.filter(Assignment.status == filters["status"])
        return q

    def paginate(self, query: Query, page: int, page_size: int) -> tuple[list[Assignment], int]:
        total = query.order_by(None).with_entities(func.count(Assignment.id)).scalar() or 0
        items = (
            query.order_by(Assignment.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def count_by_status(self, assigned_to: int | None = None) -> dict[str, int]:
        q = self.db.query(Assignment.status, func.count(Assignment.id))
        if assigned_to is not None:
            q = q.filter(Assignment.assigned_to == assigned_to)
        return {status: count for status, count in q.group_by(Assignment.status).all()}

    def active_load_per_assignee(self) -> dict[int, int]:
        rows = (
            self.db.query(Assignment.assigned_to, func.count(Assignment.id))
            .group_by(Assignment.assigned_to)
            .all()
        )
        return {assignee_id: count for assignee_id, count in rows}

    def total(self) -> int:
        return self.db.query(func.count(Assignment.id)).scalar() or 0

    def count_completed(self, assigned_to: int | None = None) -> int:
        q = self.db.query(func.count(Assignment.id)).filter(
            Assignment.status.in_([ExecutionStatus.PASSED, ExecutionStatus.FAILED])
        )
        if assigned_to is not None:
            q = q.filter(Assignment.assigned_to == assigned_to)
        return q.scalar() or 0
