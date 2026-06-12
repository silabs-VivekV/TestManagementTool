from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.jira import JiraCreateRequest, JiraTicketOut
from app.services.jira_service import JiraService

router = APIRouter(prefix="/jira", tags=["jira"])


@router.post("/defects", response_model=JiraTicketOut, status_code=201)
def create_defect(
    payload: JiraCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return JiraService(db).create_defect(payload, user.id)


@router.get("/test-cases/{test_case_id}", response_model=list[JiraTicketOut])
def list_for_test_case(
    test_case_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    return JiraService(db).list_for_test_case(test_case_id)
