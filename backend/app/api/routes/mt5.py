"""
Endpoints para comunicação direta com o EA do MetaTrader 5.
Recebe heartbeat e dados de mercado sem depender do Python local.
"""
from datetime import datetime, timezone, timedelta
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
    balance: float = 0.0


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
    # Informação de posição aberta (se houver) para Smart Exit
    open_side: str | None = None
    open_entry: float | None = None
    open_sl: float | None = None
    open_tp: float | None = None
    balance: float = 0.0


class SignalResponse(BaseModel):
    signal: str            # "BUY" | "SELL" | "HOLD"
    confidence: float
    risk: float
    decision_id: str | None = None
    regime: str
    rationale: str


class TradeOutcomePayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    decision_id: str | None = None
    ticket: str
    symbol: str
    side: str = ""
    profit: float
    points: int = 0
    mode: str = "demo"


class TradeOpenedPayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    decision_id: str
    ticket: str
    symbol: str
    side: str
    price: float
    sl: float = 0.0
    tp: float = 0.0
    lot: float = 0.0
    balance: float = 0.0


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
    sb.table("robot_instances").update({
        "last_seen_at": now,
        "current_balance": payload.balance
    }).eq("id", payload.robot_id).execute()

    return HeartbeatResponse(status="ok", timestamp=now)


@router.post("/signal", response_model=SignalResponse, summary="Análise de mercado e sinal de trade")
async def get_signal(payload: SignalPayload):
    """
    Recebe candles do EA, executa análise técnica no Render (sem Python local)
    e retorna BUY / SELL / HOLD com confiança, risco e decision_id para rastreio completo.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)

    # Atualiza o saldo e presença do robô antes da análise
    try:
        sb.table("robot_instances").update({
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "current_balance": payload.balance
        }).eq("id", payload.robot_id).execute()
    except:
        pass

    if len(payload.candles) < 60:
        return SignalResponse(
            signal="HOLD",
            confidence=0.0,
            risk=0.0,
            decision_id=None,
            regime="lateral",
            rationale="insufficient_candles",
        )

    # ── Buscar parâmetros do usuário p/ personalizar o sinal ─────────────
    sb = get_service_supabase()
    user_params = {}
    try:
        params_res = (
            sb.table("user_parameters")
            .select("per_trade_stop_loss_mode, per_trade_stop_loss_value, per_trade_take_profit_rr")
            .eq("user_id", payload.user_id)
            .single()
            .execute()
        )
        if params_res.data:
            user_params = params_res.data
    except Exception as exc:
        log.warning("Failed to fetch user parameters: %s. Using defaults.", exc)

    # ── Análise técnica p/ Novo Sinal ─────────────────────────────────────────
    from app.core.signal_engine import analyse, check_smart_exit
    result = analyse(
        payload.candles,
        sl_mode=user_params.get("per_trade_stop_loss_mode", "atr"),
        sl_value=float(user_params.get("per_trade_stop_loss_value", 2.0)),
        tp_rr=float(user_params.get("per_trade_take_profit_rr", 2.0))
    )

    # ── 🔍 SMART EXIT: Verificar se deve fechar posição atual ────────────────
    if payload.open_side and payload.open_entry:
        should_exit, exit_reason = check_smart_exit(
            payload.candles,
            payload.open_side,
            payload.open_entry,
            payload.open_sl or 0.0,
            payload.open_tp or 0.0
        )
        
        if should_exit:
            log.info(f"Smart Exit acionado: {exit_reason} para {payload.symbol}")
            return SignalResponse(
                signal=f"CLOSE_{payload.open_side.upper()}",
                confidence=1.0,
                risk=0.0,
                decision_id=None,
                regime="lateral",
                rationale=f"Smart Exit: {exit_reason}",
            )

    # ── Salvar TODOS os sinais no Supabase ──
    decision_id: str | None = None
    try:
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
            "entry_price":     result.price,
            "stop_loss":       result.sl,
            "take_profit":     result.tp,
        }).execute()
        decision_id = resp.data[0]["id"] if resp.data else None
    except Exception as exc:
        log.error("Database insert failed: %s", exc)

    # ── Tracking de Performance (Virtual Outcome Loop) ──
    try:
        current_price = payload.candles[-1][4]
        pending = (
            sb.table("trade_decisions")
            .select("id, side, entry_price, stop_loss, take_profit, rationale")
            .eq("symbol", payload.symbol)
            .eq("outcome_status", "pending")
            .execute()
        )
        
        from app.services.ai_analysis import analyze_loss
        
        for dec in (pending.data or []):
            if dec["id"] == decision_id: continue # ignora o que acabamos de criar
            
            side = dec["side"]
            entry = dec["entry_price"]
            sl = dec["stop_loss"]
            tp = dec["take_profit"]
            
            outcome = None
            diff = current_price - entry
            
            if side == "buy":
                if current_price >= tp and tp > 0: outcome = "win"
                elif current_price <= sl and sl > 0: outcome = "loss"
            elif side == "sell":
                if current_price <= tp and tp > 0: outcome = "win"
                elif current_price >= sl and sl > 0: outcome = "loss"
            
            if outcome:
                # Se for LOSS, pede aníse técnica da IA
                post_analysis = None
                if outcome == "loss":
                    post_analysis = analyze_loss(
                        payload.symbol, side, entry, sl, tp, current_price, dec["rationale"]
                    )
                
                sb.table("trade_decisions").update({
                    "outcome_status": outcome,
                    "outcome_pips": abs(diff),
                    "post_analysis": post_analysis # Salva a lição aprendida
                }).eq("id", dec["id"]).execute()
                
    except Exception as exc:
        log.warning("Tracking failed: %s", exc)

    return SignalResponse(
        signal=result.signal,
        confidence=result.confidence,
        risk=result.risk_pct,
        decision_id=decision_id,
        regime=result.regime,
        rationale=result.rationale,
    )


@router.post("/trade-outcome", summary="Reportar resultado real da operação")
async def trade_outcome(payload: TradeOutcomePayload):
    """
    Recebe o resultado financeiro final de uma operação fechada no MT5.
    Atualiza trade_decisions para Auditoria fiel.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    
    sb = get_service_supabase()
    
    # 1. Tenta localizar a decisão original pelo decision_id
    if payload.decision_id:
        try:
            status = "win" if payload.profit > 0 else "loss" if payload.profit < 0 else "neutral"
            
            sb.table("trade_decisions").update({
                "outcome_status": status,
                "outcome_pips": payload.points,
                "outcome_profit": payload.profit # Certifique-se de que esta coluna existe no banco
            }).eq("id", payload.decision_id).execute()
            
            log.info(f"Resultado real processado: {payload.decision_id} -> {status} ({payload.profit})")
            return {"status": "success", "message": "Outcome updated"}
        except Exception as exc:
            log.error("Failed to update trade outcome: %s", exc)
            raise HTTPException(status_code=500, detail="Database update failed")
    
    return {"status": "ignored", "message": "No decision_id provided"}


@router.post("/trade-opened", summary="Reportar abertura imediata de trade")
async def trade_opened(payload: TradeOpenedPayload):
    """
    Recebe a confirmação de que uma ordem foi aberta no MT5.
    Marca trade_decisions como 'executing' para aparecer no 'Agora' do Dashboard.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    
    sb = get_service_supabase()
    
    try:
        # Atualiza o registro original do sinal para 'executing'
        sb.table("trade_decisions").update({
            "outcome_status": "executing",
            "entry_price": payload.price,
            "stop_loss": payload.sl,
            "take_profit": payload.tp,
            # "ticket": payload.ticket # Adicione se criar a coluna
        }).eq("id", payload.decision_id).execute()
        
        log.info(f"Trade aberto confirmado: {payload.decision_id} (Ticket: {payload.ticket})")
        return {"status": "success", "message": "Trade marked as executing"}
    except Exception as exc:
        log.error("Failed to mark trade as opened: %s", exc)
        raise HTTPException(status_code=500, detail="Database update failed")
