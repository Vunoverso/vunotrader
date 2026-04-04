from __future__ import annotations

from typing import Any

try:
    from .config import AgentConfig
except ImportError:
    from config import AgentConfig


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_runtime_settings(config: AgentConfig) -> dict[str, Any]:
    return {
        "version": 2,
        "robot_instance_id": config.robot_id,
        "robot_name": config.instance_name,
        "trading_mode": config.trading_mode,
        "operational_timeframe": "M5",
        "confirmation_timeframe": "H1",
        "risk_per_trade": 0.5,
        "max_spread_points": config.max_spread_points,
        "default_lot": config.default_lot,
        "stop_loss_points": config.stop_loss_points,
        "take_profit_points": config.take_profit_points,
        "max_positions_per_symbol": config.max_positions_per_symbol,
        "reentry_cooldown_seconds": config.reentry_cooldown_seconds,
        "max_command_age_seconds": config.max_command_age_seconds,
        "deviation_points": config.deviation_points,
        "execution_retries": config.execution_retries,
        "manual_pause_new_orders": 1 if config.pause_new_orders else 0,
        "pause_new_orders": 1 if config.pause_new_orders else 0,
        "runtime_pause_reasons": [],
        "news_pause_active": 0,
        "performance_gate_passed": 1,
        "use_local_fallback": 1 if config.use_local_fallback else 0,
    }


def build_signal_payload(snapshot: dict[str, Any], config: AgentConfig) -> dict[str, Any]:
    open_side = str(snapshot.get("open_position_direction") or "").strip().lower()
    if open_side not in {"buy", "sell"}:
        open_side = None

    return {
        "robot_id": config.robot_id,
        "robot_token": config.robot_token,
        "user_id": config.user_id,
        "organization_id": config.organization_id,
        "mode": config.trading_mode,
        "symbol": str(snapshot.get("symbol", "")).strip(),
        "timeframe": str(snapshot.get("timeframe", "M5")).strip() or "M5",
        "candles": snapshot.get("candles") or [],
        "open_side": open_side,
        "open_entry": _to_float(snapshot.get("open_position_entry_price"), 0.0) or None,
        "open_sl": _to_float(snapshot.get("open_position_stop_loss"), 0.0) or None,
        "open_tp": _to_float(snapshot.get("open_position_take_profit"), 0.0) or None,
        "balance": _to_float(snapshot.get("balance"), 0.0),
        "cycle_id": str(snapshot.get("cycle_id") or "").strip() or None,
        "bridge_name": str(snapshot.get("bridge_name") or config.bridge_name).strip() or None,
        "chart_symbol": str(snapshot.get("chart_symbol") or snapshot.get("symbol") or "").strip() or None,
        "chart_timeframe": str(snapshot.get("chart_timeframe") or snapshot.get("timeframe") or "M5").strip() or None,
        "visual_shadow_requested": bool(snapshot.get("visual_shadow_requested", config.visual_shadow_enabled)),
        "chart_image_file": str(snapshot.get("chart_image_file") or "").strip() or None,
        "chart_image_captured_at": str(snapshot.get("chart_image_captured_at") or "").strip() or None,
        "chart_image_base64": str(snapshot.get("chart_image_base64") or "").strip() or None,
        "chart_image_sha256": str(snapshot.get("chart_image_sha256") or "").strip() or None,
        "worker_owner": str(snapshot.get("worker_owner") or "").strip() or None,
    }


def build_trade_opened_payload(snapshot: dict[str, Any], config: AgentConfig, decision_id: str) -> dict[str, Any]:
    direction = str(snapshot.get("open_position_direction") or "BUY").strip().lower()
    side = "sell" if direction == "sell" else "buy"
    return {
        "robot_id": config.robot_id,
        "robot_token": config.robot_token,
        "user_id": config.user_id,
        "organization_id": config.organization_id,
        "decision_id": decision_id,
        "ticket": str(_to_int(snapshot.get("open_position_ticket"), 0)),
        "symbol": str(snapshot.get("symbol", "")).strip(),
        "side": side,
        "price": _to_float(snapshot.get("open_position_entry_price"), 0.0),
        "sl": _to_float(snapshot.get("open_position_stop_loss"), 0.0),
        "tp": _to_float(snapshot.get("open_position_take_profit"), 0.0),
        "lot": _to_float(snapshot.get("open_position_volume"), 0.0),
        "balance": _to_float(snapshot.get("balance"), 0.0),
    }


def build_trade_feedback_payload(payload: dict[str, Any], config: AgentConfig, decision_id: str | None) -> dict[str, Any]:
    return {
        "robot_id": config.robot_id,
        "robot_token": config.robot_token,
        "user_id": config.user_id,
        "organization_id": config.organization_id,
        "decision_id": decision_id,
        "ticket": str(_to_int(payload.get("ticket"), 0)),
        "symbol": str(payload.get("symbol", "")).strip(),
        "side": "",
        "profit": _to_float(payload.get("pnl"), 0.0),
        "points": 0,
        "mode": config.trading_mode,
        "balance": 0.0,
    }


def build_heartbeat_payload(config: AgentConfig, balance: float) -> dict[str, Any]:
    return {
        "robot_id": config.robot_id,
        "robot_token": config.robot_token,
        "user_id": config.user_id,
        "organization_id": config.organization_id,
        "mode": config.trading_mode,
        "balance": balance,
        "positions": [],
    }


def build_command_payload(response: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    signal = str(response.get("signal", "HOLD")).upper().strip()
    rationale = str(response.get("rationale") or response.get("reason") or "remote_mt5").strip()
    decision_id = str(response.get("decision_id") or "").strip()
    confidence = max(0.0, min(_to_float(response.get("confidence"), 0.0), 1.0))
    risk = max(0.0, min(_to_float(response.get("risk"), 0.0), 1.0))

    if signal in {"CLOSE_BUY", "CLOSE_SELL"}:
        payload = {
            "signal": "HOLD",
            "confidence": 1.0,
            "risk": 0.0,
            "position_action": "CLOSE",
            "position_ticket": _to_int(snapshot.get("open_position_ticket"), 0),
            "reason": rationale or "smart_exit",
            "decision_id": decision_id,
        }
        if response.get("cycle_id"):
            payload["cycle_id"] = str(response["cycle_id"])
        if response.get("visual_shadow_status"):
            payload["visual_shadow_status"] = str(response["visual_shadow_status"])
        if response.get("visual_alignment"):
            payload["visual_alignment"] = str(response["visual_alignment"])
        return payload

    if signal not in {"BUY", "SELL"} or not decision_id:
        payload = {
            "signal": "HOLD",
            "confidence": 0.0,
            "risk": 0.0,
            "reason": rationale or "hold",
            "decision_id": decision_id,
        }
        if response.get("cycle_id"):
            payload["cycle_id"] = str(response["cycle_id"])
        if response.get("visual_shadow_status"):
            payload["visual_shadow_status"] = str(response["visual_shadow_status"])
        if response.get("visual_alignment"):
            payload["visual_alignment"] = str(response["visual_alignment"])
        return payload

    payload = {
        "signal": signal,
        "confidence": confidence,
        "risk": risk,
        "stop_loss_points": 0,
        "take_profit_points": 0,
        "stop_loss_price": _to_float(response.get("stop_loss"), 0.0),
        "take_profit_price": _to_float(response.get("take_profit"), 0.0),
        "reason": rationale or "remote_mt5",
        "decision_id": decision_id,
        "comment": f"VUNO|{decision_id}|{confidence * 100:.0f}%",
    }
    if response.get("cycle_id"):
        payload["cycle_id"] = str(response["cycle_id"])
    if response.get("visual_shadow_status"):
        payload["visual_shadow_status"] = str(response["visual_shadow_status"])
    if response.get("visual_alignment"):
        payload["visual_alignment"] = str(response["visual_alignment"])
    return payload