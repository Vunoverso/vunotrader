from __future__ import annotations

from .models import SnapshotCandle


def _round_price(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _average_range(candles: list[SnapshotCandle]) -> float:
    if not candles:
        return 0.0
    return sum(max(candle.high - candle.low, 0.0) for candle in candles) / len(candles)


def _default_payload() -> dict[str, object]:
    return {
        "direction": "none",
        "anchor_source": "none",
        "anchor_low": None,
        "anchor_high": None,
        "anchor_start_time": None,
        "anchor_end_time": None,
        "retracement_382": None,
        "retracement_500": None,
        "retracement_618": None,
        "entry_zone_low": None,
        "entry_zone_high": None,
        "entry_zone_label": "38.2%-61.8%",
        "target_price_1272": None,
        "target_price_1618": None,
        "stop_reference_price": None,
        "fib_score": 0.24,
        "in_retracement_zone": False,
        "near_retracement_zone": False,
    }


def _find_confirmed_pivots(candles: list[SnapshotCandle]) -> tuple[list[int], list[int]]:
    pivot_highs: list[int] = []
    pivot_lows: list[int] = []
    if len(candles) < 5:
        return pivot_highs, pivot_lows

    for index in range(2, len(candles) - 2):
        high_value = float(candles[index].high)
        low_value = float(candles[index].low)
        left_highs = [float(candles[index - 1].high), float(candles[index - 2].high)]
        right_highs = [float(candles[index + 1].high), float(candles[index + 2].high)]
        left_lows = [float(candles[index - 1].low), float(candles[index - 2].low)]
        right_lows = [float(candles[index + 1].low), float(candles[index + 2].low)]

        if high_value >= max(left_highs) and high_value > max(right_highs):
            pivot_highs.append(index)
        if low_value <= min(left_lows) and low_value < min(right_lows):
            pivot_lows.append(index)

    return pivot_highs, pivot_lows


def _resolve_pivot_anchor(window: list[SnapshotCandle], direction: str) -> tuple[int, int, str] | None:
    pivot_highs, pivot_lows = _find_confirmed_pivots(window)
    if direction == "bullish":
        for high_index in reversed(pivot_highs):
            prior_lows = [index for index in pivot_lows if index < high_index]
            if not prior_lows:
                continue
            low_index = prior_lows[-1]
            if float(window[high_index].high) > float(window[low_index].low):
                return low_index, high_index, "confirmed_pivot"
        return None

    for low_index in reversed(pivot_lows):
        prior_highs = [index for index in pivot_highs if index < low_index]
        if not prior_highs:
            continue
        high_index = prior_highs[-1]
        if float(window[high_index].high) > float(window[low_index].low):
            return high_index, low_index, "confirmed_pivot"
    return None


def _resolve_impulse_anchor(window: list[SnapshotCandle], direction: str) -> tuple[int, int, str] | None:
    if direction == "bullish":
        high_index = max(range(len(window)), key=lambda idx: (window[idx].high, idx))
        if high_index <= 0:
            return None
        low_index = min(range(high_index + 1), key=lambda idx: (window[idx].low, -idx))
        if low_index >= high_index:
            return None
        return low_index, high_index, "impulse_fallback"

    low_index = min(range(len(window)), key=lambda idx: (window[idx].low, -idx))
    if low_index <= 0:
        return None
    high_index = max(range(low_index), key=lambda idx: (window[idx].high, idx))
    if high_index >= low_index:
        return None
    return high_index, low_index, "impulse_fallback"


def analyze_fibonacci(candles: list[SnapshotCandle], direction: str) -> dict[str, object]:
    payload = _default_payload()
    normalized_direction = str(direction or "").lower().strip()
    if normalized_direction not in {"bullish", "bearish"} or len(candles) < 8:
        return payload

    window = candles[-40:]
    average_range = _average_range(window)

    anchor = _resolve_pivot_anchor(window, normalized_direction) or _resolve_impulse_anchor(window, normalized_direction)
    if anchor is None:
        return payload

    first_index, second_index, anchor_source = anchor

    if normalized_direction == "bullish":
        low_index = first_index
        high_index = second_index
        anchor_low = float(window[low_index].low)
        anchor_high = float(window[high_index].high)
        current_price = float(window[-1].close)
        retracement_382 = anchor_high - ((anchor_high - anchor_low) * 0.382)
        retracement_500 = anchor_high - ((anchor_high - anchor_low) * 0.5)
        retracement_618 = anchor_high - ((anchor_high - anchor_low) * 0.618)
        target_price_1272 = anchor_high + ((anchor_high - anchor_low) * 0.272)
        target_price_1618 = anchor_high + ((anchor_high - anchor_low) * 0.618)
        stop_reference_price = anchor_low
    else:
        high_index = first_index
        low_index = second_index
        anchor_low = float(window[low_index].low)
        anchor_high = float(window[high_index].high)
        current_price = float(window[-1].close)
        retracement_382 = anchor_low + ((anchor_high - anchor_low) * 0.382)
        retracement_500 = anchor_low + ((anchor_high - anchor_low) * 0.5)
        retracement_618 = anchor_low + ((anchor_high - anchor_low) * 0.618)
        target_price_1272 = anchor_low - ((anchor_high - anchor_low) * 0.272)
        target_price_1618 = anchor_low - ((anchor_high - anchor_low) * 0.618)
        stop_reference_price = anchor_high

    span = anchor_high - anchor_low
    if span <= 0:
        return payload

    zone_low = min(retracement_382, retracement_618)
    zone_high = max(retracement_382, retracement_618)
    tolerance = max(average_range * 0.35, span * 0.04)
    in_retracement_zone = (zone_low - tolerance) <= current_price <= (zone_high + tolerance)
    near_retracement_zone = abs(current_price - retracement_500) <= tolerance or in_retracement_zone
    fib_score = 0.82 if in_retracement_zone else 0.64 if near_retracement_zone else 0.28

    payload.update(
        {
            "direction": normalized_direction,
            "anchor_source": anchor_source,
            "anchor_low": _round_price(anchor_low),
            "anchor_high": _round_price(anchor_high),
            "anchor_start_time": window[low_index].time if normalized_direction == "bullish" else window[high_index].time,
            "anchor_end_time": window[high_index].time if normalized_direction == "bullish" else window[low_index].time,
            "retracement_382": _round_price(retracement_382),
            "retracement_500": _round_price(retracement_500),
            "retracement_618": _round_price(retracement_618),
            "entry_zone_low": _round_price(zone_low),
            "entry_zone_high": _round_price(zone_high),
            "target_price_1272": _round_price(target_price_1272),
            "target_price_1618": _round_price(target_price_1618),
            "stop_reference_price": _round_price(stop_reference_price),
            "fib_score": round(fib_score, 2),
            "in_retracement_zone": in_retracement_zone,
            "near_retracement_zone": near_retracement_zone,
        }
    )
    return payload
