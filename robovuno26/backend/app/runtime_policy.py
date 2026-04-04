from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .economic_calendar import active_news_events_for_symbol, parse_csv
from .models import DecisionResponse, SnapshotRequest, normalize_decision_engine_mode_value


VALID_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_timeframe(value: object, default: str) -> str:
    timeframe = str(value or default).upper().strip()
    if timeframe not in VALID_TIMEFRAMES:
        return default
    return timeframe


def normalize_decision_engine_mode(value: object, default: str = "HYBRID") -> str:
    try:
        return normalize_decision_engine_mode_value(str(value or default))
    except ValueError:
        return default


def normalize_enabled_flag(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    return bool(value)


def _normalize_symbol_root(symbol: str | None) -> str:
    return "".join(char for char in str(symbol or "").upper().strip() if char.isalnum())


def _looks_like_crypto(symbol_root: str) -> bool:
    if not symbol_root:
        return False
    crypto_quotes = ("USDT", "USDC", "BUSD", "BTC", "ETH")
    crypto_bases = (
        "BTC",
        "ETH",
        "SOL",
        "XRP",
        "ADA",
        "DOGE",
        "BNB",
        "LTC",
        "AVAX",
        "TRX",
    )
    return any(symbol_root.endswith(quote) for quote in crypto_quotes) and any(symbol_root.startswith(base) for base in crypto_bases)


def _looks_like_b3_future(symbol_root: str) -> bool:
    return symbol_root.startswith(("WIN", "WDO", "IND", "DOL")) and len(symbol_root) >= 5


def infer_market_session_family(symbol: str | None, broker_profile: str | None = None) -> str:
    normalized_profile = str(broker_profile or "CUSTOM").upper().strip()
    symbol_root = _normalize_symbol_root(symbol)
    if _looks_like_crypto(symbol_root):
        return "crypto_24x7"
    if normalized_profile == "B3_FUTURES" or _looks_like_b3_future(symbol_root):
        return "b3_futures"
    return "forex_like"


def evaluate_market_session(
    parameters: dict[str, object],
    symbol: str | None = None,
    broker_profile: str | None = None,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    enabled = normalize_enabled_flag(parameters.get("market_session_guard_enabled"), True)
    family = infer_market_session_family(symbol, broker_profile)
    now_value = observed_at or datetime.now(timezone.utc)

    if not enabled or not symbol:
        return {
            "enabled": enabled,
            "open": True,
            "family": family,
            "reason": None,
            "checked_symbol": str(symbol or ""),
        }

    if family == "crypto_24x7":
        return {
            "enabled": enabled,
            "open": True,
            "family": family,
            "reason": None,
            "checked_symbol": str(symbol),
        }

    if family == "b3_futures":
        now_local = now_value.astimezone(ZoneInfo("America/Sao_Paulo"))
        weekday = now_local.weekday()
        minutes = (now_local.hour * 60) + now_local.minute
        is_open = weekday < 5 and (9 * 60 + 5) <= minutes <= (18 * 60 + 25)
    else:
        weekday = now_value.weekday()
        minutes = (now_value.hour * 60) + now_value.minute
        is_open = True
        if weekday == 5:
            is_open = False
        elif weekday == 6 and minutes < (22 * 60 + 5):
            is_open = False
        elif weekday == 4 and minutes >= (21 * 60 + 55):
            is_open = False

    return {
        "enabled": enabled,
        "open": is_open,
        "family": family,
        "reason": None if is_open else "market_session_closed",
        "checked_symbol": str(symbol),
    }


def _configured_news_symbols(parameters: dict[str, object]) -> list[str]:
    return parse_csv(str(parameters.get("news_pause_symbols", "")))


def _uses_wildcard(symbols: list[str]) -> bool:
    return "*" in symbols or "ALL" in symbols


def evaluate_live_mode_news_gate(
    parameters: dict[str, object],
    tracked_symbols: list[str] | None = None,
) -> dict[str, object]:
    enabled = bool(parameters.get("news_pause_enabled", False))
    configured_symbols = _configured_news_symbols(parameters)
    wildcard = _uses_wildcard(configured_symbols)
    required_symbols = [str(symbol).strip().upper() for symbol in (tracked_symbols or []) if str(symbol).strip()]

    uncovered_symbols: list[str] = []
    if enabled and not wildcard and required_symbols:
        uncovered_symbols = [symbol for symbol in required_symbols if symbol not in configured_symbols]

    passed = enabled and bool(configured_symbols) and (wildcard or not required_symbols or not uncovered_symbols)
    reason = None
    if not enabled:
        reason = "news_pause_disabled"
    elif not configured_symbols:
        reason = "news_pause_without_symbols"
    elif uncovered_symbols:
        reason = "news_pause_symbols_uncovered"

    return {
        "enabled": enabled,
        "passed": passed,
        "wildcard": wildcard,
        "configured_symbols": configured_symbols,
        "required_symbols": required_symbols,
        "uncovered_symbols": uncovered_symbols,
        "reason": reason,
    }


def evaluate_performance_gate(parameters: dict[str, object]) -> dict[str, object]:
    enabled = bool(parameters.get("performance_gate_enabled", True))
    min_profit_factor = _safe_float(parameters.get("performance_gate_min_profit_factor", 1.3), 1.3)
    min_trades = _safe_int(parameters.get("performance_gate_min_trades", 100), 100)
    validated_profit_factor = _safe_float(parameters.get("validated_backtest_profit_factor", 0.0), 0.0)
    validated_trades = _safe_int(parameters.get("validated_backtest_trades", 0), 0)

    passed = (not enabled) or (
        validated_profit_factor >= min_profit_factor
        and validated_trades >= min_trades
    )
    missing_items: list[str] = []
    if enabled and validated_profit_factor < min_profit_factor:
        missing_items.append(f"profit factor {validated_profit_factor:.2f}/{min_profit_factor:.2f}")
    if enabled and validated_trades < min_trades:
        missing_items.append(f"trades simulados {validated_trades}/{min_trades}")

    return {
        "enabled": enabled,
        "passed": passed,
        "min_profit_factor": round(min_profit_factor, 2),
        "min_trades": min_trades,
        "validated_profit_factor": round(validated_profit_factor, 2),
        "validated_trades": validated_trades,
        "missing_items": missing_items,
    }


def evaluate_drawdown_guard(
    parameters: dict[str, object],
    snapshot: SnapshotRequest,
    daily_closed_pnl: float = 0.0,
) -> dict[str, object]:
    daily_loss_limit = _safe_float(parameters.get("daily_loss_limit", 0.0), 0.0)
    max_equity_drawdown_pct = _safe_float(parameters.get("max_equity_drawdown_pct", 0.0), 0.0)
    balance = max(_safe_float(snapshot.balance, 0.0), 0.0)
    equity = _safe_float(snapshot.equity, balance)
    equity_drawdown_pct = 0.0
    if balance > 0 and equity < balance:
        equity_drawdown_pct = round(((balance - equity) / balance) * 100, 4)

    reasons: list[str] = []
    if daily_loss_limit > 0 and daily_closed_pnl <= (-daily_loss_limit):
        reasons.append("daily_loss_limit")
    if max_equity_drawdown_pct > 0 and equity_drawdown_pct >= max_equity_drawdown_pct:
        reasons.append("equity_drawdown_limit")

    return {
        "active": bool(reasons),
        "reasons": reasons,
        "daily_closed_pnl": round(float(daily_closed_pnl), 2),
        "daily_loss_limit": round(daily_loss_limit, 2),
        "balance": round(balance, 2),
        "equity": round(equity, 2),
        "equity_drawdown_pct": round(equity_drawdown_pct, 2),
        "max_equity_drawdown_pct": round(max_equity_drawdown_pct, 2),
    }


def evaluate_news_pause(
    parameters: dict[str, object],
    symbol: str | None = None,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    enabled = bool(parameters.get("news_pause_enabled", False))
    configured_symbols = _configured_news_symbols(parameters)
    wildcard = _uses_wildcard(configured_symbols)
    if not enabled or not configured_symbols:
        return {
            "enabled": enabled,
            "active": False,
            "symbols": configured_symbols,
            "events": [],
            "error": None,
        }

    if symbol:
        normalized_symbol = str(symbol).upper().strip()
        if not wildcard and normalized_symbol not in configured_symbols:
            return {
                "enabled": enabled,
                "active": False,
                "symbols": configured_symbols,
                "events": [],
                "error": None,
            }
        symbols_to_check = [normalized_symbol]
    else:
        if wildcard:
            return {
                "enabled": enabled,
                "active": False,
                "symbols": configured_symbols,
                "events": [],
                "error": None,
            }
        symbols_to_check = configured_symbols

    before_minutes = _safe_int(parameters.get("news_pause_before_minutes", 30), 30)
    after_minutes = _safe_int(parameters.get("news_pause_after_minutes", 30), 30)
    minimum_impact = str(parameters.get("news_pause_impact", "HIGH")).upper().strip()
    configured_countries = str(parameters.get("news_pause_countries", "")).strip()
    current_time = observed_at or datetime.now(timezone.utc)

    active_events: list[dict[str, object]] = []
    first_error: str | None = None
    seen: set[tuple[str, str, str]] = set()
    for symbol_name in symbols_to_check:
        result = active_news_events_for_symbol(
            symbol=symbol_name,
            configured_countries=configured_countries,
            minimum_impact=minimum_impact,
            before_minutes=before_minutes,
            after_minutes=after_minutes,
            observed_at=current_time,
        )
        if not first_error and result["error"]:
            first_error = str(result["error"])
        for event in result["events"]:
            key = (str(event["symbol"]), str(event["title"]), str(event["date"]))
            if key in seen:
                continue
            seen.add(key)
            active_events.append(event)

    return {
        "enabled": enabled,
        "active": bool(active_events),
        "symbols": symbols_to_check,
        "events": active_events,
        "error": first_error,
    }


def build_runtime_state(
    parameters: dict[str, object],
    robot_mode: str,
    symbol: str | None = None,
    observed_at: datetime | None = None,
    broker_profile: str | None = None,
) -> dict[str, object]:
    performance = evaluate_performance_gate(parameters)
    news_pause = evaluate_news_pause(parameters, symbol=symbol, observed_at=observed_at)
    market_session = evaluate_market_session(parameters, symbol=symbol, broker_profile=broker_profile, observed_at=observed_at)
    decision_engine_mode = normalize_decision_engine_mode(parameters.get("decision_engine_mode"))
    operational_timeframe = normalize_timeframe(parameters.get("operational_timeframe"), "M5")
    confirmation_timeframe = normalize_timeframe(parameters.get("confirmation_timeframe"), "H1")

    pause_reasons: list[str] = []
    if bool(parameters.get("pause_new_orders", False)):
        pause_reasons.append("manual_pause")
    if performance["enabled"] and not performance["passed"] and str(robot_mode).upper() in {"DEMO", "REAL"}:
        pause_reasons.append("performance_gate")
    if market_session["enabled"] and not market_session["open"]:
        pause_reasons.append("market_session_closed")
    if news_pause["active"]:
        pause_reasons.append("news_pause")
    if news_pause["error"] and str(robot_mode).upper() == "REAL" and news_pause["enabled"]:
        pause_reasons.append("news_feed_unavailable")

    return {
        "runtime_pause_new_orders": bool(pause_reasons),
        "runtime_pause_reasons": pause_reasons,
        "decision_engine_mode": decision_engine_mode,
        "operational_timeframe": operational_timeframe,
        "confirmation_timeframe": confirmation_timeframe,
        "performance_gate_passed": bool(performance["passed"]),
        "performance_gate": performance,
        "news_pause_active": bool(news_pause["active"]),
        "news_pause_events": news_pause["events"],
        "news_pause_error": news_pause["error"],
        "news_pause_symbols": news_pause["symbols"],
        "market_session_open": bool(market_session["open"]),
        "market_session_family": str(market_session["family"]),
        "market_session_symbol": str(market_session["checked_symbol"]),
        "drawdown_guard_active": False,
    }


def build_runtime_guard_decision(snapshot: SnapshotRequest, runtime_state: dict[str, object]) -> DecisionResponse | None:
    if snapshot.open_positions > 0:
        return None

    pause_reasons = list(runtime_state.get("runtime_pause_reasons", []))
    if not pause_reasons:
        return None

    rationale = "runtime_pause_" + "_".join(pause_reasons)
    analysis = {
        "engine": "runtime_guard",
        "trigger": "runtime_pause",
        "pause_reasons": pause_reasons,
        "decision_engine_mode": runtime_state["decision_engine_mode"],
        "operational_timeframe": runtime_state["operational_timeframe"],
        "confirmation_timeframe": runtime_state["confirmation_timeframe"],
        "observed_timeframe": snapshot.timeframe,
        "observed_confirmation_timeframe": snapshot.htf_timeframe,
        "timeframe_match": str(snapshot.timeframe).upper() == str(runtime_state["operational_timeframe"]),
        "confirmation_match": str(snapshot.htf_timeframe or "").upper() == str(runtime_state["confirmation_timeframe"]),
        "performance_gate_passed": runtime_state["performance_gate_passed"],
        "news_pause_active": runtime_state["news_pause_active"],
        "news_pause_events": runtime_state["news_pause_events"],
        "news_pause_error": runtime_state["news_pause_error"],
        "market_session_open": runtime_state.get("market_session_open", True),
        "market_session_family": runtime_state.get("market_session_family", ""),
        "market_session_symbol": runtime_state.get("market_session_symbol", ""),
        "drawdown_guard_active": runtime_state.get("drawdown_guard_active", False),
        "daily_closed_pnl": runtime_state.get("daily_closed_pnl", 0.0),
        "daily_loss_limit": runtime_state.get("daily_loss_limit", 0.0),
        "equity": runtime_state.get("equity", 0.0),
        "balance": runtime_state.get("balance", 0.0),
        "equity_drawdown_pct": runtime_state.get("equity_drawdown_pct", 0.0),
        "max_equity_drawdown_pct": runtime_state.get("max_equity_drawdown_pct", 0.0),
    }
    return DecisionResponse(
        signal="HOLD",
        confidence=0.99,
        risk=0.0,
        stop_loss_points=0,
        take_profit_points=0,
        rationale=rationale,
        reason=rationale,
        analysis=analysis,
    )


def attach_runtime_context(
    decision: DecisionResponse,
    snapshot: SnapshotRequest,
    runtime_state: dict[str, object],
) -> DecisionResponse:
    analysis = dict(decision.analysis or {})
    analysis["decision_engine_mode"] = runtime_state["decision_engine_mode"]
    analysis["operational_timeframe"] = runtime_state["operational_timeframe"]
    analysis["confirmation_timeframe"] = runtime_state["confirmation_timeframe"]
    analysis["observed_timeframe"] = snapshot.timeframe
    analysis["observed_confirmation_timeframe"] = snapshot.htf_timeframe
    analysis["timeframe_match"] = str(snapshot.timeframe).upper() == str(runtime_state["operational_timeframe"])
    analysis["confirmation_match"] = str(snapshot.htf_timeframe or "").upper() == str(runtime_state["confirmation_timeframe"])
    analysis["runtime_pause_new_orders"] = runtime_state["runtime_pause_new_orders"]
    analysis["runtime_pause_reasons"] = runtime_state["runtime_pause_reasons"]
    analysis["performance_gate_passed"] = runtime_state["performance_gate_passed"]
    analysis["news_pause_active"] = runtime_state["news_pause_active"]
    analysis["market_session_open"] = runtime_state.get("market_session_open", True)
    analysis["market_session_family"] = runtime_state.get("market_session_family", "")
    analysis["market_session_symbol"] = runtime_state.get("market_session_symbol", "")
    analysis["drawdown_guard_active"] = runtime_state.get("drawdown_guard_active", False)
    analysis["daily_closed_pnl"] = runtime_state.get("daily_closed_pnl", 0.0)
    analysis["daily_loss_limit"] = runtime_state.get("daily_loss_limit", 0.0)
    analysis["balance"] = runtime_state.get("balance", 0.0)
    analysis["equity"] = runtime_state.get("equity", 0.0)
    analysis["equity_drawdown_pct"] = runtime_state.get("equity_drawdown_pct", 0.0)
    analysis["max_equity_drawdown_pct"] = runtime_state.get("max_equity_drawdown_pct", 0.0)
    if runtime_state["news_pause_events"]:
        analysis["news_pause_events"] = runtime_state["news_pause_events"]
    if runtime_state["news_pause_error"]:
        analysis["news_pause_error"] = runtime_state["news_pause_error"]
    decision.analysis = analysis
    return decision


def build_parameters_response_payload(parameters: dict[str, object], robot_mode: str = "DEMO") -> dict[str, object]:
    runtime_state = build_runtime_state(parameters, robot_mode=robot_mode)
    return {
        **parameters,
        "runtime_pause_new_orders": runtime_state["runtime_pause_new_orders"],
        "runtime_pause_reasons": runtime_state["runtime_pause_reasons"],
        "news_pause_active": runtime_state["news_pause_active"],
        "performance_gate_passed": runtime_state["performance_gate_passed"],
        "decision_engine_mode": runtime_state["decision_engine_mode"],
    }