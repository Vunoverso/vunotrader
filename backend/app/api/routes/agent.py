from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.api.routes import mt5
from app.core.config import get_settings
from app.core.supabase import get_service_supabase
from app.services.visual_shadow import process_visual_shadow_cycle

router = APIRouter()


class AgentDecisionPayload(BaseModel):
    robot_id: str | None = None
    robot_token: str | None = None
    user_id: str | None = None
    organization_id: str | None = None
    mode: str = "demo"
    symbol: str
    timeframe: str = "M5"
    candles: list[list[float]] = Field(default_factory=list)
    open_side: str | None = None
    open_entry: float | None = None
    open_sl: float | None = None
    open_tp: float | None = None
    balance: float = 0.0
    cycle_id: str | None = None
    bridge_name: str | None = None
    chart_symbol: str | None = None
    chart_timeframe: str | None = None
    visual_shadow_requested: bool = False
    chart_image_file: str | None = None
    chart_image_captured_at: str | None = None
    chart_image_base64: str | None = None
    chart_image_sha256: str | None = None
    worker_owner: str | None = None


class AgentSymbolCatalogPayload(BaseModel):
    bridge_name: str | None = None
    chart_symbol: str | None = None
    chart_timeframe: str | None = None
    available_symbols: list[str] = Field(default_factory=list)
    market_watch_symbols: list[str] = Field(default_factory=list)
    tracked_symbols: list[str] = Field(default_factory=list)
    exported_at: str | None = None


def _resolve_robot_token(x_device_token: str | None, x_robot_token: str | None) -> str:
    token = (x_robot_token or x_device_token or "").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token do robo ausente")
    return token


def _select_first(builder):
    result = builder.limit(1).execute()
    if isinstance(result.data, list):
        result.data = result.data[0] if result.data else None
    return result


def _resolve_robot_context(token: str) -> dict[str, Any]:
    sb = get_service_supabase()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    robot_res = _select_first(
        sb.table("robot_instances")
        .select("id, organization_id, profile_id, name, status, allowed_modes, real_trading_enabled, robot_product_type, visual_shadow_enabled, computer_use_enabled, human_approval_required")
        .eq("robot_token_hash", token_hash)
    )
    row = robot_res.data
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Instancia do robo invalida")
    if row.get("status") == "revoked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Robot revoked")

    profile_res = _select_first(
        sb.table("user_profiles")
        .select("auth_user_id")
        .eq("id", row["profile_id"])
    )
    auth_user_id = profile_res.data.get("auth_user_id") if profile_res.data else None
    if not auth_user_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Perfil do robo sem usuario autenticado")

    row["auth_user_id"] = str(auth_user_id)
    return row


def _resolve_robot_mode(robot: dict[str, Any]) -> str:
    allowed_modes = [str(mode).lower() for mode in (robot.get("allowed_modes") or [])]
    if robot.get("real_trading_enabled") and "real" in allowed_modes:
        return "real"
    if "demo" in allowed_modes:
        return "demo"
    return "observer"


def _runtime_parameters() -> dict[str, Any]:
    return {
        "risk_per_trade": 0.5,
        "max_spread_points": 30,
        "default_lot": 0.01,
        "stop_loss_points": 180,
        "take_profit_points": 360,
        "max_positions_per_symbol": 1,
        "reentry_cooldown_seconds": 60,
        "max_command_age_seconds": 45,
        "deviation_points": 20,
        "execution_retries": 3,
        "pause_new_orders": False,
        "use_local_fallback": True,
    }


def _runtime_gate_state(robot: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    reasons: list[str] = []
    if robot.get("status") != "active":
        reasons.append(f"robot_status_{robot.get('status')}")
    if robot.get("human_approval_required"):
        reasons.append("human_approval_required")
    if robot.get("visual_shadow_enabled") and settings.visual_shadow_kill_switch:
        reasons.append("visual_shadow_kill_switch")
    if robot.get("computer_use_enabled") and settings.computer_use_kill_switch:
        reasons.append("computer_use_kill_switch")
    return {
        "runtime_pause_new_orders": bool(reasons),
        "runtime_pause_reasons": reasons,
        "operational_timeframe": "M5",
        "confirmation_timeframe": "H1",
        "news_pause_active": False,
        "performance_gate_passed": not reasons,
    }


@router.get("/runtime-config")
async def runtime_config(
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    runtime_state = _runtime_gate_state(robot)
    return {
        "robot_instance_id": robot["id"],
        "robot_name": robot["name"],
        "robot_mode": _resolve_robot_mode(robot),
        "parameters": _runtime_parameters(),
        **runtime_state,
    }


@router.post("/heartbeat")
async def heartbeat(
    payload: mt5.HeartbeatPayload,
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
):
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    resolved_payload = mt5.HeartbeatPayload(
        robot_id=robot["id"],
        robot_token=token,
        user_id=robot["auth_user_id"],
        organization_id=robot["organization_id"],
        mode=_resolve_robot_mode(robot),
        balance=payload.balance,
        positions=payload.positions,
    )
    return await mt5.heartbeat(resolved_payload)


@router.post("/decision")
async def decision(
    payload: AgentDecisionPayload,
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    signal_payload = mt5.SignalPayload(
        robot_id=robot["id"],
        robot_token=token,
        user_id=robot["auth_user_id"],
        organization_id=robot["organization_id"],
        mode=_resolve_robot_mode(robot),
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        candles=payload.candles,
        open_side=payload.open_side,
        open_entry=payload.open_entry,
        open_sl=payload.open_sl,
        open_tp=payload.open_tp,
        balance=payload.balance,
        cycle_id=payload.cycle_id,
    )
    result = await mt5.get_signal(signal_payload)
    visual = process_visual_shadow_cycle(
        sb=get_service_supabase(),
        robot=robot,
        payload={
            **payload.model_dump(),
            "symbol": payload.symbol,
            "timeframe": payload.timeframe,
            "visual_shadow_requested": payload.visual_shadow_requested or bool(robot.get("visual_shadow_enabled")),
        },
        decision_id=result.decision_id,
        structured_signal=result.signal,
        structured_confidence=result.confidence,
    )
    response = result.model_dump()
    response.update(visual)
    return response


@router.post("/trade-feedback")
async def trade_feedback(
    payload: mt5.TradeOutcomePayload,
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
):
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    resolved_payload = mt5.TradeOutcomePayload(
        robot_id=robot["id"],
        robot_token=token,
        user_id=robot["auth_user_id"],
        organization_id=robot["organization_id"],
        decision_id=payload.decision_id,
        ticket=payload.ticket,
        symbol=payload.symbol,
        side=payload.side,
        profit=payload.profit,
        points=payload.points,
        mode=_resolve_robot_mode(robot),
        balance=payload.balance,
    )
    return await mt5.trade_outcome(resolved_payload)


@router.post("/trade-opened")
async def trade_opened(
    payload: mt5.TradeOpenedPayload,
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
):
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    resolved_payload = mt5.TradeOpenedPayload(
        robot_id=robot["id"],
        robot_token=token,
        user_id=robot["auth_user_id"],
        organization_id=robot["organization_id"],
        decision_id=payload.decision_id,
        ticket=payload.ticket,
        symbol=payload.symbol,
        side=payload.side,
        price=payload.price,
        sl=payload.sl,
        tp=payload.tp,
        lot=payload.lot,
        balance=payload.balance,
    )
    return await mt5.trade_opened(resolved_payload)


@router.post("/symbol-catalog")
async def symbol_catalog(
    payload: AgentSymbolCatalogPayload,
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
) -> dict[str, Any]:
    token = _resolve_robot_token(x_device_token, x_robot_token)
    robot = _resolve_robot_context(token)
    mt5._sync_robot_data(get_service_supabase(), robot["id"], 0.0)
    return {
        "status": "ok",
        "bridge_name": payload.bridge_name,
        "chart_symbol": payload.chart_symbol,
        "tracked_symbols": payload.tracked_symbols,
    }