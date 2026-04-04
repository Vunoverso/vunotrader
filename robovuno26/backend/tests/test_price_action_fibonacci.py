from __future__ import annotations

from app.models import SnapshotCandle, SnapshotRequest
from app.price_action import analyze_price_action_context
from app.price_action_fibonacci import analyze_fibonacci


def build_candle(time: str, open_price: float, high: float, low: float, close: float) -> SnapshotCandle:
    return SnapshotCandle(
        time=time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=100,
    )


def build_bullish_retracement_candles() -> list[SnapshotCandle]:
    return [
        build_candle("2026-04-04 12:00:00", 1.1000, 1.1010, 1.0996, 1.1008),
        build_candle("2026-04-04 12:05:00", 1.1008, 1.1025, 1.1007, 1.1022),
        build_candle("2026-04-04 12:10:00", 1.1022, 1.1040, 1.1020, 1.1038),
        build_candle("2026-04-04 12:15:00", 1.1038, 1.1060, 1.1036, 1.1058),
        build_candle("2026-04-04 12:20:00", 1.1058, 1.1060, 1.1048, 1.1050),
        build_candle("2026-04-04 12:25:00", 1.1050, 1.1051, 1.1036, 1.1040),
        build_candle("2026-04-04 12:30:00", 1.1040, 1.1042, 1.1029, 1.1034),
        build_candle("2026-04-04 12:35:00", 1.1035, 1.1038, 1.1018, 1.1036),
    ]


def build_confirmed_pivot_retracement_candles() -> list[SnapshotCandle]:
    return [
        build_candle("2026-04-04 11:50:00", 1.1000, 1.1006, 1.0998, 1.1004),
        build_candle("2026-04-04 11:55:00", 1.1004, 1.1008, 1.1000, 1.1003),
        build_candle("2026-04-04 12:00:00", 1.1003, 1.1005, 1.0992, 1.0996),
        build_candle("2026-04-04 12:05:00", 1.0996, 1.1015, 1.0995, 1.1012),
        build_candle("2026-04-04 12:10:00", 1.1012, 1.1032, 1.1010, 1.1030),
        build_candle("2026-04-04 12:15:00", 1.1030, 1.1048, 1.1026, 1.1045),
        build_candle("2026-04-04 12:20:00", 1.1045, 1.1042, 1.1032, 1.1036),
        build_candle("2026-04-04 12:25:00", 1.1036, 1.1039, 1.1024, 1.1030),
        build_candle("2026-04-04 12:30:00", 1.1030, 1.1032, 1.1017, 1.1020),
    ]


def test_analyze_fibonacci_detects_bullish_retracement_zone():
    fib = analyze_fibonacci(build_bullish_retracement_candles(), "bullish")

    assert fib["direction"] == "bullish"
    assert fib["in_retracement_zone"] is True
    assert fib["fib_score"] >= 0.8
    assert fib["entry_zone_low"] is not None
    assert fib["entry_zone_high"] is not None
    assert fib["target_price_1272"] is not None


def test_analyze_fibonacci_prefers_confirmed_pivot_anchor_when_available():
    fib = analyze_fibonacci(build_confirmed_pivot_retracement_candles(), "bullish")

    assert fib["direction"] == "bullish"
    assert fib["anchor_source"] == "confirmed_pivot"
    assert fib["in_retracement_zone"] is True


def test_price_action_context_exposes_fibonacci_fields():
    candles = build_bullish_retracement_candles()
    snapshot = SnapshotRequest(
        symbol="EURUSD",
        timeframe="M5",
        bid=1.1034,
        ask=1.1036,
        spread_points=2.0,
        close=1.1036,
        ema_fast=1.1030,
        ema_slow=1.1026,
        rsi=52.0,
        balance=10000.0,
        equity=10010.0,
        open_positions=0,
        captured_at="2026-04-04T12:35:00+00:00",
        candles=candles,
        htf_timeframe="H1",
        htf_candles=[],
        local_memory={"recent_win_rate": 0.55, "recent_pnl": 3.0},
    )

    context = analyze_price_action_context(snapshot)

    assert "fibonacci" in context
    assert context["fibonacci"]["fib_score"] >= 0.6
    assert context["fibonacci"]["entry_zone_label"] == "38.2%-61.8%"
