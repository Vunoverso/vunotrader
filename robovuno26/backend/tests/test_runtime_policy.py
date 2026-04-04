from __future__ import annotations

import importlib
from datetime import datetime, timezone

from app.runtime_policy import evaluate_market_session


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def login_and_prepare(client):
    email = unique_email("runtime.policy")
    password = "Senha123!"
    assert client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Policy Flow"},
    ).status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": password}).status_code == 200


def test_create_demo_instance_is_blocked_without_validated_edge(client):
    login_and_prepare(client)

    response = client.post(
        "/api/robot-instances",
        json={"name": "Robo Bloqueado", "mode": "DEMO"},
    )

    assert response.status_code == 422
    assert "Edge minimo ainda nao validado" in response.json()["detail"]


def test_news_pause_blocks_xauusd_decision(client, monkeypatch):
    login_and_prepare(client)

    parameters = client.get("/api/parameters").json()
    save_resp = client.put(
        "/api/parameters",
        json={
            **parameters,
            "news_pause_enabled": True,
            "news_pause_symbols": "XAUUSD",
            "news_pause_countries": "USD",
            "performance_gate_enabled": True,
            "performance_gate_min_profit_factor": 1.3,
            "performance_gate_min_trades": 100,
            "validated_backtest_profit_factor": 1.6,
            "validated_backtest_trades": 180,
        },
    )
    assert save_resp.status_code == 200

    create_instance = client.post(
        "/api/robot-instances",
        json={"name": "Gold Demo", "mode": "DEMO", "primary_symbol": "XAUUSD"},
    )
    assert create_instance.status_code == 200
    robot_token = create_instance.json()["token"]

    runtime_policy = importlib.import_module("app.runtime_policy")

    def fake_active_news_events_for_symbol(*_args, **_kwargs):
        return {
            "events": [
                {
                    "symbol": "XAUUSD",
                    "title": "Non-Farm Payrolls",
                    "country": "USD",
                    "impact": "HIGH",
                    "date": "2026-04-03T12:00:00+00:00",
                }
            ],
            "countries": ["USD"],
            "error": None,
        }

    monkeypatch.setattr(runtime_policy, "active_news_events_for_symbol", fake_active_news_events_for_symbol)

    runtime_config_resp = client.get(
        "/api/agent/runtime-config",
        headers={"X-Robot-Token": robot_token},
    )
    assert runtime_config_resp.status_code == 200
    assert runtime_config_resp.json()["runtime_pause_new_orders"] is True
    assert "news_pause" in runtime_config_resp.json()["runtime_pause_reasons"]

    now_iso = datetime.now(timezone.utc).isoformat()
    decision_resp = client.post(
        "/api/agent/decision",
        headers={"X-Robot-Token": robot_token},
        json={
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "bid": 2300.0,
            "ask": 2300.4,
            "spread_points": 4.0,
            "close": 2300.2,
            "ema_fast": 2300.1,
            "ema_slow": 2299.8,
            "rsi": 51.0,
            "balance": 10000.0,
            "equity": 10020.0,
            "open_positions": 0,
            "captured_at": now_iso,
            "candles": [],
            "htf_timeframe": "H1",
            "htf_candles": [],
            "local_memory": {"recent_win_rate": 0.62, "recent_pnl": 10.0},
        },
    )
    assert decision_resp.status_code == 200
    decision = decision_resp.json()["decision"]
    assert decision["signal"] == "HOLD"
    assert decision["analysis"]["engine"] == "runtime_guard"
    assert "news_pause" in decision["analysis"]["pause_reasons"]


def test_create_demo_instance_is_blocked_without_news_coverage(client):
    login_and_prepare(client)

    parameters = client.get("/api/parameters").json()
    save_resp = client.put(
        "/api/parameters",
        json={
            **parameters,
            "news_pause_enabled": True,
            "news_pause_symbols": "XAUUSD",
            "performance_gate_enabled": True,
            "performance_gate_min_profit_factor": 1.3,
            "performance_gate_min_trades": 100,
            "validated_backtest_profit_factor": 1.6,
            "validated_backtest_trades": 180,
        },
    )
    assert save_resp.status_code == 200

    response = client.post(
        "/api/robot-instances",
        json={"name": "FX Demo", "mode": "DEMO", "primary_symbol": "EURUSD", "selected_symbols": ["EURUSD", "GBPUSD"]},
    )

    assert response.status_code == 422
    assert "pausa por noticia precisa cobrir os ativos desta instancia" in response.json()["detail"]


def test_market_session_blocks_b3_future_outside_local_hours():
    result = evaluate_market_session(
        {"market_session_guard_enabled": True},
        symbol="WINM26",
        broker_profile="B3_FUTURES",
        observed_at=datetime(2026, 4, 6, 23, 10, tzinfo=timezone.utc),
    )

    assert result["family"] == "b3_futures"
    assert result["open"] is False
    assert result["reason"] == "market_session_closed"


def test_drawdown_guard_blocks_decision_after_daily_loss_and_equity_cut(client):
    login_and_prepare(client)

    parameters = client.get("/api/parameters").json()
    save_resp = client.put(
        "/api/parameters",
        json={
            **parameters,
            "performance_gate_enabled": True,
            "performance_gate_min_profit_factor": 1.3,
            "performance_gate_min_trades": 100,
            "validated_backtest_profit_factor": 1.6,
            "validated_backtest_trades": 180,
            "daily_loss_limit": 50,
            "max_equity_drawdown_pct": 2.0,
        },
    )
    assert save_resp.status_code == 200

    create_instance = client.post(
        "/api/robot-instances",
        json={"name": "Drawdown Guard", "mode": "DEMO", "primary_symbol": "EURUSD"},
    )
    assert create_instance.status_code == 200
    robot_token = create_instance.json()["token"]

    now_iso = datetime.now(timezone.utc).isoformat()
    feedback_resp = client.post(
        "/api/agent/trade-feedback",
        headers={"X-Robot-Token": robot_token},
        json={
            "symbol": "EURUSD",
            "outcome": "LOSS",
            "pnl": -75.0,
            "closed_at": now_iso,
            "ticket": 456789,
            "volume": 0.01,
        },
    )
    assert feedback_resp.status_code == 200

    decision_resp = client.post(
        "/api/agent/decision",
        headers={"X-Robot-Token": robot_token},
        json={
            "symbol": "EURUSD",
            "timeframe": "M5",
            "bid": 1.1040,
            "ask": 1.1042,
            "spread_points": 2.0,
            "close": 1.1041,
            "ema_fast": 1.1043,
            "ema_slow": 1.1038,
            "rsi": 54.0,
            "balance": 10000.0,
            "equity": 9750.0,
            "open_positions": 0,
            "captured_at": now_iso,
            "candles": [],
            "htf_timeframe": "H1",
            "htf_candles": [],
            "local_memory": {"recent_win_rate": 0.51, "recent_pnl": -12.0},
        },
    )
    assert decision_resp.status_code == 200

    payload = decision_resp.json()["decision"]
    assert payload["signal"] == "HOLD"
    assert payload["analysis"]["engine"] == "runtime_guard"
    assert "daily_loss_limit" in payload["analysis"]["pause_reasons"]
    assert "equity_drawdown_limit" in payload["analysis"]["pause_reasons"]