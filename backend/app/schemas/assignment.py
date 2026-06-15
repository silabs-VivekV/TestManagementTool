from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AutoAssignStrategy, ExecutionStatus


class AssignmentCreate(BaseModel):
    test_case_id: int
    assigned_to: int
    remarks: str | None = None


class BulkAssignmentCreate(BaseModel):
    test_case_ids: list[int] = Field(min_length=1)
    assigned_to: int
    remarks: str | None = None


class AutoAssignmentRequest(BaseModel):
    test_case_ids: list[int] = Field(min_length=1)
    assignee_ids: list[int] = Field(min_length=1)
    strategy: AutoAssignStrategy = AutoAssignStrategy.ROUND_ROBIN


class AssignByFilterRequest(BaseModel):
    assigned_to: int | None = None  # required unless dry_run
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    eta: date | None = None  # target completion date (deadline) for the assignee
    dry_run: bool = False
    case_ids: list[str] | None = None
    search: str | None = None
    # Facet filters (OR within a field, AND across fields).
    technology: list[str] | None = None
    priority: list[str] | None = None
    release_version: list[str] | None = None
    execution_type: list[str] | None = None
    product_line: list[str] | None = None
    section_id: list[str] | None = None
    sdk_type: list[str] | None = None
    product_type: list[str] | None = None
    deployment_status: list[str] | None = None
    test_case_status: list[str] | None = None
    suite_id: list[str] | None = None


class AssignByFilterSample(BaseModel):
    case_id: str
    title: str
    section_id: str | None = None
    current_assignee: str | None = None


class AssignByFilterResult(BaseModel):
    matched: int
    assigned: int
    reassigned: int
    dry_run: bool
    truncated: bool = False
    items: list[AssignByFilterSample] = []


class AssignmentStatusUpdate(BaseModel):
    status: ExecutionStatus | None = None
    comments: str | None = None
    evidence_link: str | None = None
    defect_info: str | None = None
    execution_date: datetime | None = None
    eta: date | None = None
    remarks: str | None = None


class AssignmentReassign(BaseModel):
    assigned_to: int


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    assigned_to: int
    assigned_by: int
    assigned_date: datetime
    status: ExecutionStatus
    remarks: str | None = None
    comments: str | None = None
    evidence_link: str | None = None
    defect_info: str | None = None
    jira_ticket: str | None = None
    eta: date | None = None
    execution_date: datetime | None = None
    completed_date: datetime | None = None
    updated_at: datetime


class AssignmentDetailOut(AssignmentOut):
    test_case: "TestCaseOut | None" = None
    assignee_name: str | None = None


from app.schemas.test_case import TestCaseOut  # noqa: E402

AssignmentDetailOut.model_rebuild()
