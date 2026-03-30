from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.supabase import get_anon_supabase, get_service_supabase
from app.schemas.auth import AuthSessionResponse, LoginRequest, RefreshSessionRequest, SignupRequest, UpdatePasswordRequest


@dataclass
class AuthenticatedUser:
    user_id: str
    email: str | None
    memberships: list[dict[str, Any]]


class AuthService:
    def __init__(self) -> None:
        self.anon_client = get_anon_supabase()
        self.service_client = get_service_supabase()

    def signup(self, payload: SignupRequest) -> AuthSessionResponse:
        result = self.anon_client.auth.sign_up(
            {
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {
                        "full_name": payload.full_name,
                    }
                },
            }
        )

        user = result.user
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Signup failed")

        self._create_default_organization(user.id, payload.organization_name, payload.organization_slug)
        session = result.session
        return AuthSessionResponse(
            access_token=session.access_token if session else None,
            refresh_token=session.refresh_token if session else None,
            expires_at=session.expires_at if session else None,
            user_id=user.id,
            email=user.email,
        )

    def login(self, payload: LoginRequest) -> AuthSessionResponse:
        result = self.anon_client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
        session = result.session
        user = result.user
        if not session or not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        return AuthSessionResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            user_id=user.id,
            email=user.email,
        )

    def refresh_session(self, payload: RefreshSessionRequest) -> AuthSessionResponse:
        result = self.anon_client.auth.refresh_session(payload.refresh_token)
        session = result.session
        user = result.user
        if not session or not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to refresh session")

        return AuthSessionResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            user_id=user.id,
            email=user.email,
        )

    def send_password_recovery(self, email: str) -> None:
        self.anon_client.auth.reset_password_email(email)

    def update_password(self, payload: UpdatePasswordRequest) -> None:
        client = get_anon_supabase()
        client.auth.set_session(payload.access_token, payload.refresh_token)
        client.auth.update_user({"password": payload.new_password})

    def get_user_from_token(self, token: str) -> AuthenticatedUser:
        result = self.service_client.auth.get_user(token)
        user = result.user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        memberships = self._get_memberships(user.id)
        return AuthenticatedUser(user_id=user.id, email=user.email, memberships=memberships)

    def _create_default_organization(self, auth_user_id: str, name: str, slug: str) -> None:
        profile = (
            self.service_client.table("user_profiles")
            .select("id")
            .eq("auth_user_id", auth_user_id)
            .limit(1)
            .execute()
        )
        if not profile.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User profile was not created by database trigger",
            )

        profile_id = profile.data[0]["id"]
        organization = (
            self.service_client.table("organizations")
            .insert({"name": name, "slug": slug, "owner_profile_id": profile_id})
            .execute()
        )
        organization_id = organization.data[0]["id"]
        self.service_client.table("organization_members").insert(
            {"organization_id": organization_id, "profile_id": profile_id, "role": "owner"}
        ).execute()

        # Cria assinatura inicial de trial (7 dias) para a organização.
        starter = (
            self.service_client.table("saas_plans")
            .select("id")
            .ilike("code", "starter")
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        plan_id = starter.data[0]["id"] if starter.data else None

        if not plan_id:
            fallback = (
                self.service_client.table("saas_plans")
                .select("id")
                .eq("is_active", True)
                .order("monthly_price")
                .limit(1)
                .execute()
            )
            plan_id = fallback.data[0]["id"] if fallback.data else None

        if plan_id:
            now = datetime.now(timezone.utc)
            trial_end = now + timedelta(days=7)
            self.service_client.table("saas_subscriptions").insert(
                {
                    "organization_id": organization_id,
                    "plan_id": plan_id,
                    "status": "trialing",
                    "billing_cycle": "monthly",
                    "current_period_start": now.isoformat(),
                    "current_period_end": trial_end.isoformat(),
                    "trial_ends_at": trial_end.isoformat(),
                    "updated_at": now.isoformat(),
                }
            ).execute()

    def _get_memberships(self, auth_user_id: str) -> list[dict[str, Any]]:
        profile = (
            self.service_client.table("user_profiles")
            .select("id, full_name")
            .eq("auth_user_id", auth_user_id)
            .limit(1)
            .execute()
        )
        if not profile.data:
            return []

        profile_id = profile.data[0]["id"]
        memberships = (
            self.service_client.table("organization_members")
            .select("role, organizations(id, name, slug)")
            .eq("profile_id", profile_id)
            .execute()
        )
        results: list[dict[str, Any]] = []
        for membership in memberships.data or []:
            organization = membership.get("organizations") or {}
            results.append(
                {
                    "organization_id": organization.get("id"),
                    "organization_name": organization.get("name"),
                    "organization_slug": organization.get("slug"),
                    "role": membership.get("role"),
                }
            )
        return results