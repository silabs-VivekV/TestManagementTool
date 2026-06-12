from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummary,
    ExecutiveDashboard,
    TeamLeadDashboard,
    TeamMemberDashboard,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/summary", response_model=DashboardSummary)
def summary(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    technology: list[str] | None = Query(None),
    priority: list[str] | None = Query(None),
    release_version: list[str] | None = Query(None),
    execution_type: list[str] | None = Query(None),
    product_line: list[str] | None = Query(None),
    section_id: list[str] | None = Query(None),
    sdk_type: list[str] | None = Query(None),
    product_type: list[str] | None = Query(None),
    deployment_status: list[str] | None = Query(None),
    test_case_status: list[str] | None = Query(None),
    suite_id: list[str] | None = Query(None),
    assignee: int | None = None,
):
    filters = {
        "technology": technology,
        "priority": priority,
        "release_version": release_version,
        "execution_type": execution_type,
        "product_line": product_line,
        "section_id": section_id,
        "sdk_type": sdk_type,
        "product_type": product_type,
        "deployment_status": deployment_status,
        "test_case_status": test_case_status,
        "suite_id": suite_id,
        "assignee": assignee,
    }
    return DashboardService(db).summary(filters)


@router.get("/executive", response_model=ExecutiveDashboard)
def executive(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return DashboardService(db).executive()


@router.get("/team-lead", response_model=TeamLeadDashboard)
def team_lead(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return DashboardService(db).team_lead()


@router.get("/team-member", response_model=TeamMemberDashboard)
def team_member(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return DashboardService(db).team_member(current_user.id)
