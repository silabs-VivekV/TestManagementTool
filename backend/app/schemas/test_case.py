from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TestCaseBase(BaseModel):
    case_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    priority: str | None = None
    technology: str | None = None
    release_version: str | None = None
    execution_type: str | None = None
    deployment_status: str | None = None
    product_line: str | None = None
    suite_id: str | None = None


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    priority: str | None = None
    technology: str | None = None
    release_version: str | None = None
    execution_type: str | None = None
    deployment_status: str | None = None
    product_line: str | None = None
    suite_id: str | None = None


class TestCaseOut(TestCaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
