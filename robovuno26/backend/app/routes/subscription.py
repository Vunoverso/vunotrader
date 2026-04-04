from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..deps import get_session_context
from ..database import get_connection
from ..subscription_store import build_subscription_access, list_saas_plans


router = APIRouter(prefix="/api/subscription", tags=["subscription"])


class SaasPlanResponse(BaseModel):
    plan_id: int
    code: str
    name: str
    description: str | None = None
    monthly_price: float
    yearly_price: float | None = None
    is_active: bool


class SubscriptionAccessResponse(BaseModel):
    tenant_id: int
    has_active_plan: bool
    is_trialing: bool
    trial_days_left: int
    status: str
    plan_code: str | None = None
    plan_name: str | None = None
    billing_cycle: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    trial_ends_at: str | None = None


@router.get("/plans", response_model=list[SaasPlanResponse])
def read_saas_plans() -> list[SaasPlanResponse]:
    with get_connection() as connection:
        plans = list_saas_plans(connection, active_only=True)
    return [SaasPlanResponse(**plan) for plan in plans]


@router.get("/access", response_model=SubscriptionAccessResponse)
def read_subscription_access(context=Depends(get_session_context)) -> SubscriptionAccessResponse:
    tenant_id = int(context["tenant_id"])
    with get_connection() as connection:
        payload = build_subscription_access(connection, tenant_id)
    return SubscriptionAccessResponse(**payload)