from __future__ import annotations

import math
import os
from datetime import datetime, timedelta

from .deps import now_utc


DEFAULT_TRIAL_PLAN_CODE = (os.getenv("DEFAULT_TRIAL_PLAN_CODE", "starter").strip().lower() or "starter")
DEFAULT_TRIAL_DAYS = max(1, int(os.getenv("DEFAULT_TRIAL_DAYS", "7")))


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _serialize_plan(row) -> dict[str, object]:
    return {
        "plan_id": int(row["id"]),
        "code": str(row["code"]),
        "name": str(row["name"]),
        "description": str(row["description"]) if row["description"] else None,
        "monthly_price": float(row["monthly_price"]),
        "yearly_price": float(row["yearly_price"]) if row["yearly_price"] is not None else None,
        "is_active": bool(row["is_active"]),
    }


def list_saas_plans(connection, *, active_only: bool = True) -> list[dict[str, object]]:
    clauses = ["SELECT id, code, name, description, monthly_price, yearly_price, is_active FROM saas_plans"]
    params: list[object] = []
    if active_only:
        clauses.append("WHERE is_active = ?")
        params.append(1)
    clauses.append("ORDER BY monthly_price ASC, id ASC")
    rows = connection.execute(" ".join(clauses), tuple(params)).fetchall()
    return [_serialize_plan(row) for row in rows]


def _load_latest_subscription_row(connection, tenant_id: int):
    return connection.execute(
        """
        SELECT
            saas_subscriptions.id,
            saas_subscriptions.plan_id,
            saas_subscriptions.status,
            saas_subscriptions.billing_cycle,
            saas_subscriptions.current_period_start,
            saas_subscriptions.current_period_end,
            saas_subscriptions.trial_ends_at,
            saas_subscriptions.created_at,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name,
            saas_plan_limits.max_users,
            saas_plan_limits.max_trades_per_month,
            saas_plan_limits.max_ai_tokens_per_day,
            saas_plan_limits.max_storage_gb,
            saas_plan_limits.max_bots
        FROM saas_subscriptions
        JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        LEFT JOIN saas_plan_limits ON saas_plan_limits.plan_id = saas_subscriptions.plan_id
        WHERE saas_subscriptions.tenant_id = ?
        ORDER BY saas_subscriptions.created_at DESC, saas_subscriptions.id DESC
        LIMIT 1
        """,
        (tenant_id,),
    ).fetchone()


def _serialize_limits(row) -> dict[str, object]:
    return {
        "max_users": int(row["max_users"]) if row["max_users"] is not None else None,
        "max_trades_per_month": int(row["max_trades_per_month"]) if row["max_trades_per_month"] is not None else None,
        "max_ai_tokens_per_day": int(row["max_ai_tokens_per_day"]) if row["max_ai_tokens_per_day"] is not None else None,
        "max_storage_gb": float(row["max_storage_gb"]) if row["max_storage_gb"] is not None else None,
        "max_bots": int(row["max_bots"]) if row["max_bots"] is not None else None,
    }


def ensure_default_trial_subscription(
    connection,
    *,
    tenant_id: int,
    created_at: str,
) -> dict[str, object] | None:
    existing = _load_latest_subscription_row(connection, tenant_id)
    if existing:
        return None

    plan = connection.execute(
        """
        SELECT id, code, name
        FROM saas_plans
        WHERE lower(code) = ? AND is_active = ?
        ORDER BY id ASC
        LIMIT 1
        """,
        (DEFAULT_TRIAL_PLAN_CODE, 1),
    ).fetchone()
    if not plan:
        plan = connection.execute(
            """
            SELECT id, code, name
            FROM saas_plans
            WHERE is_active = ?
            ORDER BY monthly_price ASC, id ASC
            LIMIT 1
            """,
            (1,),
        ).fetchone()
    if not plan:
        return None

    started_at = _parse_iso_datetime(created_at) or now_utc()
    trial_ends_at = started_at + timedelta(days=DEFAULT_TRIAL_DAYS)
    now_iso = started_at.isoformat()
    trial_end_iso = trial_ends_at.isoformat()

    cursor = connection.execute(
        """
        INSERT INTO saas_subscriptions (
            tenant_id,
            plan_id,
            status,
            billing_cycle,
            current_period_start,
            current_period_end,
            trial_ends_at,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            int(plan["id"]),
            "trialing",
            "monthly",
            now_iso,
            trial_end_iso,
            trial_end_iso,
            now_iso,
            now_iso,
        ),
    )

    return {
        "subscription_id": int(cursor.lastrowid),
        "plan_id": int(plan["id"]),
        "plan_code": str(plan["code"]),
        "plan_name": str(plan["name"]),
        "status": "trialing",
        "trial_ends_at": trial_end_iso,
        "trial_days": DEFAULT_TRIAL_DAYS,
    }


def build_subscription_access(connection, tenant_id: int) -> dict[str, object]:
    row = _load_latest_subscription_row(connection, tenant_id)
    if not row:
        return {
            "tenant_id": tenant_id,
            "has_active_plan": False,
            "is_trialing": False,
            "trial_days_left": 0,
            "status": "none",
            "plan_code": None,
            "plan_name": None,
            "billing_cycle": None,
            "current_period_start": None,
            "current_period_end": None,
            "trial_ends_at": None,
        }

    now = now_utc()
    trial_ends_at = _parse_iso_datetime(str(row["trial_ends_at"]) if row["trial_ends_at"] else None)
    trial_days_left = 0
    if trial_ends_at and trial_ends_at > now:
        trial_days_left = max(0, math.ceil((trial_ends_at - now).total_seconds() / 86400))

    status = str(row["status"])
    return {
        "tenant_id": tenant_id,
        "has_active_plan": status == "active",
        "is_trialing": status == "trialing" and trial_days_left > 0,
        "trial_days_left": trial_days_left,
        "status": status,
        "plan_code": str(row["plan_code"]) if row["plan_code"] else None,
        "plan_name": str(row["plan_name"]) if row["plan_name"] else None,
        "billing_cycle": str(row["billing_cycle"]) if row["billing_cycle"] else None,
        "current_period_start": str(row["current_period_start"]) if row["current_period_start"] else None,
        "current_period_end": str(row["current_period_end"]) if row["current_period_end"] else None,
        "trial_ends_at": str(row["trial_ends_at"]) if row["trial_ends_at"] else None,
    }


def build_subscription_entitlements(connection, tenant_id: int) -> dict[str, object]:
    row = _load_latest_subscription_row(connection, tenant_id)
    access = build_subscription_access(connection, tenant_id)
    if not row:
        access["plan_id"] = None
        access["limits"] = {
            "max_users": None,
            "max_trades_per_month": None,
            "max_ai_tokens_per_day": None,
            "max_storage_gb": None,
            "max_bots": None,
        }
        return access

    access["plan_id"] = int(row["plan_id"])
    access["limits"] = _serialize_limits(row)
    return access