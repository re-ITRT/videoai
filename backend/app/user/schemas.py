from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=64)
    email: Optional[str] = Field(None, max_length=128)


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)


class UserAdminUpdateRequest(BaseModel):
    nickname: Optional[str] = Field(None, max_length=64)
    email: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(user|admin)$")


class UserListResponse(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserListResponse):
    updated_at: Optional[datetime] = None
