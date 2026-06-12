from sqlalchemy.orm import Session

from app.models.jira_ticket import JiraTicket
from app.repositories.base import BaseRepository


class JiraRepository(BaseRepository[JiraTicket]):
    def __init__(self, db: Session):
        super().__init__(JiraTicket, db)

    def list_for_test_case(self, test_case_id: int) -> list[JiraTicket]:
        return (
            self.db.query(JiraTicket)
            .filter(JiraTicket.test_case_id == test_case_id)
            .all()
        )
