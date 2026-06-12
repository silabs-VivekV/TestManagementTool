from pydantic import BaseModel


class TestCaseFacets(BaseModel):
    technology: list[str]
    priority: list[str]
    release_version: list[str]
    execution_type: list[str]
    product_line: list[str]
    section_id: list[str]
    sdk_type: list[str]
    product_type: list[str]
    deployment_status: list[str]
    test_case_status: list[str]
    suite_id: list[str]


class DashboardSummary(BaseModel):
    filters_applied: dict[str, str]
    total_test_cases: int
    assigned: int
    unassigned: int
    not_started: int
    in_progress: int
    blocked: int
    passed: int
    failed: int
    needs_review: int
    completed: int
    pending: int
    remaining: int
    pass_rate: float


class ExecutiveDashboard(BaseModel):
    total_test_cases: int
    assigned: int
    completed: int
    pending: int
    blocked: int
    failed: int
    passed: int
    pass_rate: float


class WorkloadItem(BaseModel):
    assignee_id: int
    assignee_name: str
    total: int
    completed: int
    pending: int


class StatusCount(BaseModel):
    status: str
    count: int


class TeamLeadDashboard(BaseModel):
    team_workload: list[WorkloadItem]
    assignment_distribution: list[StatusCount]
    execution_progress: list[StatusCount]
    release_progress: list["ReleaseProgressItem"]


class ReleaseProgressItem(BaseModel):
    release_version: str
    total: int
    completed: int
    completion_pct: float


class TeamMemberDashboard(BaseModel):
    my_assignments: int
    my_completed: int
    my_in_progress: int
    my_open_defects: int
    my_blocked: int
    status_breakdown: list[StatusCount]


TeamLeadDashboard.model_rebuild()
