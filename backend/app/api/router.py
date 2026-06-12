from fastapi import APIRouter

from app.api.routes import (
    analytics,
    assignments,
    auth,
    dashboards,
    imports,
    jira,
    test_cases,
    testrail,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(test_cases.router)
api_router.include_router(assignments.router)
api_router.include_router(imports.router)
api_router.include_router(dashboards.router)
api_router.include_router(analytics.router)
api_router.include_router(jira.router)
api_router.include_router(testrail.router)
