from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.analytics import (
    AssigneePivotRow,
    AssignmentMatrix,
    ReleasePivotRow,
    TechnologyPivotRow,
    WeeklyProgress,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])

ANALYST_ROLES = require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)


def _filters(technology, priority, release_version, execution_type, product_line, assignee) -> dict:
    return {
        "technology": technology,
        "priority": priority,
        "release_version": release_version,
        "execution_type": execution_type,
        "product_line": product_line,
        "assignee": assignee,
    }


@router.get("/pivot/technology", response_model=list[TechnologyPivotRow])
def pivot_technology(
    db: Session = Depends(get_db),
    _: User = Depends(ANALYST_ROLES),
    technology: str | None = None,
    priority: str | None = None,
    release_version: str | None = None,
    execution_type: str | None = None,
    product_line: str | None = None,
    assignee: int | None = None,
):
    return AnalyticsService(db).pivot_by_technology(
        _filters(technology, priority, release_version, execution_type, product_line, assignee)
    )


@router.get("/pivot/release", response_model=list[ReleasePivotRow])
def pivot_release(
    db: Session = Depends(get_db),
    _: User = Depends(ANALYST_ROLES),
    technology: str | None = None,
    priority: str | None = None,
    release_version: str | None = None,
    execution_type: str | None = None,
    product_line: str | None = None,
    assignee: int | None = None,
):
    return AnalyticsService(db).pivot_by_release(
        _filters(technology, priority, release_version, execution_type, product_line, assignee)
    )


@router.get("/pivot/assignee", response_model=list[AssigneePivotRow])
def pivot_assignee(
    db: Session = Depends(get_db),
    _: User = Depends(ANALYST_ROLES),
    technology: str | None = None,
    priority: str | None = None,
    release_version: str | None = None,
    execution_type: str | None = None,
    product_line: str | None = None,
    assignee: int | None = None,
):
    return AnalyticsService(db).pivot_by_assignee(
        _filters(technology, priority, release_version, execution_type, product_line, assignee)
    )


@router.get("/assignment-matrix", response_model=AssignmentMatrix)
def assignment_matrix(
    db: Session = Depends(get_db),
    _: User = Depends(ANALYST_ROLES),
    technology: str | None = None,
    priority: str | None = None,
    release_version: str | None = None,
    execution_type: str | None = None,
    product_line: str | None = None,
    assignee: int | None = None,
):
    return AnalyticsService(db).assignment_matrix(
        _filters(technology, priority, release_version, execution_type, product_line, assignee)
    )


@router.get("/weekly-progress", response_model=WeeklyProgress)
def weekly_progress(
    db: Session = Depends(get_db),
    _: User = Depends(ANALYST_ROLES),
    weeks: int = 8,
):
    return AnalyticsService(db).weekly_progress(weeks)
