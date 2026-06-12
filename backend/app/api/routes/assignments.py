import math
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import ExecutionStatus, UserRole
from app.models.user import User
from app.schemas.assignment import (
    AssignByFilterRequest,
    AssignByFilterResult,
    AssignmentCreate,
    AssignmentDetailOut,
    AssignmentOut,
    AssignmentStatusUpdate,
    AutoAssignmentRequest,
    BulkAssignmentCreate,
)
from app.schemas.assignment_import import AssignmentImportResult
from app.schemas.common import Message, Page
from app.services.assignment_export_service import AssignmentExportService
from app.services.assignment_import_service import AssignmentImportService
from app.services.assignment_service import AssignmentService

router = APIRouter(prefix="/assignments", tags=["assignments"])

ASSIGNER_ROLES = require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)


def _to_detail(a) -> AssignmentDetailOut:
    detail = AssignmentDetailOut.model_validate(a, from_attributes=True)
    detail.assignee_name = a.assignee.name if a.assignee else None
    return detail


@router.get("", response_model=Page[AssignmentDetailOut])
def list_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    status: ExecutionStatus | None = None,
    assigned_to: int | None = None,
):
    filters: dict = {"status": status, "assigned_to": assigned_to}
    # Team members can only see their own assignments
    if current_user.role == UserRole.TEAM_MEMBER:
        filters["assigned_to"] = current_user.id
    items, total = AssignmentService(db).list(filters, page, page_size)
    return Page[AssignmentDetailOut](
        items=[_to_detail(a) for a in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if page_size else 0,
    )


@router.get("/export")
def export_assignments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Download the current assignment register (Assignee / Current Status / Comments)."""
    service = AssignmentExportService(db)
    content = service.to_bytes()
    service.save_to_disk()
    filename = f"Assigned_Test_Cases_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{assignment_id}", response_model=AssignmentDetailOut)
def get_assignment(assignment_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _to_detail(AssignmentService(db).get(assignment_id))


@router.post("", response_model=AssignmentDetailOut, status_code=201)
def create_assignment(
    payload: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(ASSIGNER_ROLES)
):
    a = AssignmentService(db).create_single(
        payload.test_case_id, payload.assigned_to, user.id, payload.remarks
    )
    return _to_detail(a)


@router.post("/bulk", response_model=Message, status_code=201)
def bulk_assign(
    payload: BulkAssignmentCreate, db: Session = Depends(get_db), user: User = Depends(ASSIGNER_ROLES)
):
    count = AssignmentService(db).create_bulk(
        payload.test_case_ids, payload.assigned_to, user.id, payload.remarks
    )
    return Message(message=f"Created {count} assignments")


@router.post("/import", response_model=AssignmentImportResult)
async def import_assignments(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(ASSIGNER_ROLES),
):
    content = await file.read()
    return AssignmentImportService(db).import_assignments(file.filename or "upload", content, user.id)


@router.post("/by-filter", response_model=AssignByFilterResult)
def assign_by_filter(
    payload: AssignByFilterRequest, db: Session = Depends(get_db), user: User = Depends(ASSIGNER_ROLES)
):
    return AssignmentService(db).assign_by_filter(payload, user.id)


@router.post("/auto", response_model=Message, status_code=201)
def auto_assign(
    payload: AutoAssignmentRequest, db: Session = Depends(get_db), user: User = Depends(ASSIGNER_ROLES)
):
    mapping = AssignmentService(db).auto_assign(payload, user.id)
    return Message(message=f"Auto-assigned {len(mapping)} test cases using {payload.strategy.value}")


@router.patch("/{assignment_id}/status", response_model=AssignmentOut)
def update_status(
    assignment_id: int,
    payload: AssignmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = AssignmentService(db)
    assignment = service.get(assignment_id)
    if current_user.role == UserRole.TEAM_MEMBER and assignment.assigned_to != current_user.id:
        from fastapi import HTTPException, status as http_status

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail="You can only update your own assignments"
        )
    return service.update_status(assignment_id, payload, current_user.id)


@router.delete("/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: int, db: Session = Depends(get_db), user: User = Depends(ASSIGNER_ROLES)
):
    AssignmentService(db).delete(assignment_id, user.id)
