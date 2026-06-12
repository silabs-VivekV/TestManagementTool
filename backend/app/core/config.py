from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Test Case Assignment & Tracking Platform"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    DATABASE_URL: str = "sqlite:///./test_tracker.db"

    SECRET_KEY: str = "change-me-to-a-long-random-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ALGORITHM: str = "HS256"

    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "admin123"
    FIRST_ADMIN_NAME: str = "Administrator"

    JIRA_BASE_URL: str = ""
    JIRA_PROJECT_KEY: str = ""

    # TestRail integration (used by the "Sync from TestRail" button)
    TESTRAIL_URL: str = "https://siliconlabsconnectivitysqa.testrail.io"
    TESTRAIL_USER: str = ""
    TESTRAIL_PASSWORD: str = ""
    TESTRAIL_CASES_PAYLOAD: str = "&group_by=cases:section_id&group_id=27102&group_order=asc&display_deleted_cases=0"
    # Where the generated Master_Project_List.xlsx artifact is written.
    MASTER_LIST_OUTPUT: str = (
        "C:/Automation_Tracking_Project/Test_Rail_Master_Data/psmr-tool/automation_data/Master_Project_List.xlsx"
    )
    # Maintained register of current assignments (Assignee / Current Status / Comments).
    ASSIGNMENT_SHEET_OUTPUT: str = (
        "C:/Automation_Tracking_Project/Test_Rail_Master_Data/psmr-tool/automation_data/Assigned_Test_Cases.xlsx"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
