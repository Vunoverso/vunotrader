from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    organization_name: str = Field(min_length=2, max_length=120)
    organization_slug: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class RefreshSessionRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class UpdatePasswordRequest(BaseModel):
    access_token: str = Field(min_length=10)
    refresh_token: str = Field(min_length=10)
    new_password: str = Field(min_length=8, max_length=128)


class AuthSessionResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: int | None = None
    token_type: Literal["bearer"] = "bearer"
    user_id: str | None = None
    email: EmailStr | None = None


class ApiMessage(BaseModel):
    message: str