from pydantic import BaseModel, EmailStr


class OrganizationMembership(BaseModel):
    organization_id: str
    organization_name: str
    organization_slug: str | None = None
    role: str


class CurrentUserResponse(BaseModel):
    user_id: str
    email: EmailStr | None = None
    full_name: str | None = None
    memberships: list[OrganizationMembership]