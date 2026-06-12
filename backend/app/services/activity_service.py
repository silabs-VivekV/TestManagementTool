from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.models.activity_log import ActivityLog
from app.repositories.activity_repository import ActivityRepository


class ActivityService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ActivityRepository(db)

    def log(
        self,
        *,
        user_id: int | None,
        action: ActivityAction | str,
        entity_type: str,
        entity_id: int | None = None,
        details: str | None = None,
    ) -> ActivityLog:
        log = ActivityLog(
            user_id=user_id,
            action=action.value if isinstance(action, ActivityAction) else action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        return self.repo.add(log)

    def recent(self, limit: int = 100) -> list[ActivityLog]:
        return self.repo.recent(limit)
