from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth import AuthenticatedUser, AuthService

bearer_scheme = HTTPBearer(auto_error=False)


def get_auth_service() -> AuthService:
    return AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthenticatedUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth_service.get_user_from_token(credentials.credentials)


async def get_current_organization(
    current_user: AuthenticatedUser = Depends(get_current_user),
    organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> str:
    if not current_user.memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no organization")

    if organization_id:
        allowed = {membership["organization_id"] for membership in current_user.memberships}
        if organization_id not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden organization")
        return organization_id

    return current_user.memberships[0]["organization_id"]