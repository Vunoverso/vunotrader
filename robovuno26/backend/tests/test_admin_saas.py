from __future__ import annotations

from datetime import datetime, timezone


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def register_and_login(client):
    email = unique_email("admin.saas")
    password = "Senha123!"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Tenant Admin SaaS"},
    )
    assert register.status_code == 200
    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["user"]


def test_admin_saas_bootstrap_and_catalog_management(client):
    user = register_and_login(client)
    assert user["is_platform_admin"] is False

    bootstrap_status = client.get("/api/admin/bootstrap-status")
    assert bootstrap_status.status_code == 200
    assert bootstrap_status.json()["can_bootstrap"] is True

    bootstrap = client.post("/api/admin/bootstrap-platform-admin")
    assert bootstrap.status_code == 200
    assert bootstrap.json()["is_platform_admin"] is True

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["is_platform_admin"] is True

    overview = client.get("/api/admin/saas/overview")
    assert overview.status_code == 200
    assert overview.json()["metrics"]["plans_total"] >= 3
    assert overview.json()["metrics"]["subscriptions_trialing"] >= 1

    plans = client.get("/api/admin/saas/plans")
    assert plans.status_code == 200
    assert any(item["code"] == "starter" for item in plans.json())
    pro_plan_id = next(item["plan_id"] for item in plans.json() if item["code"] == "pro")

    created = client.post(
        "/api/admin/saas/plans",
        json={
            "code": "elite",
            "name": "Elite",
            "description": "Plano premium local.",
            "monthly_price": 999.0,
            "yearly_price": 9990.0,
            "is_active": True,
            "max_users": 20,
            "max_trades_per_month": 50000,
            "max_ai_tokens_per_day": 2000000,
            "max_storage_gb": 50.0,
            "max_bots": 25,
        },
    )
    assert created.status_code == 200
    plan_id = created.json()["plan_id"]
    assert created.json()["code"] == "elite"
    assert created.json()["max_bots"] == 25

    updated = client.put(
        f"/api/admin/saas/plans/{plan_id}",
        json={
            "code": "elite",
            "name": "Elite Plus",
            "description": "Plano premium atualizado.",
            "monthly_price": 1099.0,
            "yearly_price": 10990.0,
            "is_active": False,
            "max_users": 30,
            "max_trades_per_month": 70000,
            "max_ai_tokens_per_day": 2500000,
            "max_storage_gb": 80.0,
            "max_bots": 40,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Elite Plus"
    assert updated.json()["is_active"] is False
    assert updated.json()["max_users"] == 30

    changes = client.get(f"/api/admin/saas/plan-changes?plan_id={plan_id}")
    assert changes.status_code == 200
    rows = changes.json()["changes"]
    assert any(item["change_type"] == "plan_created" for item in rows)
    assert any(item["change_type"] == "price_update" and item["field_name"] == "monthly_price" for item in rows)
    assert any(item["change_type"] == "limit_update" and item["field_name"] == "max_bots" for item in rows)
    assert any(item["change_type"] == "status_change" and item["field_name"] == "is_active" for item in rows)

    billing = client.get("/api/admin/saas/billing")
    assert billing.status_code == 200
    assert billing.json()["metrics"]["total_events"] >= 1
    assert any(item["event_type"] == "subscription_created" for item in billing.json()["events"])

    users = client.get("/api/admin/saas/users")
    assert users.status_code == 200
    assert any(item["email"] == user["email"] for item in users.json()["users"])

    subscriptions = client.get("/api/admin/saas/subscriptions")
    assert subscriptions.status_code == 200
    managed_subscription = next(item for item in subscriptions.json()["subscriptions"] if item["tenant_id"] == user["tenant_id"])

    updated_subscription = client.put(
        f"/api/admin/saas/subscriptions/{managed_subscription['subscription_id']}",
        json={"plan_id": pro_plan_id, "status": "active", "billing_cycle": "yearly"},
    )
    assert updated_subscription.status_code == 200
    assert updated_subscription.json()["plan_code"] == "pro"
    assert updated_subscription.json()["status"] == "active"
    assert updated_subscription.json()["billing_cycle"] == "yearly"

    billing_after_update = client.get("/api/admin/saas/billing")
    assert billing_after_update.status_code == 200
    assert any(item["event_type"] == "subscription_plan_changed" for item in billing_after_update.json()["events"])
    assert any(item["event_type"] == "subscription_status_changed" for item in billing_after_update.json()["events"])


def test_admin_saas_routes_require_platform_admin(client):
    register_and_login(client)
    overview = client.get("/api/admin/saas/overview")
    assert overview.status_code == 403
    plan_changes = client.get("/api/admin/saas/plan-changes")
    assert plan_changes.status_code == 403
    billing = client.get("/api/admin/saas/billing")
    assert billing.status_code == 403
    users = client.get("/api/admin/saas/users")
    assert users.status_code == 403
    subscriptions = client.get("/api/admin/saas/subscriptions")
    assert subscriptions.status_code == 403