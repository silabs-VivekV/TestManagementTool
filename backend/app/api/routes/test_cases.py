import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.common import Page
from app.schemas.dashboard import TestCaseFacets
from app.schemas.test_case import TestCaseCreate, TestCaseOut, TestCaseUpdate
from app.services.test_case_service import TestCaseService

router = APIRouter(prefix="/test-cases", tags=["test-cases"])


@router.get("/facets", response_model=TestCaseFacets)
def get_facets(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return TestCaseService(db).facets()


@router.get("", response_model=Page[TestCaseOut])
def list_test_cases(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: str | None = None,
    technology: str | None = None,
    priority: str | None = None,
    release_version: str | None = None,
    execution_type: str | None = None,
    product_line: str | None = None,
):
    filters = {
        "search": search,
        "technology": technology,
        "priority": priority,
        "release_version": release_version,
        "execution_type": execution_type,
        "product_line": product_line,
    }
    items, total = TestCaseService(db).list(filters, page, page_size)
    return Page[TestCaseOut](
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/{test_case_id}", response_model=TestCaseOut)
def get_test_case(test_case_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return TestCaseService(db).get(test_case_id)


@router.post("", response_model=TestCaseOut, status_code=201)
def create_test_case(
    payload: TestCaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return TestCaseService(db).create(payload, user.id)


@router.patch("/{test_case_id}", response_model=TestCaseOut)
def update_test_case(
    test_case_id: int,
    payload: TestCaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)),
):
    return TestCaseService(db).update(test_case_id, payload, user.id)


@router.delete("/{test_case_id}", status_code=204)
def delete_test_case(
    test_case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ADMIN)),
):
    TestCaseService(db).delete(test_case_id, user.id)
