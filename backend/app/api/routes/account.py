from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.schemas.account import CurrentUserResponse, OrganizationMembership
from app.services.auth import AuthenticatedUser

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: AuthenticatedUser = Depends(get_current_user)) -> CurrentUserResponse:
    memberships = [OrganizationMembership(**membership) for membership in current_user.memberships]
    return CurrentUserResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        full_name=None,
        memberships=memberships,
    )