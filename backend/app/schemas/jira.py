from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JiraCreateRequest(BaseModel):
    test_case_id: int
    summary: str | None = None
    description: str | None = None


class JiraTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int
    jira_key: str
    jira_url: str
    status: str
    created_by: int
    created_at: datetime
