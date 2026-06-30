import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.import_result import ImportResult
from app.services.import_service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])

IMPORTER_ROLES = require_roles(UserRole.ADMIN, UserRole.TEAM_LEAD)


@router.get("/master-list")
def download_master_list(_: User = Depends(get_current_user)):
    """Download the on-disk Master_Project_List.xlsx artifact (any logged-in user)."""
    path = settings.MASTER_LIST_OUTPUT
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Master_Project_List.xlsx not found on the server. "
                "Run Sync from TestRail or upload a master list first."
            ),
        )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="Master_Project_List.xlsx",
    )


@router.post("/test-cases", response_model=ImportResult)
async def import_test_cases(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(IMPORTER_ROLES),
):
    content = await file.read()
    return ImportService(db).import_file(file.filename or "upload", content, user.id)
