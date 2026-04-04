from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def test_demo_instance_agent_flow_and_summary(client):
    email = unique_email("flow.demo")
    password = "Senha123!"

    profiles_resp = client.get("/api/instrument-profiles")
    assert profiles_resp.status_code == 200
    assert any(item["profile_id"] == "B3_FUTURES" for item in profiles_resp.json())

    register_resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Flow Demo"},
    )
    assert register_resp.status_code == 200

    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200

    parameters_resp = client.get("/api/parameters")
    assert parameters_resp.status_code == 200
    assert parameters_resp.json()["reentry_cooldown_seconds"] == 60

    updated_parameters_resp = client.put(
        "/api/parameters",
        json={
            **parameters_resp.json(),
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
    assert updated_parameters_resp.status_code == 200
    assert updated_parameters_resp.json()["performance_gate_passed"] is True

    create_instance = client.post(
        "/api/robot-instances",
        json={
            "name": "MT5 Demo 01",
            "mode": "DEMO",
            "broker_profile": "FOREX_GLOBAL",
            "primary_symbol": "EURUSD.a",
            "chart_timeframe": "M15",
            "selected_symbols": ["EURUSD.a", "USDCAD.a"],
        },
    )
    assert create_instance.status_code == 200
    instance_payload = create_instance.json()
    robot_instance_id = instance_payload["robot_instance_id"]
    robot_token = instance_payload["token"]
    assert instance_payload["broker_profile"] == "FOREX_GLOBAL"
    assert instance_payload["primary_symbol"] == "EURUSD.a"
    assert instance_payload["chart_timeframe"] == "M15"
    assert instance_payload["selected_symbols"] == ["EURUSD.a", "USDCAD.a"]
    assert instance_payload["bridge_name"] == f"VunoBridge-{robot_instance_id}"

    runtime_config_resp = client.get(
        "/api/agent/runtime-config",
        headers={"X-Robot-Token": robot_token},
    )
    assert runtime_config_resp.status_code == 200
    assert runtime_config_resp.json()["parameters"]["reentry_cooldown_seconds"] == 60
    assert runtime_config_resp.json()["parameters"]["decision_engine_mode"] == "HYBRID"
    assert runtime_config_resp.json()["parameters"]["market_session_guard_enabled"] is False
    assert runtime_config_resp.json()["runtime_pause_new_orders"] is False
    assert runtime_config_resp.json()["operational_timeframe"] == "M5"
    assert runtime_config_resp.json()["confirmation_timeframe"] == "H1"

    package_resp = client.get(f"/api/robot-instances/{robot_instance_id}/agent-package")
    assert package_resp.status_code == 200
    assert package_resp.headers["content-type"] == "application/zip"
    assert ".zip" in package_resp.headers.get("content-disposition", "")

    with zipfile.ZipFile(io.BytesIO(package_resp.content)) as archive:
        names = set(archive.namelist())
        assert "vuno-robo/agent-local/iniciar-vuno-robo.cmd" in names
        assert "vuno-robo/mt5/VunoRemoteBridge.mq5" in names

        binary_path = Path(__file__).resolve().parents[2] / "agent-local" / "dist" / "vuno-agent.exe"
        if binary_path.exists():
            assert "vuno-robo/agent-local/dist/vuno-agent.exe" in names

        runtime_config = json.loads(
            archive.read("vuno-robo/agent-local/runtime/config.json").decode("utf-8")
        )
        assert runtime_config["robot_token"] == robot_token
        assert runtime_config["backend_url"] == "http://testserver"
        assert runtime_config["bridge_name"] == instance_payload["bridge_name"]
        assert runtime_config["broker_profile"] == "FOREX_GLOBAL"
        assert runtime_config["primary_symbol"] == "EURUSD.a"
        assert runtime_config["chart_timeframe"] == "M15"
        assert runtime_config["selected_symbols"] == ["EURUSD.a", "USDCAD.a"]
        assert runtime_config["metadata_dir"] == "runtime/bridge/metadata"

        quick_start = archive.read("vuno-robo/LEIA-PRIMEIRO.txt").decode("utf-8")
        assert instance_payload["bridge_name"] in quick_start
        assert "EURUSD.a" in quick_start
        assert "M15" in quick_start
        assert "USDCAD.a" in quick_start

    now_iso = datetime.now(timezone.utc).isoformat()
    heartbeat_resp = client.post(
        "/api/agent/heartbeat",
        headers={"X-Robot-Token": robot_token},
        json={
            "status": "ACTIVE",
            "observed_at": now_iso,
            "details": {
                "source": "pytest",
                "agent_runtime": "python",
                "pending_snapshots": 0,
                "pending_feedback": 0,
            },
        },
    )
    assert heartbeat_resp.status_code == 200

    catalog_resp = client.post(
        "/api/agent/symbol-catalog",
        headers={"X-Robot-Token": robot_token},
        json={
            "bridge_name": instance_payload["bridge_name"],
            "chart_symbol": "EURUSD.a",
            "chart_timeframe": "M15",
            "available_symbols": ["EURUSD.a", "USDCAD.a", "XAUUSDm"],
            "market_watch_symbols": ["EURUSD.a", "USDCAD.a"],
            "tracked_symbols": ["EURUSD.a", "USDCAD.a"],
            "exported_at": now_iso,
            "account_login": 123456,
            "server": "Demo-Server",
            "company": "Broker Teste",
            "terminal_name": "MetaTrader 5",
        },
    )
    assert catalog_resp.status_code == 200
    assert catalog_resp.json()["symbols_detected"] == 3
    assert catalog_resp.json()["primary_symbol"] == "EURUSD.a"

    update_instance = client.put(
        f"/api/robot-instances/{robot_instance_id}",
        json={
            "name": "MT5 Demo 01",
            "mode": "DEMO",
            "broker_profile": "CUSTOM",
            "primary_symbol": "XAUUSDm",
            "chart_timeframe": "H1",
            "selected_symbols": ["XAUUSDm"],
        },
    )
    assert update_instance.status_code == 200
    updated_payload = update_instance.json()
    assert updated_payload["broker_profile"] == "CUSTOM"
    assert updated_payload["primary_symbol"] == "XAUUSDm"
    assert updated_payload["chart_timeframe"] == "H1"
    assert updated_payload["selected_symbols"] == ["XAUUSDm"]
    assert updated_payload["discovered_symbols"] == ["EURUSD.a", "USDCAD.a", "XAUUSDm"]

    updated_package_resp = client.get(f"/api/robot-instances/{robot_instance_id}/agent-package")
    assert updated_package_resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(updated_package_resp.content)) as archive:
        runtime_config = json.loads(
            archive.read("vuno-robo/agent-local/runtime/config.json").decode("utf-8")
        )
        assert runtime_config["primary_symbol"] == "XAUUSDm"
        assert runtime_config["chart_timeframe"] == "H1"
        assert runtime_config["selected_symbols"] == ["XAUUSDm"]

    snapshot_payload = {
        "symbol": "XAUUSDm",
        "timeframe": "M5",
        "bid": 1.1000,
        "ask": 1.1002,
        "spread_points": 2.0,
        "close": 1.1001,
        "ema_fast": 1.1010,
        "ema_slow": 1.1000,
        "rsi": 55.0,
        "balance": 10000.0,
        "equity": 10010.0,
        "open_positions": 0,
        "captured_at": now_iso,
        "candles": [
            {
                "time": "2026-04-03 12:00:00",
                "open": 1.0990,
                "high": 1.1005,
                "low": 1.0988,
                "close": 1.1000,
                "tick_volume": 120,
            },
            {
                "time": "2026-04-03 12:05:00",
                "open": 1.1000,
                "high": 1.1008,
                "low": 1.0995,
                "close": 1.1001,
                "tick_volume": 132,
            },
        ],
        "htf_timeframe": "H1",
        "htf_candles": [
            {
                "time": "2026-04-03 11:00:00",
                "open": 1.0960,
                "high": 1.1010,
                "low": 1.0952,
                "close": 1.1001,
                "tick_volume": 980,
            }
        ],
        "local_memory": {"recent_win_rate": 0.6, "recent_pnl": 3.4},
    }
    decision_resp = client.post(
        "/api/agent/decision",
        headers={"X-Robot-Token": robot_token},
        json=snapshot_payload,
    )
    assert decision_resp.status_code == 200
    decision_payload = decision_resp.json()
    assert "decision" in decision_payload
    assert decision_payload["decision"]["signal"] in {"BUY", "SELL", "HOLD"}
    assert decision_payload["decision"]["analysis"]["engine"] in {"legacy_v1", "price_action_v1", "risk_guard"}
    assert decision_payload["decision"]["analysis"]["operational_timeframe"] == "M5"
    assert decision_payload["decision"]["analysis"]["confirmation_timeframe"] == "H1"

    management_decision_resp = client.post(
        "/api/agent/decision",
        headers={"X-Robot-Token": robot_token},
        json={
            **snapshot_payload,
            "open_positions": 1,
            "open_position_ticket": 789012,
            "open_position_direction": "BUY",
            "open_position_entry_price": 1.0990,
                "open_position_current_price": 1.0997,
                "open_position_profit": 14.0,
                "open_position_profit_points": 7.0,
        },
    )
    assert management_decision_resp.status_code == 200
    management_payload = management_decision_resp.json()
    assert management_payload["decision"]["signal"] == "HOLD"
    assert management_payload["decision"]["analysis"]["engine"] == "position_manager_v1"
    assert management_payload["decision"]["position_action"] == "NONE"

    protect_decision_resp = client.post(
        "/api/agent/decision",
        headers={"X-Robot-Token": robot_token},
        json={
            **snapshot_payload,
            "open_positions": 1,
            "open_position_ticket": 789013,
            "open_position_direction": "BUY",
            "open_position_entry_price": 1.0990,
            "open_position_current_price": 1.1008,
            "open_position_profit": 38.4,
            "open_position_profit_points": 18.0,
            "open_position_opened_at": now_iso,
        },
    )
    assert protect_decision_resp.status_code == 200
    protect_payload = protect_decision_resp.json()
    assert protect_payload["decision"]["analysis"]["engine"] == "position_manager_v1"
    assert protect_payload["decision"]["position_action"] == "PROTECT"

    management_audit = client.get(
        "/api/audit-events",
        params={"event_type": "position_management_recorded", "limit": 5},
    )
    assert management_audit.status_code == 200
    latest_management = management_audit.json()[0]
    assert latest_management["robot_instance_id"] == robot_instance_id
    assert latest_management["payload"]["position_action"] in {"NONE", "PROTECT", "CLOSE"}

    management_none_audit = client.get(
        "/api/audit-events",
        params={"position_action": "NONE", "limit": 5},
    )
    assert management_none_audit.status_code == 200
    latest_none = management_none_audit.json()[0]
    assert latest_none["robot_instance_id"] == robot_instance_id
    assert latest_none["payload"]["analysis"]["engine"] == "position_manager_v1"
    assert latest_none["payload"]["position_action"] == "NONE"

    management_protect_audit = client.get(
        "/api/audit-events",
        params={"position_action": "PROTECT", "limit": 5},
    )
    assert management_protect_audit.status_code == 200
    latest_protect = management_protect_audit.json()[0]
    assert latest_protect["robot_instance_id"] == robot_instance_id
    assert latest_protect["payload"]["analysis"]["engine"] == "position_manager_v1"
    assert latest_protect["payload"]["position_action"] == "PROTECT"


    feedback_resp = client.post(
        "/api/agent/trade-feedback",
        headers={"X-Robot-Token": robot_token},
        json={
            "symbol": "XAUUSDm",
            "outcome": "WIN",
            "pnl": 12.34,
            "closed_at": now_iso,
            "ticket": 123456,
            "volume": 0.01,
        },
    )
    assert feedback_resp.status_code == 200

    instances_resp = client.get("/api/robot-instances")
    assert instances_resp.status_code == 200
    instances = instances_resp.json()
    assert instances
    assert any(item["is_online"] for item in instances)
    current_instance = next(item for item in instances if item["robot_instance_id"] == robot_instance_id)
    assert current_instance["package_delivery_mode"] in {"exe", "python"}
    assert current_instance["last_heartbeat_details"]["agent_runtime"] in {"exe", "python"}
    assert current_instance["broker_profile"] == "CUSTOM"
    assert current_instance["primary_symbol"] == "XAUUSDm"
    assert current_instance["chart_timeframe"] == "H1"
    assert current_instance["selected_symbols"] == ["XAUUSDm"]
    assert current_instance["discovered_symbols"] == ["EURUSD.a", "USDCAD.a", "XAUUSDm"]
    assert current_instance["symbols_detected_at"] is not None
    assert current_instance["bridge_name"] == instance_payload["bridge_name"]
    assert current_instance["operational_timeframe"] == "M5"
    assert current_instance["confirmation_timeframe"] == "H1"
    assert current_instance["performance_gate_passed"] is True

    summary_resp = client.get("/api/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["decisions_total"] >= 1
    assert summary["results_total"] >= 1
    assert summary["instances_total"] >= 1
