from pydantic import BaseModel


class TechnologyPivotRow(BaseModel):
    technology: str
    total: int
    passed: int
    failed: int
    blocked: int


class ReleasePivotRow(BaseModel):
    release_version: str
    total: int
    completed: int
    completion_pct: float
    pass_rate: float
    fail_rate: float


class AssigneePivotRow(BaseModel):
    assignee_id: int
    assignee_name: str
    assigned: int
    completed: int
    pending: int


class AssignmentMatrixSection(BaseModel):
    section_id: str
    total: int
    by_release: dict[str, int]
    by_status: dict[str, int]
    status_summary: str
    by_deadline: dict[str, int]
    deadline_summary: str


class AssignmentMatrixRow(BaseModel):
    assignee_id: int
    assignee_name: str
    total: int
    by_release: dict[str, int]
    by_status: dict[str, int]
    status_summary: str
    by_deadline: dict[str, int]
    deadline_summary: str
    sections: list[AssignmentMatrixSection]


class AssignmentMatrix(BaseModel):
    """Assignee -> Test Plan (Section ID) counts, broken down by release version."""

    columns: list[str]
    rows: list[AssignmentMatrixRow]
    column_totals: dict[str, int]
    grand_total: int


class WeeklyBucket(BaseModel):
    key: str  # Monday (week start) as ISO date, used as the column key
    label: str  # human-friendly label, e.g. "Jun 08"


class WeeklyProgressRow(BaseModel):
    assignee_id: int
    assignee_name: str
    by_week: dict[str, int]
    total: int
    on_time: int
    late: int
    overdue: int


class WeeklyProgress(BaseModel):
    """Test cases completed (Passed/Failed) per team member, per week."""

    weeks: list[WeeklyBucket]
    rows: list[WeeklyProgressRow]
    week_totals: dict[str, int]
    grand_total: int
    total_on_time: int
    total_late: int
    total_overdue: int
