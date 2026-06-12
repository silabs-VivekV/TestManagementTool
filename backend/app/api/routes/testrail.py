from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.testrail import TestRailProject, TestRailSyncRequest, TestRailSyncResult
from app.services.testrail_service import TestRailService

router = APIRouter(prefix="/testrail", tags=["testrail"])


@router.get("/projects", response_model=list[TestRailProject])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return TestRailService(db).list_projects()


@router.post("/sync", response_model=TestRailSyncResult)
def sync_from_testrail(
    payload: TestRailSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return TestRailService(db).sync(payload.project_id, payload.suite_id, user.id)


@router.post("/sync/stream")
def sync_from_testrail_stream(
    payload: TestRailSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    """Stream live progress (NDJSON lines) while the TestRail sync runs."""
    generator = TestRailService(db).sync_stream(payload.project_id, payload.suite_id, user.id)
    return StreamingResponse(
        generator,
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
