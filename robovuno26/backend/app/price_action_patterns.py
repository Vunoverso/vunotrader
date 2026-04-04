from __future__ import annotations

from .models import SnapshotCandle


EPSILON = 1e-9
PATTERN_PRIORITY = {"engulfing": 3, "pin_bar": 2, "inside_bar": 1}


def _body(candle: SnapshotCandle) -> float:
    return abs(candle.close - candle.open)


def _range(candle: SnapshotCandle) -> float:
    return max(candle.high - candle.low, EPSILON)


def _upper_wick(candle: SnapshotCandle) -> float:
    return max(0.0, candle.high - max(candle.open, candle.close))


def _lower_wick(candle: SnapshotCandle) -> float:
    return max(0.0, min(candle.open, candle.close) - candle.low)


def _midpoint(candle: SnapshotCandle) -> float:
    return candle.low + ((_range(candle)) / 2.0)


def detect_primary_pattern(candles: list[SnapshotCandle]) -> dict[str, object] | None:
    if len(candles) < 2:
        return None

    last = candles[-1]
    prev = candles[-2]
    candidates: list[dict[str, object]] = []

    body = max(_body(last), _range(last) * 0.05)
    upper = _upper_wick(last)
    lower = _lower_wick(last)

    if lower >= body * 2.5 and upper <= _range(last) * 0.35 and last.close > _midpoint(last):
        strength = min(0.58 + (min(lower / body, 4.5) * 0.06), 0.9)
        candidates.append({
            "name": "pin_bar",
            "direction": "bullish",
            "strength": round(strength, 2),
            "label": "bullish_pin_bar",
        })

    if upper >= body * 2.5 and lower <= _range(last) * 0.35 and last.close < _midpoint(last):
        strength = min(0.58 + (min(upper / body, 4.5) * 0.06), 0.9)
        candidates.append({
            "name": "pin_bar",
            "direction": "bearish",
            "strength": round(strength, 2),
            "label": "bearish_pin_bar",
        })

    previous_body = max(_body(prev), _range(prev) * 0.05)

    if prev.close < prev.open and last.close > last.open and last.open <= prev.close and last.close >= prev.open:
        strength = min(0.62 + (min(_body(last) / previous_body, 2.5) * 0.08), 0.94)
        candidates.append({
            "name": "engulfing",
            "direction": "bullish",
            "strength": round(strength, 2),
            "label": "bullish_engulfing",
        })

    if prev.close > prev.open and last.close < last.open and last.open >= prev.close and last.close <= prev.open:
        strength = min(0.62 + (min(_body(last) / previous_body, 2.5) * 0.08), 0.94)
        candidates.append({
            "name": "engulfing",
            "direction": "bearish",
            "strength": round(strength, 2),
            "label": "bearish_engulfing",
        })

    if last.high <= prev.high and last.low >= prev.low:
        direction = "bullish" if last.close >= _midpoint(prev) else "bearish"
        strength = 0.45 + ((1.0 - min(_range(last) / max(_range(prev), EPSILON), 1.0)) * 0.25)
        candidates.append({
            "name": "inside_bar",
            "direction": direction,
            "strength": round(strength, 2),
            "label": f"{direction}_inside_bar",
        })

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda candidate: (float(candidate["strength"]), PATTERN_PRIORITY[str(candidate["name"])]),
    )