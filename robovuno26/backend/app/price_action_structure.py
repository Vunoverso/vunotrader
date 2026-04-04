from __future__ import annotations

from .models import SnapshotCandle


def _find_swing_highs(candles: list[SnapshotCandle]) -> list[dict[str, float | int]]:
    values: list[dict[str, float | int]] = []
    for index in range(1, len(candles) - 1):
        current = candles[index]
        if current.high > candles[index - 1].high and current.high >= candles[index + 1].high:
            values.append({"index": index, "price": current.high})
    return values


def _find_swing_lows(candles: list[SnapshotCandle]) -> list[dict[str, float | int]]:
    values: list[dict[str, float | int]] = []
    for index in range(1, len(candles) - 1):
        current = candles[index]
        if current.low < candles[index - 1].low and current.low <= candles[index + 1].low:
            values.append({"index": index, "price": current.low})
    return values


def _trend_from_swings(highs: list[dict[str, float | int]], lows: list[dict[str, float | int]]) -> str:
    if len(highs) < 2 or len(lows) < 2:
        return "neutral"

    higher_high = float(highs[-1]["price"]) > float(highs[-2]["price"])
    higher_low = float(lows[-1]["price"]) > float(lows[-2]["price"])
    lower_high = float(highs[-1]["price"]) < float(highs[-2]["price"])
    lower_low = float(lows[-1]["price"]) < float(lows[-2]["price"])

    if higher_high and higher_low:
        return "bullish"
    if lower_high and lower_low:
        return "bearish"
    return "range"


def _classify_state(candles: list[SnapshotCandle]) -> dict[str, object]:
    if len(candles) < 6:
        return {
            "state": "neutral",
            "score": 0.3,
            "breakout_bias": "none",
            "bos_signal": "none",
            "choch_signal": "none",
            "false_breakout_signal": "none",
        }

    window = candles[-30:]
    highs = _find_swing_highs(window)
    lows = _find_swing_lows(window)
    state = _trend_from_swings(highs, lows)
    previous_state = _trend_from_swings(highs[:-1], lows[:-1]) if len(highs) >= 3 and len(lows) >= 3 else "neutral"

    score = 0.35
    if state in {"bullish", "bearish"}:
        score = 0.78
    elif state == "range":
        score = 0.58

    previous_high = max(candle.high for candle in window[:-1])
    previous_low = min(candle.low for candle in window[:-1])
    last = window[-1]

    breakout_bias = "none"
    if last.close > previous_high:
        breakout_bias = "bullish"
    elif last.close < previous_low:
        breakout_bias = "bearish"

    false_breakout_signal = "none"
    if last.high > previous_high and last.close < previous_high:
        false_breakout_signal = "bearish"
    elif last.low < previous_low and last.close > previous_low:
        false_breakout_signal = "bullish"

    bos_signal = "none"
    last_swing_high = float(highs[-1]["price"]) if highs else previous_high
    last_swing_low = float(lows[-1]["price"]) if lows else previous_low
    if breakout_bias == "bullish" and state in {"bullish", "range", "neutral"}:
        bos_signal = "bullish"
    elif breakout_bias == "bearish" and state in {"bearish", "range", "neutral"}:
        bos_signal = "bearish"

    if state == "neutral" and bos_signal != "none":
        state = "range"

    choch_signal = "none"
    if previous_state == "bullish" and breakout_bias == "bearish":
        choch_signal = "bearish"
    elif previous_state == "bearish" and breakout_bias == "bullish":
        choch_signal = "bullish"

    if bos_signal != "none":
        score += 0.06
    if choch_signal != "none":
        score += 0.04
    if false_breakout_signal != "none":
        score += 0.05

    return {
        "state": state,
        "score": round(min(score, 0.95), 2),
        "breakout_bias": breakout_bias,
        "bos_signal": bos_signal,
        "choch_signal": choch_signal,
        "false_breakout_signal": false_breakout_signal,
    }


def analyze_structure(
    candles: list[SnapshotCandle],
    higher_timeframe_candles: list[SnapshotCandle],
) -> dict[str, object]:
    local = _classify_state(candles)
    higher = _classify_state(higher_timeframe_candles) if higher_timeframe_candles else {
        "state": "neutral",
        "score": 0.35,
        "breakout_bias": "none",
        "bos_signal": "none",
        "choch_signal": "none",
        "false_breakout_signal": "none",
    }

    alignment_score = 0.25
    if local["state"] == "range":
        alignment_score = 0.6
    elif local["state"] == higher["state"] and local["state"] in {"bullish", "bearish"}:
        alignment_score = 0.88
    elif higher["state"] == "neutral":
        alignment_score = 0.6

    structure_score = (float(local["score"]) * 0.7) + (alignment_score * 0.3)
    return {
        "state": str(local["state"]),
        "higher_state": str(higher["state"]),
        "breakout_bias": str(local["breakout_bias"]),
        "bos_signal": str(local["bos_signal"]),
        "choch_signal": str(local["choch_signal"]),
        "false_breakout_signal": str(local["false_breakout_signal"]),
        "structure_score": round(min(structure_score, 0.96), 2),
        "alignment_score": round(alignment_score, 2),
    }