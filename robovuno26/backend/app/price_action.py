from __future__ import annotations

from datetime import datetime, timezone

from .models import DecisionResponse, SnapshotRequest
from .price_action_fibonacci import analyze_fibonacci
from .price_action_patterns import detect_primary_pattern
from .price_action_structure import analyze_structure
from .price_action_zones import analyze_zones


def _clamp_score(value: float) -> float:
    if value <= 0:
        return 0.0
    if value >= 0.99:
        return 0.99
    return round(value, 2)


def _price_point(snapshot: SnapshotRequest) -> float:
    max_decimals = 0
    for price in (snapshot.bid, snapshot.ask, snapshot.close):
        text = f"{float(price):.10f}".rstrip("0").rstrip(".")
        if "." not in text:
            continue
        max_decimals = max(max_decimals, len(text.split(".", 1)[1]))
    return 10 ** (-max_decimals) if max_decimals else 1.0


def _points_between(snapshot: SnapshotRequest, price_a: float | None, price_b: float | None) -> int:
    if price_a is None or price_b is None:
        return 0
    point = _price_point(snapshot)
    if point <= 0:
        return 0
    return max(int(round(abs(float(price_a) - float(price_b)) / point)), 0)


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _direction_to_signal(direction: str) -> str:
    return "BUY" if direction == "bullish" else "SELL"


def _opposite_direction(direction: str) -> str:
    return "bearish" if direction == "bullish" else "bullish"


def _parse_snapshot_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        parsed = None

    if parsed is None:
        for pattern in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(raw, pattern)
                break
            except ValueError:
                continue

    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _elapsed_minutes(start_value: str | None, end_value: str | None) -> int | None:
    start_dt = _parse_snapshot_datetime(start_value)
    end_dt = _parse_snapshot_datetime(end_value)
    if start_dt is None or end_dt is None or end_dt < start_dt:
        return None
    return int((end_dt - start_dt).total_seconds() // 60)


def _assess_position_stagnation(snapshot: SnapshotRequest, window_size: int) -> dict[str, object]:
    window = snapshot.candles[-window_size:]
    if len(window) < window_size:
        return {
            "window_size": len(window),
            "range_points": 0,
            "net_progress_points": 0,
            "stalled": False,
        }

    range_points = _points_between(
        snapshot,
        max(float(candle.high) for candle in window),
        min(float(candle.low) for candle in window),
    )
    net_progress_points = _points_between(snapshot, float(window[0].close), float(window[-1].close))
    stalled = (
        range_points <= max(int(round(snapshot.spread_points * 6.0)), 12)
        and net_progress_points <= max(int(round(snapshot.spread_points * 2.0)), 4)
    )

    return {
        "window_size": len(window),
        "range_points": range_points,
        "net_progress_points": net_progress_points,
        "stalled": stalled,
    }


def _build_structural_protection(
    snapshot: SnapshotRequest,
    direction: str,
    entry_price: float,
    current_price: float,
    window_size: int,
) -> float | None:
    window = snapshot.candles[-window_size:]
    if not window:
        return None

    point = _price_point(snapshot)
    buffer_price = max(snapshot.spread_points * 1.5, 2.0) * point
    if direction == "bullish":
        structural_price = min(float(candle.low) for candle in window) - (point * 2)
        candidate = max(entry_price + buffer_price, structural_price)
        limit = current_price - (point * 2)
        if candidate >= limit:
            return None
        return _round_price(candidate)

    structural_price = max(float(candle.high) for candle in window) + (point * 2)
    candidate = min(entry_price - buffer_price, structural_price)
    limit = current_price + (point * 2)
    if candidate <= limit:
        return None
    return _round_price(candidate)


def analyze_price_action_context(snapshot: SnapshotRequest) -> dict[str, object]:
    candles = snapshot.candles
    zones = analyze_zones(candles)
    structure = analyze_structure(candles, snapshot.htf_candles)
    pattern = detect_primary_pattern(candles) if len(candles) >= 8 else None
    direction = str(pattern["direction"]) if pattern else str(structure["breakout_bias"])
    if direction not in {"bullish", "bearish"}:
        direction = "none"
    fibonacci = analyze_fibonacci(candles, direction if direction in {"bullish", "bearish"} else str(structure["breakout_bias"]))

    zone_ok = direction in {"bullish", "bearish"} and (
        (direction == "bullish" and zones["zone_type"] in {"support", "range_low"})
        or (direction == "bearish" and zones["zone_type"] in {"resistance", "range_high"})
    )
    structure_ok = direction in {"bullish", "bearish"} and (
        (direction == "bullish" and structure["higher_state"] != "bearish")
        or (direction == "bearish" and structure["higher_state"] != "bullish")
    )

    if pattern and str(pattern["name"]) == "inside_bar" and str(structure["breakout_bias"]) not in {direction, "none"}:
        structure_ok = False
    if direction == "bullish" and structure["choch_signal"] == "bearish":
        structure_ok = False
    if direction == "bearish" and structure["choch_signal"] == "bullish":
        structure_ok = False

    score = (
        float(zones["zone_score"]) * 0.38
        + float(structure["structure_score"]) * 0.34
        + float(fibonacci["fib_score"]) * 0.28
    )
    if pattern:
        score = (
            float(pattern["strength"]) * 0.38
            + float(zones["zone_score"]) * 0.27
            + float(structure["structure_score"]) * 0.20
            + float(fibonacci["fib_score"]) * 0.15
        )
    if direction in {"bullish", "bearish"} and direction == str(structure["bos_signal"]):
        score += 0.08
    if direction in {"bullish", "bearish"} and direction == str(structure["choch_signal"]):
        score += 0.06
    if direction in {"bullish", "bearish"} and direction == str(structure["false_breakout_signal"]):
        score += 0.07
    if direction in {"bullish", "bearish"} and direction == str(zones["false_breakout_signal"]):
        score += 0.06
    if direction == "bullish" and int(zones["support_touches"]) >= 3:
        score += 0.05
    if direction == "bearish" and int(zones["resistance_touches"]) >= 3:
        score += 0.05
    if direction in {"bullish", "bearish"} and fibonacci["direction"] == direction:
        if fibonacci["in_retracement_zone"]:
            score += 0.08
        elif fibonacci["near_retracement_zone"]:
            score += 0.04
        else:
            score -= 0.03
    if not zone_ok and direction in {"bullish", "bearish"}:
        score -= 0.25
    if not structure_ok and direction in {"bullish", "bearish"}:
        score -= 0.20
    if snapshot.spread_points > 20:
        score -= 0.10
    score = _clamp_score(score)

    support = zones["support"] if zones["support"] is not None else None
    resistance = zones["resistance"] if zones["resistance"] is not None else None
    tolerance = float(zones["tolerance"])
    zone_low = _round_price((float(support) - tolerance) if support is not None else None)
    zone_high = _round_price((float(resistance) + tolerance) if resistance is not None else None)

    current_price = float(snapshot.close)
    point = _price_point(snapshot)
    minimum_stop_points = max(int(round(snapshot.spread_points * 3)), 1)
    stop_loss_price = None
    take_profit_price = None
    stop_loss_points = 0
    take_profit_points = 0

    fib_stop = fibonacci["stop_reference_price"]
    fib_target = fibonacci["target_price_1272"]

    if direction == "bullish":
        stop_candidates = []
        if support is not None:
            stop_candidates.append(float(support) - tolerance)
        if fib_stop is not None:
            stop_candidates.append(float(fib_stop) - tolerance)
        target_candidates = []
        if resistance is not None and float(resistance) > current_price:
            target_candidates.append(float(resistance))
        if fib_target is not None and float(fib_target) > current_price:
            target_candidates.append(float(fib_target))
        stop_loss_price = _round_price(min(stop_candidates) if stop_candidates else current_price - (point * 30))
        take_profit_price = _round_price(min(target_candidates)) if target_candidates else None
    elif direction == "bearish":
        stop_candidates = []
        if resistance is not None:
            stop_candidates.append(float(resistance) + tolerance)
        if fib_stop is not None:
            stop_candidates.append(float(fib_stop) + tolerance)
        target_candidates = []
        if support is not None and float(support) < current_price:
            target_candidates.append(float(support))
        if fib_target is not None and float(fib_target) < current_price:
            target_candidates.append(float(fib_target))
        stop_loss_price = _round_price(max(stop_candidates) if stop_candidates else current_price + (point * 30))
        take_profit_price = _round_price(max(target_candidates)) if target_candidates else None

    if direction in {"bullish", "bearish"}:
        stop_loss_points = max(_points_between(snapshot, current_price, stop_loss_price), minimum_stop_points)
        take_profit_points = max(_points_between(snapshot, current_price, take_profit_price), int(stop_loss_points * 2))
        if direction == "bullish":
            take_profit_price = _round_price(current_price + (take_profit_points * point))
        else:
            take_profit_price = _round_price(current_price - (take_profit_points * point))

    checklist = {
        "pattern_detected": bool(pattern),
        "zone_ok": bool(zone_ok),
        "structure_ok": bool(structure_ok),
        "spread_ok": snapshot.spread_points <= 20,
        "score_ok": score >= 0.62,
    }
    invalidation_reason = ""
    if not pattern:
        invalidation_reason = "sem_padrao_confirmado"
    elif not zone_ok:
        invalidation_reason = "fora_da_zona_de_interesse"
    elif not structure_ok:
        invalidation_reason = "estrutura_contraria"
    elif score < 0.62:
        invalidation_reason = "score_abaixo_do_minimo"

    return {
        "pattern": pattern,
        "zones": zones,
        "structure": structure,
        "fibonacci": fibonacci,
        "direction": direction,
        "score": score,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "stop_loss_price": stop_loss_price,
        "take_profit_price": take_profit_price,
        "stop_loss_points": stop_loss_points,
        "take_profit_points": take_profit_points,
        "valid_entry": bool(pattern) and zone_ok and structure_ok and score >= 0.62,
        "checklist": checklist,
        "invalidation_reason": invalidation_reason,
    }


def _build_analysis(snapshot: SnapshotRequest, context: dict[str, object]) -> dict[str, object]:
    pattern = context["pattern"]
    zones = context["zones"]
    structure = context["structure"]
    fibonacci = context["fibonacci"]
    direction = context["direction"]
    checklist = context["checklist"]
    return {
        "engine": "price_action_v1",
        "setup": pattern["name"] if pattern else None,
        "setup_label": pattern["label"] if pattern else None,
        "setup_direction": direction,
        "setup_strength": pattern["strength"] if pattern else None,
        "setup_score": context["score"],
        "zone_type": zones["zone_type"],
        "zone_low": context["zone_low"],
        "zone_high": context["zone_high"],
        "support": zones["support"],
        "resistance": zones["resistance"],
        "support_touches": zones["support_touches"],
        "resistance_touches": zones["resistance_touches"],
        "zone_false_breakout_signal": zones["false_breakout_signal"],
        "fib_direction": fibonacci["direction"],
        "fib_anchor_source": fibonacci["anchor_source"],
        "fib_score": fibonacci["fib_score"],
        "fib_entry_zone_label": fibonacci["entry_zone_label"],
        "fib_entry_zone_low": fibonacci["entry_zone_low"],
        "fib_entry_zone_high": fibonacci["entry_zone_high"],
        "fib_retracement_382": fibonacci["retracement_382"],
        "fib_retracement_500": fibonacci["retracement_500"],
        "fib_retracement_618": fibonacci["retracement_618"],
        "fib_target_1272": fibonacci["target_price_1272"],
        "fib_target_1618": fibonacci["target_price_1618"],
        "fib_in_retracement_zone": fibonacci["in_retracement_zone"],
        "fib_near_retracement_zone": fibonacci["near_retracement_zone"],
        "structure_state": structure["state"],
        "higher_state": structure["higher_state"],
        "breakout_bias": structure["breakout_bias"],
        "bos_signal": structure["bos_signal"],
        "choch_signal": structure["choch_signal"],
        "structure_false_breakout_signal": structure["false_breakout_signal"],
        "trigger_type": pattern["name"] if pattern else structure["breakout_bias"],
        "invalidation_reason": context["invalidation_reason"],
        "checklist": checklist,
        "checklist_passed": all(checklist.values()),
        "score": context["score"],
        "planned_stop_loss_price": context["stop_loss_price"],
        "planned_take_profit_price": context["take_profit_price"],
        "planned_stop_loss_points": context["stop_loss_points"],
        "planned_take_profit_points": context["take_profit_points"],
    }


def evaluate_price_action(snapshot: SnapshotRequest) -> DecisionResponse | None:
    context = analyze_price_action_context(snapshot)
    if not context["valid_entry"]:
        return None

    signal = _direction_to_signal(str(context["direction"]))
    rationale = (
        f"pa_{(context['pattern'] or {'name': 'contexto'})['name']}_{context['zones']['zone_type']}_{context['structure']['state']}"
        f"_score_{str(context['score']).replace('.', '_')}"
    )
    return DecisionResponse(
        signal=signal,
        confidence=float(context["score"]),
        risk=round(min(0.55, 0.2 + (float(context["score"]) * 0.25)), 2),
        stop_loss_points=int(context["stop_loss_points"]),
        take_profit_points=int(context["take_profit_points"]),
        rationale=rationale,
        reason=rationale,
        analysis=_build_analysis(snapshot, context),
    )


def _position_reversal_reasons(direction: str, context: dict[str, object]) -> list[str]:
    opposite = _opposite_direction(direction)
    pattern = context["pattern"]
    zones = context["zones"]
    structure = context["structure"]
    fibonacci = context["fibonacci"]
    reasons: list[str] = []
    if structure["choch_signal"] == opposite:
        reasons.append(f"choch_{opposite}")
    if structure["false_breakout_signal"] == opposite:
        reasons.append(f"false_breakout_{opposite}")
    if zones["false_breakout_signal"] == opposite:
        reasons.append(f"zone_false_breakout_{opposite}")
    if pattern and pattern["direction"] == opposite and float(context["score"]) >= 0.55:
        reasons.append(f"pattern_{pattern['name']}_{opposite}")
    if context["direction"] == opposite and (fibonacci["in_retracement_zone"] or fibonacci["near_retracement_zone"]):
        reasons.append(f"fibonacci_{opposite}")
    if direction == "bullish" and zones["zone_type"] in {"resistance", "range_high"}:
        reasons.append("rejeicao_em_resistencia")
    if direction == "bearish" and zones["zone_type"] in {"support", "range_low"}:
        reasons.append("rejeicao_em_suporte")
    return reasons


def evaluate_open_position_management(
    snapshot: SnapshotRequest,
    market_data_quality: dict[str, object] | None = None,
    management_settings: dict[str, object] | None = None,
) -> DecisionResponse:
    settings = management_settings or {}
    break_even_trigger_points = max(int(settings.get("break_even_trigger_points", 8) or 8), 0)
    trailing_trigger_points = max(int(settings.get("trailing_trigger_points", 14) or 14), break_even_trigger_points)
    time_stop_minutes = max(int(settings.get("position_time_stop_minutes", 90) or 0), 0)
    stagnation_window = max(int(settings.get("position_stagnation_window_candles", 6) or 6), 3)
    base_analysis = {
        "engine": "position_manager_v1",
        "entry_blocked_due_to_open_position": True,
        "open_positions": snapshot.open_positions,
        "open_position_ticket": snapshot.open_position_ticket,
        "open_position_direction": snapshot.open_position_direction,
        "open_position_opened_at": snapshot.open_position_opened_at,
        "open_position_profit": snapshot.open_position_profit,
        "open_position_profit_points": snapshot.open_position_profit_points,
        "break_even_trigger_points": break_even_trigger_points,
        "trailing_trigger_points": trailing_trigger_points,
        "position_time_stop_minutes": time_stop_minutes,
        "position_stagnation_window_candles": stagnation_window,
    }

    if market_data_quality and not bool(market_data_quality.get("tradable", True)):
        analysis = {
            **base_analysis,
            "management_action": "NONE",
            "management_reasons": list(market_data_quality.get("reasons", [])),
            "data_quality_guard_active": True,
            "data_quality_reasons": list(market_data_quality.get("reasons", [])),
            "checked_candles": int(market_data_quality.get("checked_candles", 0)),
            "identical_tail": int(market_data_quality.get("identical_tail", 0)),
            "unique_candles": int(market_data_quality.get("unique_candles", 0)),
            "flat_candles": int(market_data_quality.get("flat_candles", 0)),
            "recent_range": float(market_data_quality.get("recent_range", 0.0)),
        }
        rationale = "manage_hold_market_data_guard"
        return DecisionResponse(
            signal="HOLD",
            confidence=0.86,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale=rationale,
            reason=rationale,
            analysis=analysis,
        )

    context = analyze_price_action_context(snapshot)
    analysis = _build_analysis(snapshot, context)
    analysis.update(base_analysis)

    position_signal = str(snapshot.open_position_direction or "").upper().strip()
    if position_signal not in {"BUY", "SELL"}:
        rationale = "manage_open_position_sem_detalhe"
        analysis["management_action"] = "NONE"
        return DecisionResponse(
            signal="HOLD",
            confidence=0.75,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale=rationale,
            reason=rationale,
            analysis=analysis,
        )

    direction = "bullish" if position_signal == "BUY" else "bearish"
    point = _price_point(snapshot)
    profit_points = float(snapshot.open_position_profit_points or 0.0)
    current_sl = snapshot.open_position_stop_loss
    current_tp = snapshot.open_position_take_profit
    entry_price = snapshot.open_position_entry_price
    current_price = float(snapshot.open_position_current_price or snapshot.close)
    elapsed_minutes = _elapsed_minutes(snapshot.open_position_opened_at, snapshot.captured_at)
    stagnation = _assess_position_stagnation(snapshot, stagnation_window)
    reversal_reasons = _position_reversal_reasons(direction, context)
    time_stop_triggered = (
        elapsed_minutes is not None
        and time_stop_minutes > 0
        and elapsed_minutes >= time_stop_minutes
        and profit_points >= max(snapshot.spread_points * 2.0, 2.0)
        and (bool(stagnation["stalled"]) or context["direction"] not in {direction, "none"})
    )
    analysis["open_position_elapsed_minutes"] = elapsed_minutes
    analysis["stagnation_window_size"] = stagnation["window_size"]
    analysis["stagnation_range_points"] = stagnation["range_points"]
    analysis["stagnation_net_progress_points"] = stagnation["net_progress_points"]
    analysis["stagnation_detected"] = bool(stagnation["stalled"])
    analysis["time_stop_triggered"] = time_stop_triggered

    if profit_points > 0 and reversal_reasons:
        rationale = "manage_close_profit_on_reversal"
        analysis["management_action"] = "CLOSE"
        management_reasons = list(reversal_reasons)
        if time_stop_triggered and "time_stop" not in management_reasons:
            management_reasons.append("time_stop")
        if bool(stagnation["stalled"]) and "estagnacao" not in management_reasons:
            management_reasons.append("estagnacao")
        analysis["management_reasons"] = management_reasons
        return DecisionResponse(
            signal="HOLD",
            confidence=0.92,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale=rationale,
            reason=rationale,
            analysis=analysis,
            position_action="CLOSE",
            position_ticket=snapshot.open_position_ticket,
        )

    if time_stop_triggered:
        rationale = "manage_close_time_stop"
        analysis["management_action"] = "CLOSE"
        reasons = ["time_stop"]
        if bool(stagnation["stalled"]):
            reasons.append("estagnacao")
        analysis["management_reasons"] = reasons
        return DecisionResponse(
            signal="HOLD",
            confidence=0.87,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale=rationale,
            reason=rationale,
            analysis=analysis,
            position_action="CLOSE",
            position_ticket=snapshot.open_position_ticket,
        )

    if (
        bool(stagnation["stalled"])
        and profit_points >= max(float(break_even_trigger_points), snapshot.spread_points * 2.5)
        and context["direction"] not in {direction, "none"}
    ):
        rationale = "manage_close_stagnation"
        analysis["management_action"] = "CLOSE"
        analysis["management_reasons"] = ["estagnacao"]
        return DecisionResponse(
            signal="HOLD",
            confidence=0.84,
            risk=0.0,
            stop_loss_points=0,
            take_profit_points=0,
            rationale=rationale,
            reason=rationale,
            analysis=analysis,
            position_action="CLOSE",
            position_ticket=snapshot.open_position_ticket,
        )

    if profit_points >= trailing_trigger_points and entry_price is not None:
        candidate_sl = _build_structural_protection(
            snapshot,
            direction,
            float(entry_price),
            current_price,
            stagnation_window,
        )
        if direction == "bullish":
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl > float(current_sl) + point
            candidate_tp = context["take_profit_price"] if context["direction"] == direction else current_tp
            better_tp = candidate_tp is not None and (current_tp is None or float(candidate_tp) > float(current_tp) + point)
        else:
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl < float(current_sl) - point
            candidate_tp = context["take_profit_price"] if context["direction"] == direction else current_tp
            better_tp = candidate_tp is not None and (current_tp is None or float(candidate_tp) < float(current_tp) - point)

        if (candidate_sl is not None and better_sl) or better_tp:
            rationale = "manage_trailing_profit"
            analysis["management_action"] = "PROTECT"
            analysis["management_reasons"] = ["trailing_estrutural"]
            return DecisionResponse(
                signal="HOLD",
                confidence=0.9,
                risk=0.0,
                stop_loss_points=0,
                take_profit_points=0,
                rationale=rationale,
                reason=rationale,
                analysis=analysis,
                position_action="PROTECT",
                position_ticket=snapshot.open_position_ticket,
                position_stop_loss=candidate_sl if better_sl else None,
                position_take_profit=candidate_tp if better_tp else None,
            )

    if profit_points >= break_even_trigger_points and entry_price is not None:
        breakeven_buffer_points = max(snapshot.spread_points * 1.5, 2.0)
        if direction == "bullish":
            candidate_sl = _round_price(float(entry_price) + (breakeven_buffer_points * point))
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl > float(current_sl) + point
        else:
            candidate_sl = _round_price(float(entry_price) - (breakeven_buffer_points * point))
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl < float(current_sl) - point

        if better_sl:
            rationale = "manage_break_even"
            analysis["management_action"] = "PROTECT"
            analysis["management_reasons"] = ["breakeven_ativo"]
            analysis["protected_profit_points"] = round(breakeven_buffer_points, 2)
            return DecisionResponse(
                signal="HOLD",
                confidence=0.86,
                risk=0.0,
                stop_loss_points=0,
                take_profit_points=0,
                rationale=rationale,
                reason=rationale,
                analysis=analysis,
                position_action="PROTECT",
                position_ticket=snapshot.open_position_ticket,
                position_stop_loss=candidate_sl,
                position_take_profit=None,
            )

    protect_threshold = max(snapshot.spread_points * 4.0, 12.0)
    if profit_points >= protect_threshold and entry_price is not None:
        protected_profit_points = max(snapshot.spread_points * 2.0, profit_points * 0.4)
        if direction == "bullish":
            candidate_sl = _round_price(float(entry_price) + (protected_profit_points * point))
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl > float(current_sl) + point
            candidate_tp = context["take_profit_price"] if context["direction"] == direction else current_tp
            better_tp = candidate_tp is not None and (current_tp is None or float(candidate_tp) > float(current_tp) + point)
        else:
            candidate_sl = _round_price(float(entry_price) - (protected_profit_points * point))
            better_sl = current_sl is None or candidate_sl is not None and candidate_sl < float(current_sl) - point
            candidate_tp = context["take_profit_price"] if context["direction"] == direction else current_tp
            better_tp = candidate_tp is not None and (current_tp is None or float(candidate_tp) < float(current_tp) - point)

        if better_sl or better_tp:
            rationale = "manage_protect_profit"
            analysis["management_action"] = "PROTECT"
            analysis["management_reasons"] = ["lucro_protegido"]
            analysis["protected_profit_points"] = round(protected_profit_points, 2)
            return DecisionResponse(
                signal="HOLD",
                confidence=0.88,
                risk=0.0,
                stop_loss_points=0,
                take_profit_points=0,
                rationale=rationale,
                reason=rationale,
                analysis=analysis,
                position_action="PROTECT",
                position_ticket=snapshot.open_position_ticket,
                position_stop_loss=candidate_sl if better_sl else None,
                position_take_profit=candidate_tp if better_tp else None,
            )

    rationale = "manage_open_position_hold"
    analysis["management_action"] = "NONE"
    analysis["management_reasons"] = ["monitorando_sem_nova_entrada"]
    return DecisionResponse(
        signal="HOLD",
        confidence=0.78,
        risk=0.0,
        stop_loss_points=0,
        take_profit_points=0,
        rationale=rationale,
        reason=rationale,
        analysis=analysis,
    )
