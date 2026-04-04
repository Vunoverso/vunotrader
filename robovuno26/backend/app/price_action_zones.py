from __future__ import annotations

from .models import SnapshotCandle


EPSILON = 1e-9


def _average_range(candles: list[SnapshotCandle]) -> float:
    if not candles:
        return 0.0
    return sum(max(candle.high - candle.low, 0.0) for candle in candles) / len(candles)


def _cluster_levels(levels: list[float], tolerance: float) -> list[dict[str, float | int]]:
    clusters: list[dict[str, float | int]] = []
    for level in sorted(levels):
        matched = False
        for cluster in clusters:
            if abs(level - float(cluster["level"])) <= tolerance:
                touches = int(cluster["touches"]) + 1
                cluster["touches"] = touches
                cluster["level"] = ((float(cluster["level"]) * (touches - 1)) + level) / touches
                matched = True
                break
        if not matched:
            clusters.append({"level": level, "touches": 1})
    return clusters


def analyze_zones(candles: list[SnapshotCandle]) -> dict[str, object]:
    if len(candles) < 5:
        return {
            "zone_type": "neutral",
            "zone_score": 0.2,
            "support": None,
            "resistance": None,
            "is_range": False,
            "tolerance": 0.0,
            "support_touches": 0,
            "resistance_touches": 0,
            "false_breakout_signal": "none",
        }

    window = candles[-30:]
    last = window[-1]
    raw_support = min(candle.low for candle in window)
    raw_resistance = max(candle.high for candle in window)
    range_span = max(raw_resistance - raw_support, EPSILON)
    average_range = max(_average_range(window), EPSILON)
    tolerance = max(average_range * 0.25, range_span * 0.04)

    support_clusters = _cluster_levels([candle.low for candle in window], tolerance)
    resistance_clusters = _cluster_levels([candle.high for candle in window], tolerance)
    support_cluster = max(support_clusters, key=lambda item: (int(item["touches"]), -float(item["level"])))
    resistance_cluster = max(resistance_clusters, key=lambda item: (int(item["touches"]), float(item["level"])))
    support = float(support_cluster["level"])
    resistance = float(resistance_cluster["level"])
    support_touches = int(support_cluster["touches"])
    resistance_touches = int(resistance_cluster["touches"])

    support_touch = last.low <= support + tolerance and last.close >= support - tolerance
    resistance_touch = last.high >= resistance - tolerance and last.close <= resistance + tolerance
    net_move = abs(window[-1].close - window[0].open)
    is_range = range_span <= average_range * 6.0 and net_move <= range_span * 0.55

    false_breakout_signal = "none"
    if last.low < support - tolerance and last.close > support:
        false_breakout_signal = "bullish"
    elif last.high > resistance + tolerance and last.close < resistance:
        false_breakout_signal = "bearish"

    zone_type = "neutral"
    zone_score = 0.22

    if support_touch and is_range:
        zone_type = "range_low"
        zone_score = 0.8
    elif resistance_touch and is_range:
        zone_type = "range_high"
        zone_score = 0.8
    elif support_touch:
        zone_type = "support"
        zone_score = 0.74
    elif resistance_touch:
        zone_type = "resistance"
        zone_score = 0.74
    elif is_range:
        zone_type = "mid_range"
        zone_score = 0.34

    repeated_touches = max(support_touches, resistance_touches)
    if repeated_touches >= 3:
        zone_score += min((repeated_touches - 2) * 0.05, 0.15)
    if false_breakout_signal != "none":
        zone_score += 0.06

    return {
        "zone_type": zone_type,
        "zone_score": round(min(zone_score, 0.94), 2),
        "support": round(support, 6),
        "resistance": round(resistance, 6),
        "is_range": is_range,
        "tolerance": round(tolerance, 6),
        "support_touches": support_touches,
        "resistance_touches": resistance_touches,
        "false_breakout_signal": false_breakout_signal,
    }