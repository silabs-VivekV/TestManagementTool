from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.repositories.base import BaseRepository


class ActivityRepository(BaseRepository[ActivityLog]):
    def __init__(self, db: Session):
        super().__init__(ActivityLog, db)

    def recent(self, limit: int = 100) -> list[ActivityLog]:
        return (
            self.db.query(ActivityLog)
            .order_by(ActivityLog.timestamp.desc())
            .limit(limit)
            .all()
        )
