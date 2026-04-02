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

class OpenPosition(BaseModel):
    ticket: int
    symbol: str
    side: str
    volume: float
    price: float
    profit: float
    sl: float = 0.0
    tp: float = 0.0
    decision_id: str | None = None


class HeartbeatPayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    mode: str = "demo"
    balance: float = 0.0
    positions: list[OpenPosition] = []


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
    # Parâmetros do usuário retornados para o EA aplicar
    user_mode: str | None = None          # "observer" | "demo" | "real"
    daily_loss_limit: float | None = None # R$ limite de perda diária
    max_drawdown_pct: float | None = None # % drawdown máximo
    max_trades_day: int | None = None     # máx. trades por dia
    trading_start: str | None = None      # "HH:MM:SS"
    trading_end: str | None = None        # "HH:MM:SS"
    allowed_symbols: str | None = None    # símbolos separados por vírgula


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
    balance: float = 0.0


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
        .select("id, robot_token_hash, organization_id, status, initial_balance")
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


def _sync_robot_data(sb, robot_id: str, balance: float) -> None:
    """Força a atualização do saldo e presença do robô no Supabase."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        update_data = {
            "last_seen_at": now,
        }
        
        # Busca o robô para checar banca inicial e saldo atual
        check = sb.table("robot_instances").select("initial_balance, current_balance").eq("id", robot_id).single().execute()
        
        # Só atualiza o saldo se for maior que zero ou se ainda não temos saldo registrado
        # (isso evita que um payload sem o campo balance — que chega como 0.0 — zere a banca no painel)
        if balance > 0:
            update_data["current_balance"] = balance
        elif not check.data or not check.data.get("current_balance"):
            update_data["current_balance"] = 0.0

        if check.data and (not check.data.get("initial_balance") or check.data.get("initial_balance") == 0):
            if balance > 0:
                log.info(f"Setando banca inicial para {robot_id}: {balance}")
                update_data["initial_balance"] = balance
        
        sb.table("robot_instances").update(update_data).eq("id", robot_id).execute()
    except Exception as exc:
        log.warning(f"Failed to sync robot data for {robot_id}: {exc}")


def _log_cycle_signal(
    sb,
    *,
    cycle_id: str,
    payload: SignalPayload,
    result,
    decision_id: str | None,
    decision_status: str,
) -> None:
    try:
        sb.table("scanner_cycle_logs").insert({
            "cycle_id": cycle_id,
            "cycle_ts": datetime.now(timezone.utc).isoformat(),
            "mode": payload.mode,
            "symbol": payload.symbol,
            "timeframe": payload.timeframe,
            "signal": result.signal,
            "decision_status": decision_status,
            "decision_reason": result.rationale,
            "block_reason": result.rationale if decision_status == "analyzed" else None,
            "confidence": result.confidence,
            "risk_pct": result.risk_pct,
            "regime": result.regime,
            "score": float(getattr(result, "score", 0.0) or 0.0),
            "spread_points": 0.0,
            "atr_pct": float(getattr(result, "atr_pct", 0.0) or 0.0),
            "volume_ratio": float(getattr(result, "volume_ratio", 0.0) or 0.0),
            "rsi": float(getattr(result, "rsi", 0.0) or 0.0),
            "momentum_20": float(getattr(result, "momentum_20", 0.0) or 0.0),
            "decision_id": decision_id,
            "executed": False,
            "user_id": payload.user_id,
            "organization_id": payload.organization_id,
            "robot_instance_id": payload.robot_id,
            "feature_hash": hashlib.sha256(
                f"{payload.symbol}|{payload.timeframe}|{getattr(result, 'score', 0.0)}|{getattr(result, 'atr_pct', 0.0)}|{getattr(result, 'volume_ratio', 0.0)}|{getattr(result, 'rsi', 0.0)}|{getattr(result, 'momentum_20', 0.0)}".encode("utf-8")
            ).hexdigest(),
        }).execute()
    except Exception as exc:
        log.warning("Cycle log insert failed: %s", exc)


def _mark_cycle_executed(sb, decision_id: str, ticket: str, price: float) -> None:
    try:
        sb.table("scanner_cycle_logs").update({
            "decision_status": "executed",
            "executed": True,
            "broker_ticket": ticket,
            "pnl_money": 0.0,
            "pnl_points": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).eq("decision_id", decision_id).execute()
    except Exception as exc:
        log.warning("Cycle log execute update failed: %s", exc)


def _mark_cycle_closed(sb, decision_id: str, profit: float, points: int, result_label: str) -> None:
    try:
        sb.table("scanner_cycle_logs").update({
            "decision_status": "closed",
            "executed": True,
            "result": result_label,
            "pnl_money": profit,
            "pnl_points": float(points),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).eq("decision_id", decision_id).execute()
    except Exception as exc:
        log.warning("Cycle log close update failed: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/heartbeat", response_model=HeartbeatResponse, summary="Ping de vida do EA")
async def heartbeat(payload: HeartbeatPayload):
    """Atualiza presença e saldo via heartbeat."""
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    sb = get_service_supabase()
    _sync_robot_data(sb, payload.robot_id, payload.balance)

    # Healing Logic: Sincroniza estados das decisões baseado no que o MT5 reportou
    if payload.positions:
        for pos in payload.positions:
            if pos.decision_id:
                # Se o MT5 diz que está aberta, garante que no DB está como 'executing'
                # (isso cura casos onde o /trade-opened falhou mas a ordem abriu)
                sb.table("trade_decisions").update({
                    "outcome_status": "executing",
                    "entry_price": pos.price,
                    "stop_loss": pos.sl if pos.sl > 0 else None,
                    "take_profit": pos.tp if pos.tp > 0 else None,
                }).eq("id", pos.decision_id).neq("outcome_status", "executing").execute()
    
    return HeartbeatResponse(status="ok", timestamp=datetime.now(timezone.utc).isoformat())


@router.post("/signal", response_model=SignalResponse, summary="Análise de mercado e sinal de trade")
async def get_signal(payload: SignalPayload):
    """Recebe candles, analisa mercado e sincroniza saldo."""
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    sb = get_service_supabase()
    _sync_robot_data(sb, payload.robot_id, payload.balance)

    if len(payload.candles) < 60:
        result = SignalResponse(
            signal="HOLD",
            confidence=0.0,
            risk=0.0,
            decision_id=None,
            regime="lateral",
            rationale="insufficient_candles",
        )
        try:
            sb.table("scanner_cycle_logs").insert({
                "cycle_id": f"{payload.symbol}-{int(time.time() * 1000)}",
                "cycle_ts": datetime.now(timezone.utc).isoformat(),
                "mode": payload.mode,
                "symbol": payload.symbol,
                "timeframe": payload.timeframe,
                "signal": result.signal,
                "decision_status": "analyzed",
                "decision_reason": result.rationale,
                "block_reason": result.rationale,
                "confidence": 0.0,
                "risk_pct": 0.0,
                "regime": result.regime,
                "executed": False,
                "user_id": payload.user_id,
                "organization_id": payload.organization_id,
                "robot_instance_id": payload.robot_id,
            }).execute()
        except Exception as exc:
            log.warning("Cycle log insert failed for insufficient candles: %s", exc)
        return result

    # ── Buscar parâmetros do usuário p/ personalizar o sinal ─────────────
    user_params = {}
    try:
        params_res = (
            sb.table("user_parameters")
            .select(
                "per_trade_stop_loss_mode, per_trade_stop_loss_value, per_trade_take_profit_rr,"
                "mode, daily_loss_limit, max_drawdown_pct, max_trades_per_day,"
                "trading_start, trading_end, allowed_symbols"
            )
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
    trade_id = f"{payload.symbol}-{int(time.time() * 1000)}"
    try:
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

    cycle_status = "picked" if result.signal in {"BUY", "SELL"} else "analyzed"
    _log_cycle_signal(
        sb,
        cycle_id=trade_id,
        payload=payload,
        result=result,
        decision_id=decision_id,
        decision_status=cycle_status,
    )

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

    # Extrair os parâmetros do usuário para enviar ao EA
    _max_trades = user_params.get("max_trades_per_day")
    return SignalResponse(
        signal=result.signal,
        confidence=result.confidence,
        risk=result.risk_pct,
        decision_id=decision_id,
        regime=result.regime,
        rationale=result.rationale,
        user_mode=user_params.get("mode") or None,
        daily_loss_limit=float(user_params["daily_loss_limit"]) if user_params.get("daily_loss_limit") is not None else None,
        max_drawdown_pct=float(user_params["max_drawdown_pct"]) if user_params.get("max_drawdown_pct") is not None else None,
        max_trades_day=int(_max_trades) if _max_trades is not None else None,
        trading_start=user_params.get("trading_start") or None,
        trading_end=user_params.get("trading_end") or None,
        allowed_symbols=user_params.get("allowed_symbols") or None,
    )


@router.post("/trade-outcome", summary="Reportar resultado real da operação")
async def trade_outcome(payload: TradeOutcomePayload):
    """Reporta resultado e sincroniza saldo final."""
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    sb = get_service_supabase()
    _sync_robot_data(sb, payload.robot_id, payload.balance)

    decision_id = payload.decision_id

    # HEALING LOGIC: Se não veio decision_id, tenta encontrar pelo ticket ou pelo último Buy/Sell neste símbolo
    if not decision_id:
        try:
            # 1. Tenta pelo ticket já registrado em executed_trades
            find_exec = sb.table("executed_trades").select("trade_decision_id").eq("broker_ticket", payload.ticket).maybeSingle().execute()
            if find_exec.data:
                decision_id = find_exec.data["trade_decision_id"]
            else:
                # 2. Tenta a decisão 'executing' mais recente para este símbolo e robô
                find_dec = sb.table("trade_decisions").select("id").eq("robot_instance_id", payload.robot_id).eq("symbol", payload.symbol).eq("outcome_status", "executing").order("created_at", { "ascending": False }).limit(1).execute()
                if find_dec.data:
                    decision_id = find_dec.data[0]["id"]
        except:
            pass

    if not decision_id:
        return {"status": "ignored", "message": "Could not link outcome to any decision"}
    try:
        # 1. Busca dados da decisão para duração e preços de referência
        dec_res = sb.table("trade_decisions").select(
            "created_at, entry_price, stop_loss, take_profit, robot_instance_id"
        ).eq("id", payload.decision_id).single().execute()

        now_utc = datetime.now(timezone.utc)
        duration_secs = 0
        entry_price = None
        stop_loss = None
        take_profit = None
        if dec_res.data:
            if dec_res.data.get("created_at"):
                created_at = datetime.fromisoformat(dec_res.data["created_at"].replace("Z", "+00:00"))
                duration_secs = int((now_utc - created_at).total_seconds())
            entry_price = dec_res.data.get("entry_price")
            stop_loss = dec_res.data.get("stop_loss")
            take_profit = dec_res.data.get("take_profit")

        outcome_status = "win" if payload.profit > 0 else "loss" if payload.profit < 0 else "neutral"
        result_label  = "win" if payload.profit > 0 else "loss" if payload.profit < 0 else "breakeven"

        # 2. Atualiza trade_decisions com resultado final
        sb.table("trade_decisions").update({
            "outcome_status":   outcome_status,
            "outcome_pips":     payload.points,
            "outcome_profit":   payload.profit,
            "closed_at":        now_utc.isoformat(),
            "duration_seconds": duration_secs,
        }).eq("id", payload.decision_id).execute()

        # 3. Busca ou cria executed_trade para este decision_id
        existing = sb.table("executed_trades").select("id").eq(
            "trade_decision_id", payload.decision_id
        ).execute()

        if existing.data:
            executed_trade_id = existing.data[0]["id"]
            sb.table("executed_trades").update({
                "status":      "closed",
                "closed_at":   now_utc.isoformat(),
                "broker_ticket": payload.ticket or None,
            }).eq("id", executed_trade_id).execute()
        else:
            # Trade fechado sem ter passado pelo /trade-opened (edge case)
            ins = sb.table("executed_trades").insert({
                "organization_id":   payload.organization_id,
                "robot_instance_id": payload.robot_id,
                "trade_decision_id": payload.decision_id,
                "broker_ticket":     payload.ticket or None,
                "entry_price":       entry_price,
                "stop_loss":         stop_loss,
                "take_profit":       take_profit,
                "status":            "closed",
                "opened_at":         now_utc.isoformat(),
                "closed_at":         now_utc.isoformat(),
            }).execute()
            executed_trade_id = ins.data[0]["id"] if ins.data else None

        # 4. Cria trade_outcomes (apenas se não houver duplicata)
        if executed_trade_id:
            has_outcome = sb.table("trade_outcomes").select("id").eq(
                "executed_trade_id", executed_trade_id
            ).execute()
            if not has_outcome.data:
                sb.table("trade_outcomes").insert({
                    "organization_id":   payload.organization_id,
                    "robot_instance_id": payload.robot_id,
                    "executed_trade_id": executed_trade_id,
                    "result":            result_label,
                    "pnl_money":         payload.profit,
                    "pnl_points":        float(payload.points),
                    "win_loss_reason":   f"MT5 ticket {payload.ticket}",
                }).execute()

        _mark_cycle_closed(sb, payload.decision_id, payload.profit, payload.points, result_label)

        log.info(
            "Resultado real processado: %s -> %s (PnL: %.2f, Dur: %ds)",
            payload.decision_id, outcome_status, payload.profit, duration_secs,
        )
        return {"status": "success", "message": "Outcome updated with performance data"}
    except Exception as exc:
        log.error("Failed to update trade outcome: %s", exc)
        raise HTTPException(status_code=500, detail="Database update failed")


@router.post("/trade-opened", summary="Reportar abertura imediata de trade")
async def trade_opened(payload: TradeOpenedPayload):
    """Confirma abertura e sincroniza saldo com a nova margem."""
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)
    sb = get_service_supabase()
    _sync_robot_data(sb, payload.robot_id, payload.balance)
    try:
        now_utc = datetime.now(timezone.utc).isoformat()

        # 1. Atualiza trade_decisions para 'executing' com preços reais do MT5
        sb.table("trade_decisions").update({
            "outcome_status": "executing",
            "entry_price":    payload.price,
            "stop_loss":      payload.sl if payload.sl > 0 else None,
            "take_profit":    payload.tp if payload.tp > 0 else None,
        }).eq("id", payload.decision_id).execute()

        # 2. Cria executed_trade (evita duplicata por idempotência)
        existing = sb.table("executed_trades").select("id").eq(
            "trade_decision_id", payload.decision_id
        ).execute()
        if not existing.data:
            sb.table("executed_trades").insert({
                "organization_id":   payload.organization_id,
                "robot_instance_id": payload.robot_id,
                "trade_decision_id": payload.decision_id,
                "broker_ticket":     payload.ticket,
                "entry_price":       payload.price,
                "stop_loss":         payload.sl if payload.sl > 0 else None,
                "take_profit":       payload.tp if payload.tp > 0 else None,
                "lot":               payload.lot if payload.lot > 0 else None,
                "status":            "open",
                "opened_at":         now_utc,
            }).execute()

        _mark_cycle_executed(sb, payload.decision_id, payload.ticket, payload.price)

        log.info(
            "Trade aberto confirmado: %s (Ticket: %s, Price: %.5f)",
            payload.decision_id, payload.ticket, payload.price,
        )
        return {"status": "success", "message": "Trade marked as executing"}
    except Exception as exc:
        log.error("Failed to mark trade as opened: %s", exc)
        raise HTTPException(status_code=500, detail="Database update failed")
