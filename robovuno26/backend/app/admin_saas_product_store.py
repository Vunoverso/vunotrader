from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .deps import now_utc
from .subscription_store import DEFAULT_TRIAL_DAYS


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _serialize_admin_subscription(row) -> dict[str, object]:
    return {
        "subscription_id": int(row["id"]),
        "tenant_id": int(row["tenant_id"]),
        "tenant_name": str(row["tenant_name"]),
        "plan_id": int(row["plan_id"]),
        "plan_code": str(row["plan_code"]),
        "plan_name": str(row["plan_name"]),
        "status": str(row["status"]),
        "billing_cycle": str(row["billing_cycle"]),
        "current_period_start": str(row["current_period_start"]) if row["current_period_start"] else None,
        "current_period_end": str(row["current_period_end"]) if row["current_period_end"] else None,
        "trial_ends_at": str(row["trial_ends_at"]) if row["trial_ends_at"] else None,
        "users_total": int(row["users_total"] or 0),
        "active_robots": int(row["active_robots"] or 0),
        "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        "created_at": str(row["created_at"]),
    }


def list_admin_users(connection, *, limit: int = 80, search: str | None = None) -> list[dict[str, object]]:
    clauses = [
        """
        SELECT
            users.id,
            users.email,
            users.is_platform_admin,
            users.created_at,
            profiles.role,
            tenants.id AS tenant_id,
            tenants.name AS tenant_name,
            (
                SELECT sessions.created_at
                FROM sessions
                WHERE sessions.user_id = users.id
                ORDER BY sessions.created_at DESC
                LIMIT 1
            ) AS last_session_at,
            saas_subscriptions.id AS subscription_id,
            saas_subscriptions.status AS subscription_status,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name
        FROM users
        LEFT JOIN profiles ON profiles.user_id = users.id AND profiles.is_default = 1
        LEFT JOIN tenants ON tenants.id = profiles.tenant_id
        LEFT JOIN saas_subscriptions ON saas_subscriptions.id = (
            SELECT inner_sub.id
            FROM saas_subscriptions AS inner_sub
            WHERE inner_sub.tenant_id = tenants.id
            ORDER BY inner_sub.created_at DESC, inner_sub.id DESC
            LIMIT 1
        )
        LEFT JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        """
    ]
    params: list[object] = []
    if search:
        clauses.append("WHERE (LOWER(users.email) LIKE ? OR LOWER(COALESCE(tenants.name, '')) LIKE ?)")
        needle = f"%{search.lower()}%"
        params.extend([needle, needle])
    clauses.append("ORDER BY users.created_at DESC, users.id DESC LIMIT ?")
    params.append(limit)
    rows = connection.execute(" ".join(clauses), tuple(params)).fetchall()
    return [
        {
            "user_id": int(row["id"]),
            "email": str(row["email"]),
            "is_platform_admin": bool(row["is_platform_admin"]),
            "role": str(row["role"]) if row["role"] else None,
            "tenant_id": int(row["tenant_id"]) if row["tenant_id"] is not None else None,
            "tenant_name": str(row["tenant_name"]) if row["tenant_name"] else None,
            "subscription_id": int(row["subscription_id"]) if row["subscription_id"] is not None else None,
            "subscription_status": str(row["subscription_status"]) if row["subscription_status"] else None,
            "plan_code": str(row["plan_code"]) if row["plan_code"] else None,
            "plan_name": str(row["plan_name"]) if row["plan_name"] else None,
            "last_session_at": str(row["last_session_at"]) if row["last_session_at"] else None,
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def list_admin_subscriptions(
    connection,
    *,
    limit: int = 80,
    status: str | None = None,
    plan_id: int | None = None,
) -> list[dict[str, object]]:
    clauses = [
        """
        SELECT
            saas_subscriptions.id,
            saas_subscriptions.tenant_id,
            saas_subscriptions.plan_id,
            saas_subscriptions.status,
            saas_subscriptions.billing_cycle,
            saas_subscriptions.current_period_start,
            saas_subscriptions.current_period_end,
            saas_subscriptions.trial_ends_at,
            saas_subscriptions.updated_at,
            saas_subscriptions.created_at,
            tenants.name AS tenant_name,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name,
            (
                SELECT COUNT(*)
                FROM profiles
                WHERE profiles.tenant_id = saas_subscriptions.tenant_id
            ) AS users_total,
            (
                SELECT COUNT(*)
                FROM robot_instances
                WHERE robot_instances.tenant_id = saas_subscriptions.tenant_id
                    AND robot_instances.is_active = 1
            ) AS active_robots
        FROM saas_subscriptions
        JOIN tenants ON tenants.id = saas_subscriptions.tenant_id
        JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        WHERE saas_subscriptions.id = (
            SELECT inner_sub.id
            FROM saas_subscriptions AS inner_sub
            WHERE inner_sub.tenant_id = saas_subscriptions.tenant_id
            ORDER BY inner_sub.created_at DESC, inner_sub.id DESC
            LIMIT 1
        )
        """
    ]
    params: list[object] = []
    if status:
        clauses.append("AND saas_subscriptions.status = ?")
        params.append(status)
    if plan_id is not None:
        clauses.append("AND saas_subscriptions.plan_id = ?")
        params.append(plan_id)
    clauses.append("ORDER BY saas_subscriptions.updated_at DESC, saas_subscriptions.id DESC LIMIT ?")
    params.append(limit)
    rows = connection.execute(" ".join(clauses), tuple(params)).fetchall()
    return [_serialize_admin_subscription(row) for row in rows]


def get_admin_subscription_entry(connection, *, subscription_id: int) -> dict[str, object] | None:
    rows = connection.execute(
        """
        SELECT
            saas_subscriptions.id,
            saas_subscriptions.tenant_id,
            saas_subscriptions.plan_id,
            saas_subscriptions.status,
            saas_subscriptions.billing_cycle,
            saas_subscriptions.current_period_start,
            saas_subscriptions.current_period_end,
            saas_subscriptions.trial_ends_at,
            saas_subscriptions.updated_at,
            saas_subscriptions.created_at,
            tenants.name AS tenant_name,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name,
            (
                SELECT COUNT(*)
                FROM profiles
                WHERE profiles.tenant_id = saas_subscriptions.tenant_id
            ) AS users_total,
            (
                SELECT COUNT(*)
                FROM robot_instances
                WHERE robot_instances.tenant_id = saas_subscriptions.tenant_id
                    AND robot_instances.is_active = 1
            ) AS active_robots
        FROM saas_subscriptions
        JOIN tenants ON tenants.id = saas_subscriptions.tenant_id
        JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        WHERE saas_subscriptions.id = ?
        """,
        (subscription_id,),
    ).fetchone()
    return _serialize_admin_subscription(rows) if rows else None


def _build_period_end(reference: datetime, billing_cycle: str) -> str:
    horizon = 365 if billing_cycle == "yearly" else 30
    return (reference + timedelta(days=horizon)).isoformat()


def update_admin_subscription_entry(
    connection,
    *,
    subscription_id: int,
    plan_id: int,
    status: str,
    billing_cycle: str,
) -> dict[str, object] | None:
    existing = get_admin_subscription_entry(connection, subscription_id=subscription_id)
    if not existing:
        return None

    plan = connection.execute(
        "SELECT id FROM saas_plans WHERE id = ?",
        (plan_id,),
    ).fetchone()
    if not plan:
        raise LookupError("plan_not_found")

    now = now_utc()
    now_iso = now.isoformat()
    plan_changed = int(existing["plan_id"]) != int(plan_id)
    status_changed = str(existing["status"]) != status
    cycle_changed = str(existing["billing_cycle"]) != billing_cycle
    current_period_start = str(existing["current_period_start"] or now_iso)
    current_period_end = str(existing["current_period_end"] or _build_period_end(now, billing_cycle))
    trial_ends_at = str(existing["trial_ends_at"]) if existing["trial_ends_at"] else None

    if status == "trialing":
        if plan_changed or status_changed or cycle_changed or not _parse_iso_datetime(trial_ends_at):
            current_period_start = now_iso
            trial_ends_at = (now + timedelta(days=DEFAULT_TRIAL_DAYS)).isoformat()
            current_period_end = trial_ends_at
    elif status == "active":
        if plan_changed or status_changed or cycle_changed:
            current_period_start = now_iso
            current_period_end = _build_period_end(now, billing_cycle)
        trial_ends_at = None
    else:
        if status_changed and status != "trialing":
            trial_ends_at = None

    connection.execute(
        """
        UPDATE saas_subscriptions
        SET
            plan_id = ?,
            status = ?,
            billing_cycle = ?,
            current_period_start = ?,
            current_period_end = ?,
            trial_ends_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            plan_id,
            status,
            billing_cycle,
            current_period_start,
            current_period_end,
            trial_ends_at,
            now_iso,
            subscription_id,
        ),
    )
    return get_admin_subscription_entry(connection, subscription_id=subscription_id)