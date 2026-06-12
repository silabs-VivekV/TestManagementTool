from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import ActivityAction
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.activity_service import ActivityService


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.activity = ActivityService(db)

    def authenticate(self, email: str, password: str) -> tuple[str, User]:
        user = self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        token = create_access_token(subject=user.id, role=user.role)
        self.activity.log(user_id=user.id, action=ActivityAction.LOGIN, entity_type="user", entity_id=user.id)
        self.db.commit()
        return token, user
