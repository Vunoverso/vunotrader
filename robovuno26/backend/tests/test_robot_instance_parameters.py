from __future__ import annotations

from datetime import datetime, timezone


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def login_and_prepare(client):
    email = unique_email("robot.params")
    password = "Senha123!"
    assert client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Robot Params"},
    ).status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200


def enable_demo_creation(client) -> None:
    parameters = client.get("/api/parameters").json()
    response = client.put(
        "/api/parameters",
        json={
            **parameters,
            "news_pause_enabled": True,
            "news_pause_symbols": "*",
            "performance_gate_enabled": True,
            "performance_gate_min_profit_factor": 1.3,
            "performance_gate_min_trades": 100,
            "validated_backtest_profit_factor": 1.55,
            "validated_backtest_trades": 180,
        },
    )
    assert response.status_code == 200


def test_robot_scoped_parameters_override_runtime_and_audit(client):
    login_and_prepare(client)
    enable_demo_creation(client)

    created = client.post(
        "/api/robot-instances",
        json={"name": "Robo Escopado", "mode": "DEMO", "primary_symbol": "EURUSD", "chart_timeframe": "M5"},
    )
    assert created.status_code == 200
    payload = created.json()
    robot_instance_id = payload["robot_instance_id"]
    robot_token = payload["token"]

    scoped_read = client.get("/api/parameters", params={"robot_instance_id": robot_instance_id})
    assert scoped_read.status_code == 200
    scoped_payload = scoped_read.json()
    assert scoped_payload["parameter_scope"] == "robot"
    assert scoped_payload["scope_robot_instance_id"] == robot_instance_id
    assert scoped_payload["scope_robot_name"] == "Robo Escopado"
    assert scoped_payload["scope_inherited"] is True

    scoped_save = client.put(
        "/api/parameters",
        params={"robot_instance_id": robot_instance_id},
        json={
            **scoped_payload,
            "decision_engine_mode": "PRICE_ACTION_ONLY",
            "operational_timeframe": "M15",
            "confirmation_timeframe": "H4",
            "stop_loss_points": 120,
            "take_profit_points": 260,
            "performance_gate_enabled": False,
        },
    )
    assert scoped_save.status_code == 200
    saved_payload = scoped_save.json()
    assert saved_payload["scope_inherited"] is False
    assert saved_payload["decision_engine_mode"] == "PRICE_ACTION_ONLY"
    assert saved_payload["operational_timeframe"] == "M15"
    assert saved_payload["confirmation_timeframe"] == "H4"
    assert saved_payload["stop_loss_points"] == 120
    assert saved_payload["take_profit_points"] == 260

    runtime_config = client.get(
        "/api/agent/runtime-config",
        headers={"X-Robot-Token": robot_token},
    )
    assert runtime_config.status_code == 200
    runtime_payload = runtime_config.json()
    assert runtime_payload["operational_timeframe"] == "M15"
    assert runtime_payload["confirmation_timeframe"] == "H4"
    assert runtime_payload["parameters"]["parameter_scope"] == "robot"
    assert runtime_payload["parameters"]["scope_robot_name"] == "Robo Escopado"
    assert runtime_payload["parameters"]["decision_engine_mode"] == "PRICE_ACTION_ONLY"
    assert runtime_payload["parameters"]["stop_loss_points"] == 120
    assert runtime_payload["parameters"]["take_profit_points"] == 260

    instances = client.get("/api/robot-instances")
    assert instances.status_code == 200
    current = next(item for item in instances.json() if item["robot_instance_id"] == robot_instance_id)
    assert current["operational_timeframe"] == "M15"
    assert current["confirmation_timeframe"] == "H4"

    audit = client.get("/api/audit-events", params={"event_type": "user_parameters_updated", "limit": 5})
    assert audit.status_code == 200
    latest = audit.json()[0]
    assert latest["robot_instance_id"] == robot_instance_id
    assert latest["robot_name"] == "Robo Escopado"


def test_delete_robot_instance_hides_listing_and_invalidates_token(client):
    login_and_prepare(client)
    enable_demo_creation(client)

    created = client.post(
        "/api/robot-instances",
        json={"name": "Robo Excluido", "mode": "DEMO"},
    )
    assert created.status_code == 200
    payload = created.json()
    robot_instance_id = payload["robot_instance_id"]
    robot_token = payload["token"]

    deleted = client.delete(f"/api/robot-instances/{robot_instance_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    instances = client.get("/api/robot-instances")
    assert instances.status_code == 200
    assert all(item["robot_instance_id"] != robot_instance_id for item in instances.json())

    runtime_config = client.get(
        "/api/agent/runtime-config",
        headers={"X-Robot-Token": robot_token},
    )
    assert runtime_config.status_code == 401

    audit = client.get("/api/audit-events", params={"event_type": "robot_instance_deleted", "limit": 5})
    assert audit.status_code == 200
    latest = audit.json()[0]
    assert latest["robot_instance_id"] == robot_instance_id
    assert latest["robot_name"] == "Robo Excluido"