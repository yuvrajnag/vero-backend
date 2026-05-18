from pydantic import BaseModel, EmailStr, field_serializer
from typing import Optional
import uuid

from app.models.user import role_for_api

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "customer"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    credential: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str]
    role: Optional[str]
    is_active: bool
    is_verified: bool
    onboarding_completed: bool
    profile_status: str

    @field_serializer("role")
    def serialize_role(self, role: Optional[str]) -> Optional[str]:
        return role_for_api(role)

    class Config:
        from_attributes = True
