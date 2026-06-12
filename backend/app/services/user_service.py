import re

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.security import hash_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

DEFAULT_MEMBER_PASSWORD = "Welcome@123"


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def list_users(self) -> list[User]:
        return self.users.list(limit=1000)

    def get(self, user_id: int) -> User:
        user = self.users.get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def create(self, payload: UserCreate) -> User:
        if self.users.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(
            name=payload.name,
            email=payload.email,
            role=payload.role,
            hashed_password=hash_password(payload.password),
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_quick(self, name: str, role: UserRole = UserRole.TEAM_MEMBER) -> User:
        """Create a member by name only; generate a unique email and default password."""
        name = name.strip()
        existing = self.db.query(User).filter(func.lower(User.name) == name.lower()).first() if name else None
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"A member named '{name}' already exists"
            )
        slug = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".") or "member"
        email = f"{slug}@team-tracker.com"
        i = 2
        while self.users.get_by_email(email):
            email = f"{slug}{i}@team-tracker.com"
            i += 1
        user = User(
            name=name, email=email, role=role,
            hashed_password=hash_password(DEFAULT_MEMBER_PASSWORD),
        )
        self.users.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user_id: int, payload: UserUpdate) -> User:
        user = self.get(user_id)
        if payload.name is not None:
            user.name = payload.name
        if payload.role is not None:
            user.role = payload.role
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.password:
            user.hashed_password = hash_password(payload.password)
        self.db.commit()
        self.db.refresh(user)
        return user
