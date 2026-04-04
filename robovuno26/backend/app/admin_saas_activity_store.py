from __future__ import annotations

import json

from .deps import now_utc


PRICE_FIELDS = ("monthly_price", "yearly_price")
LIMIT_FIELDS = (
    "max_users",
    "max_trades_per_month",
    "max_ai_tokens_per_day",
    "max_storage_gb",
    "max_bots",
)
METADATA_FIELDS = ("code", "name", "description")


def _stringify(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return (f"{value:.10f}").rstrip("0").rstrip(".") or "0"
    return str(value)


def record_plan_change(
    connection,
    *,
    plan_id: int,
    change_type: str,
    field_name: str,
    new_value,
    old_value=None,
    user_id: int | None = None,
    created_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO plan_changes (
            plan_id,
            change_type,
            field_name,
            old_value,
            new_value,
            changed_by,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan_id,
            change_type,
            field_name,
            _stringify(old_value),
            _stringify(new_value) or "",
            user_id,
            created_at or now_utc().isoformat(),
        ),
    )


def record_plan_creation_history(connection, *, plan: dict[str, object], user_id: int) -> None:
    plan_id = int(plan["plan_id"])
    created_at = now_utc().isoformat()
    record_plan_change(
        connection,
        plan_id=plan_id,
        change_type="plan_created",
        field_name="name",
        new_value=plan.get("name"),
        user_id=user_id,
        created_at=created_at,
    )
    for field_name in PRICE_FIELDS:
        if plan.get(field_name) is not None:
            record_plan_change(
                connection,
                plan_id=plan_id,
                change_type="price_update",
                field_name=field_name,
                new_value=plan.get(field_name),
                user_id=user_id,
                created_at=created_at,
            )
    for field_name in LIMIT_FIELDS:
        if plan.get(field_name) is not None:
            record_plan_change(
                connection,
                plan_id=plan_id,
                change_type="limit_update",
                field_name=field_name,
                new_value=plan.get(field_name),
                user_id=user_id,
                created_at=created_at,
            )


def record_plan_update_history(
    connection,
    *,
    previous: dict[str, object],
    current: dict[str, object],
    user_id: int,
) -> None:
    plan_id = int(current["plan_id"])
    created_at = now_utc().isoformat()
    tracked_fields = [("metadata_update", METADATA_FIELDS), ("price_update", PRICE_FIELDS), ("limit_update", LIMIT_FIELDS)]
    for change_type, field_names in tracked_fields:
        for field_name in field_names:
            if _stringify(previous.get(field_name)) == _stringify(current.get(field_name)):
                continue
            record_plan_change(
                connection,
                plan_id=plan_id,
                change_type=change_type,
                field_name=field_name,
                old_value=previous.get(field_name),
                new_value=current.get(field_name),
                user_id=user_id,
                created_at=created_at,
            )
    if bool(previous.get("is_active")) != bool(current.get("is_active")):
        record_plan_change(
            connection,
            plan_id=plan_id,
            change_type="status_change",
            field_name="is_active",
            old_value=previous.get("is_active"),
            new_value=current.get("is_active"),
            user_id=user_id,
            created_at=created_at,
        )


def list_plan_change_history(connection, *, limit: int = 50, plan_id: int | None = None) -> list[dict[str, object]]:
    clauses = [
        """
        SELECT
            plan_changes.id,
            plan_changes.plan_id,
            plan_changes.change_type,
            plan_changes.field_name,
            plan_changes.old_value,
            plan_changes.new_value,
            plan_changes.changed_by,
            plan_changes.created_at,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name,
            users.email AS changed_by_email
        FROM plan_changes
        JOIN saas_plans ON saas_plans.id = plan_changes.plan_id
        LEFT JOIN users ON users.id = plan_changes.changed_by
        """
    ]
    params: list[object] = []
    if plan_id is not None:
        clauses.append("WHERE plan_changes.plan_id = ?")
        params.append(plan_id)
    clauses.append("ORDER BY plan_changes.created_at DESC, plan_changes.id DESC LIMIT ?")
    params.append(limit)
    rows = connection.execute(" ".join(clauses), tuple(params)).fetchall()
    return [
        {
            "change_id": int(row["id"]),
            "plan_id": int(row["plan_id"]),
            "plan_code": str(row["plan_code"]),
            "plan_name": str(row["plan_name"]),
            "change_type": str(row["change_type"]),
            "field_name": str(row["field_name"]),
            "old_value": str(row["old_value"]) if row["old_value"] is not None else None,
            "new_value": str(row["new_value"]),
            "changed_by": int(row["changed_by"]) if row["changed_by"] is not None else None,
            "changed_by_email": str(row["changed_by_email"]) if row["changed_by_email"] else None,
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]


def record_billing_event(
    connection,
    *,
    tenant_id: int,
    subscription_id: int | None,
    event_type: str,
    amount: float = 0.0,
    currency: str = "BRL",
    status: str = "recorded",
    provider: str = "internal",
    provider_event_id: str | None = None,
    payload: dict[str, object] | None = None,
    created_at: str | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO billing_events (
            subscription_id,
            tenant_id,
            event_type,
            amount,
            currency,
            status,
            provider,
            provider_event_id,
            payload,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subscription_id,
            tenant_id,
            event_type,
            float(amount or 0.0),
            currency,
            status,
            provider,
            provider_event_id,
            json.dumps(payload, ensure_ascii=True, sort_keys=True) if payload is not None else None,
            created_at or now_utc().isoformat(),
        ),
    )


def build_billing_overview(
    connection,
    *,
    limit: int = 50,
    status: str | None = None,
    provider: str | None = None,
) -> dict[str, object]:
    clauses = [
        """
        SELECT
            billing_events.id,
            billing_events.subscription_id,
            billing_events.tenant_id,
            billing_events.event_type,
            billing_events.amount,
            billing_events.currency,
            billing_events.status,
            billing_events.provider,
            billing_events.provider_event_id,
            billing_events.created_at,
            tenants.name AS tenant_name,
            saas_subscriptions.billing_cycle,
            saas_subscriptions.status AS subscription_status,
            saas_plans.code AS plan_code,
            saas_plans.name AS plan_name
        FROM billing_events
        LEFT JOIN tenants ON tenants.id = billing_events.tenant_id
        LEFT JOIN saas_subscriptions ON saas_subscriptions.id = billing_events.subscription_id
        LEFT JOIN saas_plans ON saas_plans.id = saas_subscriptions.plan_id
        """
    ]
    conditions: list[str] = []
    params: list[object] = []
    if status:
        conditions.append("billing_events.status = ?")
        params.append(status)
    if provider:
        conditions.append("LOWER(billing_events.provider) = ?")
        params.append(provider.lower())
    if conditions:
        clauses.append("WHERE " + " AND ".join(conditions))
    clauses.append("ORDER BY billing_events.created_at DESC, billing_events.id DESC LIMIT ?")
    params.append(limit)
    rows = connection.execute(" ".join(clauses), tuple(params)).fetchall()

    events = [
        {
            "event_id": int(row["id"]),
            "subscription_id": int(row["subscription_id"]) if row["subscription_id"] is not None else None,
            "tenant_id": int(row["tenant_id"]),
            "tenant_name": str(row["tenant_name"]) if row["tenant_name"] else None,
            "event_type": str(row["event_type"]),
            "amount": float(row["amount"] or 0.0),
            "currency": str(row["currency"]),
            "status": str(row["status"]),
            "provider": str(row["provider"]),
            "provider_event_id": str(row["provider_event_id"]) if row["provider_event_id"] else None,
            "billing_cycle": str(row["billing_cycle"]) if row["billing_cycle"] else None,
            "subscription_status": str(row["subscription_status"]) if row["subscription_status"] else None,
            "plan_code": str(row["plan_code"]) if row["plan_code"] else None,
            "plan_name": str(row["plan_name"]) if row["plan_name"] else None,
            "created_at": str(row["created_at"]),
        }
        for row in rows
    ]
    return {
        "metrics": {
            "total_events": len(events),
            "trial_events": sum(1 for item in events if item["event_type"] == "subscription_created"),
            "successful_charges": round(sum(item["amount"] for item in events if item["event_type"] == "charge_succeeded"), 2),
            "failed_charges": round(sum(item["amount"] for item in events if item["event_type"] == "charge_failed"), 2),
            "refunds": round(sum(item["amount"] for item in events if item["event_type"] == "refund_issued"), 2),
            "net_revenue": round(
                sum(item["amount"] for item in events if item["event_type"] == "charge_succeeded")
                - sum(item["amount"] for item in events if item["event_type"] == "refund_issued"),
                2,
            ),
            "providers_total": len({item["provider"] for item in events if item["provider"]}),
        },
        "providers": sorted({item["provider"] for item in events if item["provider"]}),
        "events": events,
    }