from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..admin_saas_activity_store import (
    build_billing_overview,
    list_plan_change_history,
    record_plan_creation_history,
    record_plan_update_history,
    record_billing_event,
)
from ..admin_saas_product_store import (
    get_admin_subscription_entry,
    list_admin_subscriptions,
    list_admin_users,
    update_admin_subscription_entry,
)
from ..admin_saas_store import (
    bootstrap_platform_admin,
    build_admin_overview,
    build_platform_admin_bootstrap_status,
    create_plan_catalog_entry,
    get_plan_catalog_entry,
    list_plan_catalog,
    update_plan_catalog_entry,
)
from ..audit import record_audit_event
from ..database import get_connection, is_integrity_error
from ..deps import get_session_context
from ..settings import load_settings


router = APIRouter(prefix="/api/admin", tags=["admin-saas"])
SETTINGS = load_settings()


class PlatformAdminBootstrapStatusResponse(BaseModel):
    is_platform_admin: bool
    can_bootstrap: bool
    reason: str
    admin_count: int


class SaasPlanCatalogPayload(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=280)
    monthly_price: float = Field(ge=0.0, le=999999.0)
    yearly_price: float | None = Field(default=None, ge=0.0, le=9999999.0)
    is_active: bool = True
    max_users: int | None = Field(default=None, ge=1, le=100000)
    max_trades_per_month: int | None = Field(default=None, ge=1, le=1000000)
    max_ai_tokens_per_day: int | None = Field(default=None, ge=1, le=100000000)
    max_storage_gb: float | None = Field(default=None, ge=0.1, le=10000.0)
    max_bots: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().lower().replace(" ", "-")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AdminSubscriptionUpdatePayload(BaseModel):
    plan_id: int = Field(ge=1)
    status: str = Field(min_length=4, max_length=20)
    billing_cycle: str = Field(min_length=6, max_length=10)

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"trialing", "active", "past_due", "paused", "canceled"}:
            raise ValueError("status invalido")
        return normalized

    @field_validator("billing_cycle")
    @classmethod
    def normalize_cycle(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"monthly", "yearly"}:
            raise ValueError("billing_cycle invalido")
        return normalized


def _require_platform_admin(context) -> None:
    if not bool(context["is_platform_admin"]):
        raise HTTPException(status_code=403, detail="Acesso restrito ao admin SaaS")


@router.get("/bootstrap-status", response_model=PlatformAdminBootstrapStatusResponse)
def platform_admin_bootstrap_status(context=Depends(get_session_context)) -> PlatformAdminBootstrapStatusResponse:
    with get_connection() as connection:
        payload = build_platform_admin_bootstrap_status(
            connection,
            is_platform_admin=bool(context["is_platform_admin"]),
            app_env=SETTINGS.app_env,
        )
    return PlatformAdminBootstrapStatusResponse(**payload)


@router.post("/bootstrap-platform-admin", response_model=PlatformAdminBootstrapStatusResponse)
def bootstrap_platform_admin_access(context=Depends(get_session_context)) -> PlatformAdminBootstrapStatusResponse:
    with get_connection() as connection:
        payload = build_platform_admin_bootstrap_status(
            connection,
            is_platform_admin=bool(context["is_platform_admin"]),
            app_env=SETTINGS.app_env,
        )
        if not bool(payload["can_bootstrap"]):
            raise HTTPException(status_code=403, detail="Bootstrap de admin SaaS indisponivel")
        bootstrap_platform_admin(connection, user_id=int(context["user_id"]))
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="platform_admin_bootstrapped",
            payload={"source": "development_bootstrap"},
            user_id=int(context["user_id"]),
        )
        updated = build_platform_admin_bootstrap_status(
            connection,
            is_platform_admin=True,
            app_env=SETTINGS.app_env,
        )
    return PlatformAdminBootstrapStatusResponse(**updated)


@router.get("/saas/overview")
def read_admin_saas_overview(context=Depends(get_session_context)) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return build_admin_overview(connection)


@router.get("/saas/plans")
def read_admin_saas_plans(context=Depends(get_session_context)) -> list[dict[str, object]]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return list_plan_catalog(connection)


@router.get("/saas/plan-changes")
def read_admin_saas_plan_changes(
    limit: int = Query(default=50, ge=1, le=200),
    plan_id: int | None = Query(default=None, ge=1),
    context=Depends(get_session_context),
) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return {"changes": list_plan_change_history(connection, limit=limit, plan_id=plan_id)}


@router.get("/saas/billing")
def read_admin_saas_billing(
    limit: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    provider: str | None = Query(default=None),
    context=Depends(get_session_context),
) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return build_billing_overview(connection, limit=limit, status=status, provider=provider)


@router.get("/saas/users")
def read_admin_saas_users(
    limit: int = Query(default=80, ge=1, le=200),
    search: str | None = Query(default=None, min_length=2, max_length=120),
    context=Depends(get_session_context),
) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return {"users": list_admin_users(connection, limit=limit, search=search)}


@router.get("/saas/subscriptions")
def read_admin_saas_subscriptions(
    limit: int = Query(default=80, ge=1, le=200),
    status: str | None = Query(default=None),
    plan_id: int | None = Query(default=None, ge=1),
    context=Depends(get_session_context),
) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        return {
            "subscriptions": list_admin_subscriptions(
                connection,
                limit=limit,
                status=status,
                plan_id=plan_id,
            )
        }


@router.post("/saas/plans")
def create_admin_saas_plan(payload: SaasPlanCatalogPayload, context=Depends(get_session_context)) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        try:
            created = create_plan_catalog_entry(connection, payload.model_dump())
        except Exception as exc:
            if is_integrity_error(exc):
                raise HTTPException(status_code=409, detail="Codigo do plano ja existe") from exc
            raise
        record_plan_creation_history(connection, plan=created, user_id=int(context["user_id"]))
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="saas_plan_created",
            payload={"plan_id": created["plan_id"], "code": created["code"], "name": created["name"]},
            user_id=int(context["user_id"]),
        )
    return created


@router.put("/saas/plans/{plan_id}")
def update_admin_saas_plan(plan_id: int, payload: SaasPlanCatalogPayload, context=Depends(get_session_context)) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        previous = get_plan_catalog_entry(connection, plan_id=plan_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Plano nao encontrado")
        try:
            updated = update_plan_catalog_entry(connection, plan_id=plan_id, payload=payload.model_dump())
        except Exception as exc:
            if is_integrity_error(exc):
                raise HTTPException(status_code=409, detail="Codigo do plano ja existe") from exc
            raise
        if not updated:
            raise HTTPException(status_code=404, detail="Plano nao encontrado")
        record_plan_update_history(
            connection,
            previous=previous,
            current=updated,
            user_id=int(context["user_id"]),
        )
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="saas_plan_updated",
            payload={"plan_id": updated["plan_id"], "code": updated["code"], "name": updated["name"]},
            user_id=int(context["user_id"]),
        )
    return updated


@router.put("/saas/subscriptions/{subscription_id}")
def update_admin_saas_subscription(
    subscription_id: int,
    payload: AdminSubscriptionUpdatePayload,
    context=Depends(get_session_context),
) -> dict[str, object]:
    _require_platform_admin(context)
    with get_connection() as connection:
        previous = get_admin_subscription_entry(connection, subscription_id=subscription_id)
        if not previous:
            raise HTTPException(status_code=404, detail="Assinatura nao encontrada")
        try:
            updated = update_admin_subscription_entry(
                connection,
                subscription_id=subscription_id,
                plan_id=payload.plan_id,
                status=payload.status,
                billing_cycle=payload.billing_cycle,
            )
        except LookupError as exc:
            if str(exc) == "plan_not_found":
                raise HTTPException(status_code=404, detail="Plano nao encontrado") from exc
            raise
        if not updated:
            raise HTTPException(status_code=404, detail="Assinatura nao encontrada")

        if int(previous["plan_id"]) != int(updated["plan_id"]):
            record_billing_event(
                connection,
                tenant_id=int(updated["tenant_id"]),
                subscription_id=int(updated["subscription_id"]),
                event_type="subscription_plan_changed",
                status="recorded",
                provider="internal",
                payload={
                    "from_plan_code": previous["plan_code"],
                    "to_plan_code": updated["plan_code"],
                },
            )
        if str(previous["status"]) != str(updated["status"]):
            record_billing_event(
                connection,
                tenant_id=int(updated["tenant_id"]),
                subscription_id=int(updated["subscription_id"]),
                event_type="subscription_status_changed",
                status="recorded",
                provider="internal",
                payload={"from_status": previous["status"], "to_status": updated["status"]},
            )
        record_audit_event(
            connection,
            tenant_id=int(updated["tenant_id"]),
            event_type="saas_subscription_updated",
            payload={
                "subscription_id": updated["subscription_id"],
                "from": {
                    "plan_id": previous["plan_id"],
                    "plan_code": previous["plan_code"],
                    "status": previous["status"],
                    "billing_cycle": previous["billing_cycle"],
                },
                "to": {
                    "plan_id": updated["plan_id"],
                    "plan_code": updated["plan_code"],
                    "status": updated["status"],
                    "billing_cycle": updated["billing_cycle"],
                },
            },
            user_id=int(context["user_id"]),
        )
        return updated