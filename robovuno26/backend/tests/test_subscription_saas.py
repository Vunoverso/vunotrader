from __future__ import annotations

import importlib
from datetime import datetime, timezone


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def register_and_login(client):
    email = unique_email("subscription.saas")
    password = "Senha123!"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Tenant SaaS"},
    )
    assert register.status_code == 200

    login = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return login.json()["user"]


def unlock_demo_creation(client) -> None:
    parameters = client.get("/api/parameters")
    assert parameters.status_code == 200
    updated = client.put(
        "/api/parameters",
        json={
            **parameters.json(),
            "market_session_guard_enabled": False,
            "news_pause_enabled": True,
            "news_pause_symbols": "*",
            "performance_gate_enabled": True,
            "performance_gate_min_profit_factor": 1.3,
            "performance_gate_min_trades": 100,
            "validated_backtest_profit_factor": 1.42,
            "validated_backtest_trades": 148,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["performance_gate_passed"] is True


def test_subscription_catalog_and_trial_access(client):
    user = register_and_login(client)

    plans = client.get("/api/subscription/plans")
    assert plans.status_code == 200
    plan_codes = [item["code"] for item in plans.json()]
    assert plan_codes == ["starter", "pro", "scale"]

    access = client.get("/api/subscription/access")
    assert access.status_code == 200
    payload = access.json()
    assert payload["tenant_id"] == user["tenant_id"]
    assert payload["status"] == "trialing"
    assert payload["plan_code"] == "starter"
    assert payload["plan_name"] == "Starter"
    assert payload["has_active_plan"] is False
    assert payload["is_trialing"] is True
    assert payload["trial_days_left"] >= 1


def test_subscription_access_reflects_active_status(client):
    user = register_and_login(client)

    database = importlib.import_module("app.database")
    with database.get_connection() as connection:
        connection.execute(
            """
            UPDATE saas_subscriptions
            SET status = ?, updated_at = ?, trial_ends_at = ?, current_period_end = ?
            WHERE tenant_id = ?
            """,
            (
                "active",
                datetime.now(timezone.utc).isoformat(),
                None,
                (datetime.now(timezone.utc)).isoformat(),
                int(user["tenant_id"]),
            ),
        )

    access = client.get("/api/subscription/access")
    assert access.status_code == 200
    payload = access.json()
    assert payload["status"] == "active"
    assert payload["has_active_plan"] is True
    assert payload["is_trialing"] is False
    assert payload["plan_code"] == "starter"


def test_subscription_limit_blocks_second_robot_instance(client):
    register_and_login(client)
    unlock_demo_creation(client)

    first = client.post(
        "/api/robot-instances",
        json={
            "name": "MT5 Demo 01",
            "mode": "DEMO",
            "broker_profile": "FOREX_GLOBAL",
            "primary_symbol": "EURUSD.a",
            "chart_timeframe": "M15",
            "selected_symbols": ["EURUSD.a"],
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/api/robot-instances",
        json={
            "name": "MT5 Demo 02",
            "mode": "DEMO",
            "broker_profile": "FOREX_GLOBAL",
            "primary_symbol": "USDCAD.a",
            "chart_timeframe": "M15",
            "selected_symbols": ["USDCAD.a"],
        },
    )
    assert second.status_code == 403
    assert "permite ate 1 robo" in second.json()["detail"]


def test_audit_requires_active_plan_and_releases_after_activation(client):
    user = register_and_login(client)

    blocked = client.get("/api/audit-events")
    assert blocked.status_code == 403
    assert "plano ativo" in blocked.json()["detail"]

    database = importlib.import_module("app.database")
    with database.get_connection() as connection:
        connection.execute(
            """
            UPDATE saas_subscriptions
            SET status = ?, updated_at = ?, trial_ends_at = ?
            WHERE tenant_id = ?
            """,
            (
                "active",
                datetime.now(timezone.utc).isoformat(),
                None,
                int(user["tenant_id"]),
            ),
        )

    released = client.get("/api/audit-events")
    assert released.status_code == 200
    assert any(item["event_type"] == "saas_feature_blocked" for item in released.json())