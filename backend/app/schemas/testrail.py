from pydantic import BaseModel

from app.schemas.import_result import ImportResult


class TestRailProject(BaseModel):
    id: int
    name: str


class TestRailSyncRequest(BaseModel):
    project_id: int
    suite_id: int


class TestRailSyncResult(BaseModel):
    project_id: int
    suite_id: int
    fetched: int
    output_file: str
    import_result: ImportResult
