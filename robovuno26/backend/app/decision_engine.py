from __future__ import annotations

from .models import DecisionResponse, SnapshotRequest, normalize_decision_engine_mode_value
from .price_action import analyze_price_action_context, evaluate_open_position_management, evaluate_price_action


def clamp_risk(value: float) -> float:
    if value <= 0:
        return 0.0
    if value > 1.0:
        return 1.0
    return round(value, 2)


def safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candle_signature(candle) -> tuple[float, float, float, float]:
    return (
        round(float(candle.open), 6),
        round(float(candle.high), 6),
        round(float(candle.low), 6),
        round(float(candle.close), 6),
    )


def _normalize_memory_token(value: object, fallback: str = "na") -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    return token or fallback


def _build_memory_context_key(signal: str, analysis: dict[str, object]) -> str:
    timeframe = str(analysis.get("observed_timeframe") or "NA").upper()
    setup = _normalize_memory_token(analysis.get("setup") or analysis.get("engine"), "setup")
    zone = _normalize_memory_token(analysis.get("zone_type"), "neutral")
    structure = _normalize_memory_token(analysis.get("structure_state") or analysis.get("state"), "neutral")
    fib_state = "fib" if analysis.get("fib_in_retracement_zone") or analysis.get("fib_near_retracement_zone") else "nofib"
    return f"{timeframe}|{setup}|{zone}|{structure}|{str(signal or 'HOLD').upper()}|{fib_state}"


def _assess_market_data(snapshot: SnapshotRequest) -> dict[str, object]:
    window = snapshot.candles[-12:]
    if not window:
        return {"tradable": True, "reasons": [], "checked_candles": 0, "identical_tail": 0, "unique_candles": 0, "flat_candles": 0, "recent_range": 0.0}

    signatures = [_candle_signature(candle) for candle in window]
    unique_candles = len(set(signatures))
    identical_tail = 1
    for index in range(len(signatures) - 2, -1, -1):
        if signatures[index] != signatures[-1]:
            break
        identical_tail += 1

    spread_range = abs(float(snapshot.ask) - float(snapshot.bid))
    flat_threshold = max(spread_range * 0.6, max(abs(float(snapshot.close)), 1.0) * 0.000005)
    flat_candles = sum(1 for candle in window if abs(float(candle.high) - float(candle.low)) <= flat_threshold)
    recent_range = round(max(float(candle.high) for candle in window) - min(float(candle.low) for candle in window), 6)

    reasons: list[str] = []
    if len(window) >= 6 and identical_tail >= 6:
        reasons.append("dados_repetidos")
    if len(window) >= 8 and unique_candles <= 2:
        reasons.append("feed_congelado")
    if len(window) >= 8 and flat_candles >= max(6, int(len(window) * 0.75)) and recent_range <= max(spread_range * 3.0, max(abs(float(snapshot.close)), 1.0) * 0.00003):
        reasons.append("ativo_parado")

    return {
        "tradable": not reasons,
        "reasons": reasons,
        "checked_candles": len(window),
        "identical_tail": identical_tail,
        "unique_candles": unique_candles,
        "flat_candles": flat_candles,
        "recent_range": recent_range,
    }


def _risk_guard(snapshot: SnapshotRequest) -> DecisionResponse | None:
    if snapshot.spread_points > 30:
        return DecisionResponse(
            signal="HOLD",
            confidence=0.95,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale="spread_alto",
            reason="spread_alto",
            analysis={
                "engine": "risk_guard",
                "trigger": "spread_alto",
                "spread_points": snapshot.spread_points,
            },
        )

    return None


def _market_data_guard(snapshot: SnapshotRequest, market_data: dict[str, object]) -> DecisionResponse | None:
    if bool(market_data.get("tradable", True)):
        return None

    return DecisionResponse(
        signal="HOLD",
        confidence=0.97,
        risk=0.0,
        stop_loss_points=0,
        take_profit_points=0,
        rationale="market_data_quality_guard",
        reason="market_data_quality_guard",
        analysis={
            "engine": "market_data_guard",
            "trigger": "market_data_quality",
            "data_quality_reasons": list(market_data.get("reasons", [])),
            "checked_candles": int(market_data.get("checked_candles", 0)),
            "identical_tail": int(market_data.get("identical_tail", 0)),
            "unique_candles": int(market_data.get("unique_candles", 0)),
            "flat_candles": int(market_data.get("flat_candles", 0)),
            "recent_range": float(market_data.get("recent_range", 0.0)),
            "spread_points": snapshot.spread_points,
        },
    )


def _price_action_only_hold(snapshot: SnapshotRequest) -> DecisionResponse:
    context = analyze_price_action_context(snapshot)
    analysis = {
        "engine": "price_action_only_guard",
        "trigger": "price_action_sem_confluencia",
        "setup": context["pattern"]["name"] if context["pattern"] else None,
        "setup_score": context["score"],
        "zone_type": context["zones"]["zone_type"],
        "zone_low": context["zone_low"],
        "zone_high": context["zone_high"],
        "structure_state": context["structure"]["state"],
        "higher_state": context["structure"]["higher_state"],
        "invalidation_reason": context["invalidation_reason"],
        "checklist": context["checklist"],
        "checklist_passed": False,
    }
    return DecisionResponse(
        signal="HOLD",
        confidence=0.9,
        risk=0.0,
        stop_loss_points=0,
        take_profit_points=0,
        rationale="price_action_sem_confluencia",
        reason="price_action_sem_confluencia",
        analysis=analysis,
    )


def _legacy_decision(snapshot: SnapshotRequest) -> DecisionResponse:
    signal = "HOLD"
    confidence = 0.45
    risk = 0.2
    rationale = "sem_vantagem_clara"

    trend_strength = abs(snapshot.ema_fast - snapshot.ema_slow)
    sl_points = 180
    tp_points = 360

    if snapshot.ema_fast > snapshot.ema_slow and snapshot.rsi < 68:
        signal = "BUY"
        confidence = 0.55 + min(trend_strength / max(snapshot.close, 1e-6), 0.2)
        risk = 0.35
        rationale = "tendencia_alta"
    elif snapshot.ema_fast < snapshot.ema_slow and snapshot.rsi > 32:
        signal = "SELL"
        confidence = 0.55 + min(trend_strength / max(snapshot.close, 1e-6), 0.2)
        risk = 0.35
        rationale = "tendencia_baixa"

    return DecisionResponse(
        signal=signal,
        confidence=round(max(0.05, min(confidence, 0.99)), 2),
        risk=clamp_risk(risk),
        stop_loss_points=sl_points if signal != "HOLD" else 0,
        take_profit_points=tp_points if signal != "HOLD" else 0,
        rationale=rationale,
        reason=rationale,
        analysis={
            "engine": "legacy_v1",
            "trend_strength": round(trend_strength, 6),
            "ema_fast": snapshot.ema_fast,
            "ema_slow": snapshot.ema_slow,
            "rsi": snapshot.rsi,
            "candles_available": len(snapshot.candles),
        },
    )


def _apply_local_memory_adjustments(snapshot: SnapshotRequest, decision: DecisionResponse) -> DecisionResponse:
    if decision.signal == "HOLD":
        return decision

    local_memory = snapshot.local_memory or {}
    recent_win_rate = safe_float(local_memory.get("recent_win_rate", 0.5), 0.5)
    recent_pnl = safe_float(local_memory.get("recent_pnl", 0.0), 0.0)

    if recent_win_rate < 0.45:
        decision.risk -= 0.1
        decision.confidence -= 0.05
        decision.rationale += "_com_memoria_defensiva"
        decision.reason = decision.rationale

    if recent_pnl < 0:
        decision.risk -= 0.05

    analysis = dict(decision.analysis or {})
    setup_key = str(analysis.get("setup") or analysis.get("engine") or "").strip()
    current_context_key = str(local_memory.get("current_context_key") or _build_memory_context_key(decision.signal, analysis)).strip()
    raw_setup_stats = local_memory.get("setup_stats") or {}
    raw_context_stats = local_memory.get("context_stats") or {}
    setup_stats = raw_setup_stats.get(setup_key, {}) if isinstance(raw_setup_stats, dict) and setup_key else {}
    context_stats = raw_context_stats.get(current_context_key, {}) if isinstance(raw_context_stats, dict) and current_context_key else {}
    memory_adjustments: list[str] = []

    setup_trades = safe_float(setup_stats.get("recent_trades", 0.0), 0.0)
    setup_win_rate = safe_float(setup_stats.get("recent_win_rate", 0.5), 0.5)
    setup_pnl = safe_float(setup_stats.get("recent_pnl", 0.0), 0.0)
    if setup_trades >= 3:
        if setup_win_rate < 0.4 or setup_pnl < 0:
            decision.risk -= 0.08
            decision.confidence -= 0.04
            memory_adjustments.append("setup_defensivo")
        elif setup_win_rate >= 0.65 and setup_pnl > 0:
            decision.confidence += 0.03
            memory_adjustments.append("setup_favoravel")

    context_trades = safe_float(context_stats.get("recent_trades", 0.0), 0.0)
    context_win_rate = safe_float(context_stats.get("recent_win_rate", 0.5), 0.5)
    context_pnl = safe_float(context_stats.get("recent_pnl", 0.0), 0.0)
    if context_trades >= 3:
        if context_win_rate < 0.4 or context_pnl < 0:
            decision.risk -= 0.05
            decision.confidence -= 0.03
            memory_adjustments.append("contexto_defensivo")
        elif context_win_rate >= 0.65 and context_pnl > 0:
            decision.confidence += 0.02
            memory_adjustments.append("contexto_favoravel")

    analysis["recent_win_rate"] = round(recent_win_rate, 4)
    analysis["recent_pnl"] = round(recent_pnl, 4)
    analysis["memory_mode"] = "defensive" if recent_win_rate < 0.45 else "normal"
    if setup_key:
        analysis["setup_memory"] = {
            "setup": setup_key,
            "recent_trades": round(setup_trades, 2),
            "recent_win_rate": round(setup_win_rate, 4),
            "recent_pnl": round(setup_pnl, 2),
        }
    if current_context_key:
        analysis["context_memory"] = {
            "context_key": current_context_key,
            "recent_trades": round(context_trades, 2),
            "recent_win_rate": round(context_win_rate, 4),
            "recent_pnl": round(context_pnl, 2),
        }
    if memory_adjustments:
        analysis["memory_adjustments"] = memory_adjustments
    decision.analysis = analysis
    decision.confidence = round(max(0.05, min(decision.confidence, 0.99)), 2)
    decision.risk = clamp_risk(decision.risk)
    return decision


def evaluate_snapshot(
    snapshot: SnapshotRequest,
    decision_engine_mode: str = "HYBRID",
    management_settings: dict[str, object] | None = None,
) -> DecisionResponse:
    market_data = _assess_market_data(snapshot)

    if snapshot.open_positions > 0:
        decision = evaluate_open_position_management(
            snapshot,
            market_data_quality=market_data,
            management_settings=management_settings,
        )
        decision.analysis = dict(decision.analysis or {})
        decision.analysis["engine_requested"] = normalize_decision_engine_mode_value(decision_engine_mode)
        return decision

    guarded = _risk_guard(snapshot)
    if guarded is not None:
        return guarded

    market_guard = _market_data_guard(snapshot, market_data)
    if market_guard is not None:
        market_guard.analysis = dict(market_guard.analysis or {})
        market_guard.analysis["engine_requested"] = normalize_decision_engine_mode_value(decision_engine_mode)
        return market_guard

    mode = normalize_decision_engine_mode_value(decision_engine_mode)
    price_action_decision = evaluate_price_action(snapshot) if mode != "LEGACY_ONLY" else None

    if mode == "PRICE_ACTION_ONLY":
        decision = price_action_decision or _price_action_only_hold(snapshot)
    elif mode == "LEGACY_ONLY":
        decision = _legacy_decision(snapshot)
    else:
        decision = price_action_decision or _legacy_decision(snapshot)

    decision.analysis = dict(decision.analysis or {})
    decision.analysis["engine_requested"] = mode
    return _apply_local_memory_adjustments(snapshot, decision)
