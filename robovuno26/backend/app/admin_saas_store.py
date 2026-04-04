from __future__ import annotations

import os

from .deps import now_utc


def should_auto_grant_platform_admin(email: str) -> bool:
    raw = os.getenv("PLATFORM_ADMIN_EMAILS", "")
    allowed = {item.strip().lower() for item in raw.split(",") if item.strip()}
    return str(email or "").strip().lower() in allowed


def count_platform_admins(connection) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS total FROM users WHERE is_platform_admin = 1"
    ).fetchone()
    return int(row["total"] or 0)


def build_platform_admin_bootstrap_status(connection, *, is_platform_admin: bool, app_env: str) -> dict[str, object]:
    admin_count = count_platform_admins(connection)
    if is_platform_admin:
        return {
            "is_platform_admin": True,
            "can_bootstrap": False,
            "reason": "already_admin",
            "admin_count": admin_count,
        }
    if str(app_env).lower() != "development":
        return {
            "is_platform_admin": False,
            "can_bootstrap": False,
            "reason": "disabled_outside_development",
            "admin_count": admin_count,
        }
    if admin_count > 0:
        return {
            "is_platform_admin": False,
            "can_bootstrap": False,
            "reason": "admin_already_exists",
            "admin_count": admin_count,
        }
    return {
        "is_platform_admin": False,
        "can_bootstrap": True,
        "reason": "available",
        "admin_count": admin_count,
    }


def bootstrap_platform_admin(connection, *, user_id: int) -> None:
    connection.execute(
        "UPDATE users SET is_platform_admin = 1 WHERE id = ?",
        (user_id,),
    )


def list_plan_catalog(connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            saas_plans.id,
            saas_plans.code,
            saas_plans.name,
            saas_plans.description,
            saas_plans.monthly_price,
            saas_plans.yearly_price,
            saas_plans.is_active,
            saas_plan_limits.max_users,
            saas_plan_limits.max_trades_per_month,
            saas_plan_limits.max_ai_tokens_per_day,
            saas_plan_limits.max_storage_gb,
            saas_plan_limits.max_bots
        FROM saas_plans
        LEFT JOIN saas_plan_limits ON saas_plan_limits.plan_id = saas_plans.id
        ORDER BY saas_plans.monthly_price ASC, saas_plans.id ASC
        """
    ).fetchall()
    return [
        {
            "plan_id": int(row["id"]),
            "code": str(row["code"]),
            "name": str(row["name"]),
            "description": str(row["description"]) if row["description"] else None,
            "monthly_price": float(row["monthly_price"]),
            "yearly_price": float(row["yearly_price"]) if row["yearly_price"] is not None else None,
            "is_active": bool(row["is_active"]),
            "max_users": int(row["max_users"]) if row["max_users"] is not None else None,
            "max_trades_per_month": int(row["max_trades_per_month"]) if row["max_trades_per_month"] is not None else None,
            "max_ai_tokens_per_day": int(row["max_ai_tokens_per_day"]) if row["max_ai_tokens_per_day"] is not None else None,
            "max_storage_gb": float(row["max_storage_gb"]) if row["max_storage_gb"] is not None else None,
            "max_bots": int(row["max_bots"]) if row["max_bots"] is not None else None,
        }
        for row in rows
    ]


def get_plan_catalog_entry(connection, *, plan_id: int) -> dict[str, object] | None:
    for item in list_plan_catalog(connection):
        if int(item["plan_id"]) == int(plan_id):
            return item
    return None


def _upsert_plan_limits(connection, *, plan_id: int, payload: dict[str, object], created_at: str) -> None:
    existing = connection.execute(
        "SELECT id FROM saas_plan_limits WHERE plan_id = ?",
        (plan_id,),
    ).fetchone()
    values = (
        payload.get("max_users"),
        payload.get("max_trades_per_month"),
        payload.get("max_ai_tokens_per_day"),
        payload.get("max_storage_gb"),
        payload.get("max_bots"),
    )
    if existing:
        connection.execute(
            """
            UPDATE saas_plan_limits
            SET
                max_users = ?,
                max_trades_per_month = ?,
                max_ai_tokens_per_day = ?,
                max_storage_gb = ?,
                max_bots = ?
            WHERE plan_id = ?
            """,
            (*values, plan_id),
        )
        return
    connection.execute(
        """
        INSERT INTO saas_plan_limits (
            plan_id,
            max_users,
            max_trades_per_month,
            max_ai_tokens_per_day,
            max_storage_gb,
            max_bots,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (plan_id, *values, created_at),
    )


def create_plan_catalog_entry(connection, payload: dict[str, object]) -> dict[str, object]:
    created_at = now_utc().isoformat()
    cursor = connection.execute(
        """
        INSERT INTO saas_plans (
            code,
            name,
            description,
            monthly_price,
            yearly_price,
            is_active,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["code"],
            payload["name"],
            payload.get("description"),
            payload["monthly_price"],
            payload.get("yearly_price"),
            1 if payload["is_active"] else 0,
            created_at,
        ),
    )
    plan_id = int(cursor.lastrowid)
    _upsert_plan_limits(connection, plan_id=plan_id, payload=payload, created_at=created_at)
    return next(item for item in list_plan_catalog(connection) if int(item["plan_id"]) == plan_id)


def update_plan_catalog_entry(connection, *, plan_id: int, payload: dict[str, object]) -> dict[str, object] | None:
    existing = connection.execute(
        "SELECT id FROM saas_plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
    if not existing:
        return None
    connection.execute(
        """
        UPDATE saas_plans
        SET
            code = ?,
            name = ?,
            description = ?,
            monthly_price = ?,
            yearly_price = ?,
            is_active = ?
        WHERE id = ?
        """,
        (
            payload["code"],
            payload["name"],
            payload.get("description"),
            payload["monthly_price"],
            payload.get("yearly_price"),
            1 if payload["is_active"] else 0,
            plan_id,
        ),
    )
    _upsert_plan_limits(connection, plan_id=plan_id, payload=payload, created_at=now_utc().isoformat())
    return next(item for item in list_plan_catalog(connection) if int(item["plan_id"]) == plan_id)


def build_admin_overview(connection) -> dict[str, object]:
    tenants_row = connection.execute("SELECT COUNT(*) AS total FROM tenants").fetchone()
    plans = list_plan_catalog(connection)
    subscription_rows = connection.execute(
        """
        SELECT
            saas_subscriptions.id,
            saas_subscriptions.tenant_id,
            saas_subscriptions.status,
            saas_subscriptions.billing_cycle,
            saas_subscriptions.current_period_end,
            saas_subscriptions.trial_ends_at,
            saas_subscriptions.created_at,
            tenants.name AS tenant_name,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name,
            saas_plans.monthly_price,
            saas_plans.yearly_price
        FROM saas_subscriptions
        JOIN tenants ON tenants.id = saas_subscriptions.tenant_id
        JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        ORDER BY saas_subscriptions.created_at DESC, saas_subscriptions.id DESC
        """
    ).fetchall()
    active_subscriptions = [row for row in subscription_rows if str(row["status"]) == "active"]
    trialing_subscriptions = [row for row in subscription_rows if str(row["status"]) == "trialing"]
    estimated_mrr = 0.0
    for row in active_subscriptions:
        yearly_price = float(row["yearly_price"]) if row["yearly_price"] is not None else None
        monthly_price = float(row["monthly_price"])
        estimated_mrr += (yearly_price / 12.0) if str(row["billing_cycle"]) == "yearly" and yearly_price else monthly_price
    return {
        "metrics": {
            "tenants_total": int(tenants_row["total"] or 0),
            "plans_total": len(plans),
            "plans_active": sum(1 for item in plans if item["is_active"]),
            "subscriptions_total": len(subscription_rows),
            "subscriptions_active": len(active_subscriptions),
            "subscriptions_trialing": len(trialing_subscriptions),
            "estimated_mrr": round(estimated_mrr, 2),
        },
        "recent_subscriptions": [
            {
                "subscription_id": int(row["id"]),
                "tenant_id": int(row["tenant_id"]),
                "tenant_name": str(row["tenant_name"]),
                "plan_code": str(row["plan_code"]),
                "plan_name": str(row["plan_name"]),
                "status": str(row["status"]),
                "billing_cycle": str(row["billing_cycle"]),
                "current_period_end": str(row["current_period_end"]) if row["current_period_end"] else None,
                "trial_ends_at": str(row["trial_ends_at"]) if row["trial_ends_at"] else None,
                "created_at": str(row["created_at"]),
            }
            for row in subscription_rows[:12]
        ],
    }