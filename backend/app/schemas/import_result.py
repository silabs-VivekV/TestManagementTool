from pydantic import BaseModel


class ImportError(BaseModel):
    row: int
    case_id: str | None = None
    reason: str


class ImportResult(BaseModel):
    total_rows: int
    imported: int
    skipped_duplicates: int
    failed: int
    errors: list[ImportError]
