from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import UserRole


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: UserRole = UserRole.TEAM_MEMBER


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class QuickUserCreate(BaseModel):
    """Create a team member with just a name; email/password are auto-generated."""

    name: str = Field(min_length=1, max_length=120)
    role: UserRole = UserRole.TEAM_MEMBER


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    # Stored value may be an auto-generated placeholder; don't re-validate as EmailStr.
    email: str
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
