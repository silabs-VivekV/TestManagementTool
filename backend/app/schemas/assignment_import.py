from pydantic import BaseModel


class AssignmentImportError(BaseModel):
    row: int
    case_id: str | None = None
    reason: str


class AssignmentImportResult(BaseModel):
    total_rows: int
    assigned: int
    reassigned: int
    updated: int
    users_created: int
    failed: int
    created_users: list[str]
    errors: list[AssignmentImportError]
