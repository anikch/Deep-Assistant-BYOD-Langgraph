from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    is_admin: bool


class UserResponse(BaseModel):
    id: str
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True
