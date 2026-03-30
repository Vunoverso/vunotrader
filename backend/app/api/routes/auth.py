from fastapi import APIRouter, Depends, status

from app.core.dependencies import get_auth_service
from app.schemas.auth import (
    ApiMessage,
    AuthSessionResponse,
    LoginRequest,
    PasswordRecoveryRequest,
    RefreshSessionRequest,
    SignupRequest,
    UpdatePasswordRequest,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post("/signup", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthSessionResponse:
    return auth_service.signup(payload)


@router.post("/login", response_model=AuthSessionResponse)
def login(payload: LoginRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthSessionResponse:
    return auth_service.login(payload)


@router.post("/refresh", response_model=AuthSessionResponse)
def refresh(payload: RefreshSessionRequest, auth_service: AuthService = Depends(get_auth_service)) -> AuthSessionResponse:
    return auth_service.refresh_session(payload)


@router.post("/recover", response_model=ApiMessage)
def recover_password(
    payload: PasswordRecoveryRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiMessage:
    auth_service.send_password_recovery(payload.email)
    return ApiMessage(message="Recovery email sent")


@router.post("/update-password", response_model=ApiMessage)
def update_password(
    payload: UpdatePasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ApiMessage:
    auth_service.update_password(payload)
    return ApiMessage(message="Password updated")