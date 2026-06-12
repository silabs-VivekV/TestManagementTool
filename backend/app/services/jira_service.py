from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import ActivityAction
from app.models.jira_ticket import JiraTicket
from app.repositories.jira_repository import JiraRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.jira import JiraCreateRequest
from app.services.activity_service import ActivityService


class JiraService:
    """Abstraction over JIRA. In stub mode it generates deterministic keys.

    Real integration should be wired here via the JIRA MCP server; UI must
    never call JIRA directly.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = JiraRepository(db)
        self.test_cases = TestCaseRepository(db)
        self.activity = ActivityService(db)

    def create_defect(self, payload: JiraCreateRequest, user_id: int) -> JiraTicket:
        tc = self.test_cases.get(payload.test_case_id)
        if not tc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found")

        key = self._next_key()
        base_url = settings.JIRA_BASE_URL.rstrip("/") if settings.JIRA_BASE_URL else "https://jira.example.com"
        ticket = JiraTicket(
            test_case_id=tc.id,
            jira_key=key,
            jira_url=f"{base_url}/browse/{key}",
            status="Open",
            created_by=user_id,
        )
        self.repo.add(ticket)
        self.activity.log(
            user_id=user_id, action=ActivityAction.JIRA_CREATE, entity_type="jira_ticket",
            entity_id=ticket.id, details=f"{key} for test_case={tc.id}",
        )
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def list_for_test_case(self, test_case_id: int) -> list[JiraTicket]:
        return self.repo.list_for_test_case(test_case_id)

    def _next_key(self) -> str:
        project = settings.JIRA_PROJECT_KEY or "QA"
        seq = self.db.query(JiraTicket).count() + 1
        stamp = datetime.now(timezone.utc).strftime("%y%m")
        return f"{project}-{stamp}{seq:04d}"
