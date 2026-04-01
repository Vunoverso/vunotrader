"""
Endpoints para comunicação direta com o EA do MetaTrader 5.
Recebe heartbeat e dados de mercado sem depender do Python local.
"""
from datetime import datetime, timezone
import hashlib
import hmac
import time
import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.supabase import get_service_supabase

router = APIRouter()

log = logging.getLogger("mt5")


# ── Schemas ──────────────────────────────────────────────────────────────────

class HeartbeatPayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    mode: str = "demo"


class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str


class SignalPayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    mode: str = "demo"
    symbol: str
    timeframe: str = "M5"
    # candles: lista de [timestamp, open, high, low, close, volume]
    candles: list[list[float]]


class SignalResponse(BaseModel):
    signal: str            # "BUY" | "SELL" | "HOLD"
    confidence: float
    risk: float
    decision_id: str | None = None
    regime: str
    rationale: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_robot(robot_id: str, robot_token: str, organization_id: str) -> dict:
    """Valida se o robot_id + token pertencem à organização. Retorna o registro."""
    sb = get_service_supabase()
    result = (
        sb.table("robot_instances")
        .select("id, robot_token_hash, organization_id, status")
        .eq("id", robot_id)
        .eq("organization_id", organization_id)
        .single()
        .execute()
    )
    row = result.data
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")

    stored_hash = str(row.get("robot_token_hash") or "")
    incoming_hash = hashlib.sha256(robot_token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(stored_hash, incoming_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid robot token")

    if row.get("status") == "revoked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Robot revoked")
    return row


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/heartbeat", response_model=HeartbeatResponse, summary="Ping de vida do EA")
async def heartbeat(payload: HeartbeatPayload):
    """
    Recebe um ping do EA do MetaTrader 5 e atualiza last_seen_at no Supabase.
    Chamado a cada 30 segundos pelo OnTimer() — sem necessidade do Python local.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)

    now = datetime.now(timezone.utc).isoformat()
    sb = get_service_supabase()
    sb.table("robot_instances").update({"last_seen_at": now}).eq("id", payload.robot_id).execute()

    return HeartbeatResponse(status="ok", timestamp=now)


@router.post("/signal", response_model=SignalResponse, summary="Análise de mercado e sinal de trade")
async def get_signal(payload: SignalPayload):
    """
    Recebe candles do EA, executa análise técnica no Render (sem Python local)
    e retorna BUY / SELL / HOLD com confiança, risco e decision_id para rastreio completo.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)

    if len(payload.candles) < 60:
        return SignalResponse(
            signal="HOLD",
            confidence=0.0,
            risk=0.0,
            decision_id=None,
            regime="lateral",
            rationale="insufficient_candles",
        )

    # ── Análise técnica ───────────────────────────────────────────────────────
    from app.core.signal_engine import analyse
    result = analyse(payload.candles)

    # ── Salvar TODOS os sinais no Supabase (inclusive HOLD → alimenta terminal feed) ──
    decision_id: str | None = None
    try:
        sb = get_service_supabase()
        trade_id = f"{payload.symbol}-{int(time.time() * 1000)}"
        resp = sb.table("trade_decisions").insert({
            "trade_id":        trade_id,
            "user_id":         payload.user_id,
            "organization_id": payload.organization_id,
            "robot_instance_id": payload.robot_id,
            "mode":            payload.mode,
            "symbol":          payload.symbol,
            "timeframe":       payload.timeframe,
            "side":            result.signal.lower(),
            "confidence":      result.confidence,
            "risk_pct":        result.risk_pct,
            "rationale":       result.rationale,
        }).execute()
        decision_id = resp.data[0]["id"] if resp.data else None
        log.info("Decision saved: %s %s conf=%.2f", result.signal, payload.symbol, result.confidence)
    except Exception as exc:
        log.warning("Supabase trade_decisions insert failed: %s", exc)

    return SignalResponse(
        signal=result.signal,
        confidence=result.confidence,
        risk=result.risk_pct,
        decision_id=decision_id,
        regime=result.regime,
        rationale=result.rationale,
    )
