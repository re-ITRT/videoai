from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=6)
    nickname: Optional[str] = Field(None, max_length=64)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric or contain underscore")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: Optional[str] = None
