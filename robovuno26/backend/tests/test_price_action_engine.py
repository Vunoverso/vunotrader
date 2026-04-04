from __future__ import annotations

from app.decision_engine import _build_memory_context_key, evaluate_snapshot
from app.models import SnapshotCandle, SnapshotRequest
from app.price_action_structure import analyze_structure
from app.price_action_zones import analyze_zones


def build_candle(
    time: str,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> SnapshotCandle:
    return SnapshotCandle(
        time=time,
        open=open_price,
        high=high,
        low=low,
        close=close,
        tick_volume=100,
    )


def build_snapshot(
    candles: list[SnapshotCandle],
    higher_timeframe_candles: list[SnapshotCandle],
    ema_fast: float,
    ema_slow: float,
    rsi: float,
    **overrides,
) -> SnapshotRequest:
    payload = {
        "symbol": "EURUSD",
        "timeframe": "M5",
        "bid": 1.2052,
        "ask": 1.2054,
        "spread_points": 2.0,
        "close": candles[-1].close if candles else 1.2053,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "rsi": rsi,
        "balance": 10000.0,
        "equity": 10000.0,
        "open_positions": 0,
        "captured_at": "2026-04-03T12:10:00+00:00",
        "candles": candles,
        "htf_timeframe": "H1",
        "htf_candles": higher_timeframe_candles,
        "local_memory": {"recent_win_rate": 0.58, "recent_pnl": 4.0},
    }
    payload.update(overrides)
    return SnapshotRequest(**payload)


def build_repeated_candles(count: int = 8, price: float = 1.2050) -> list[SnapshotCandle]:
    candles: list[SnapshotCandle] = []
    for index in range(count):
        candles.append(build_candle(f"2026-04-03 13:{index:02d}:00", price, price, price, price))
    return candles


def test_price_action_returns_buy_on_bullish_pin_bar_at_support():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2070, 1.2074, 1.2062, 1.2066),
        build_candle("2026-04-03 12:05:00", 1.2066, 1.2068, 1.2057, 1.2060),
        build_candle("2026-04-03 12:10:00", 1.2060, 1.2062, 1.2052, 1.2056),
        build_candle("2026-04-03 12:15:00", 1.2056, 1.2059, 1.2050, 1.2054),
        build_candle("2026-04-03 12:20:00", 1.2054, 1.2056, 1.2048, 1.2051),
        build_candle("2026-04-03 12:25:00", 1.2051, 1.2053, 1.2046, 1.2049),
        build_candle("2026-04-03 12:30:00", 1.2049, 1.2050, 1.2044, 1.2047),
        build_candle("2026-04-03 12:35:00", 1.2049, 1.2054, 1.2038, 1.2053),
    ]
    higher_timeframe_candles = [
        build_candle("2026-04-03 08:00:00", 1.2080, 1.2085, 1.2058, 1.2068),
        build_candle("2026-04-03 09:00:00", 1.2068, 1.2072, 1.2054, 1.2061),
        build_candle("2026-04-03 10:00:00", 1.2061, 1.2066, 1.2049, 1.2058),
        build_candle("2026-04-03 11:00:00", 1.2058, 1.2061, 1.2048, 1.2052),
        build_candle("2026-04-03 12:00:00", 1.2052, 1.2059, 1.2046, 1.2054),
    ]

    decision = evaluate_snapshot(build_snapshot(candles, higher_timeframe_candles, 1.2048, 1.2050, 51.0))

    assert decision.signal == "BUY"
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "price_action_v1"
    assert decision.analysis["setup"] == "pin_bar"
    assert decision.analysis["zone_type"] in {"support", "range_low"}
    assert "fib_score" in decision.analysis
    assert "fib_entry_zone_label" in decision.analysis


def test_price_action_returns_sell_on_bearish_pin_bar_at_resistance():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.3000, 1.3006, 1.2998, 1.3004),
        build_candle("2026-04-03 12:05:00", 1.3004, 1.3010, 1.3002, 1.3008),
        build_candle("2026-04-03 12:10:00", 1.3008, 1.3014, 1.3006, 1.3011),
        build_candle("2026-04-03 12:15:00", 1.3011, 1.3017, 1.3009, 1.3014),
        build_candle("2026-04-03 12:20:00", 1.3014, 1.3020, 1.3011, 1.3017),
        build_candle("2026-04-03 12:25:00", 1.3017, 1.3022, 1.3014, 1.3019),
        build_candle("2026-04-03 12:30:00", 1.3019, 1.3024, 1.3015, 1.3020),
        build_candle("2026-04-03 12:35:00", 1.30195, 1.3032, 1.3015, 1.3016),
    ]
    higher_timeframe_candles = [
        build_candle("2026-04-03 08:00:00", 1.2990, 1.3008, 1.2988, 1.3003),
        build_candle("2026-04-03 09:00:00", 1.3003, 1.3010, 1.2998, 1.3006),
        build_candle("2026-04-03 10:00:00", 1.3006, 1.3016, 1.3001, 1.3010),
        build_candle("2026-04-03 11:00:00", 1.3010, 1.3020, 1.3005, 1.3014),
        build_candle("2026-04-03 12:00:00", 1.3014, 1.3022, 1.3009, 1.3016),
    ]

    decision = evaluate_snapshot(build_snapshot(candles, higher_timeframe_candles, 1.3014, 1.3018, 49.0))

    assert decision.signal == "SELL"
    assert decision.analysis is not None
    assert decision.analysis["engine"] in {"price_action_v1", "legacy_v1"}
    if decision.analysis["engine"] == "price_action_v1":
        assert decision.analysis["setup"] == "pin_bar"
        assert decision.analysis["zone_type"] in {"resistance", "range_high"}


def test_decision_engine_keeps_legacy_fallback_without_pattern():
    decision = evaluate_snapshot(
        SnapshotRequest(
            symbol="EURUSD",
            timeframe="M5",
            bid=1.1000,
            ask=1.1002,
            spread_points=2.0,
            close=1.1001,
            ema_fast=1.1010,
            ema_slow=1.1000,
            rsi=55.0,
            balance=10000.0,
            equity=10010.0,
            open_positions=0,
            captured_at="2026-04-03T12:35:00+00:00",
            candles=[],
            htf_timeframe="H1",
            htf_candles=[],
            local_memory={"recent_win_rate": 0.6, "recent_pnl": 3.4},
        )
    )

    assert decision.signal == "BUY"
    assert decision.rationale == "tendencia_alta"
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "legacy_v1"


def test_price_action_only_mode_holds_without_pattern():
    decision = evaluate_snapshot(
        build_snapshot([], [], 1.1010, 1.1000, 55.0),
        decision_engine_mode="PRICE_ACTION_ONLY",
    )

    assert decision.signal == "HOLD"
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "price_action_only_guard"
    assert decision.analysis["engine_requested"] == "PRICE_ACTION_ONLY"


def test_market_data_guard_holds_on_repeated_feed():
    candles = build_repeated_candles()

    decision = evaluate_snapshot(build_snapshot(candles, [], 1.2050, 1.2050, 50.0))

    assert decision.signal == "HOLD"
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "market_data_guard"
    assert "dados_repetidos" in decision.analysis["data_quality_reasons"]


def test_open_position_management_holds_when_market_data_is_frozen():
    candles = build_repeated_candles(price=1.3010)

    decision = evaluate_snapshot(
        build_snapshot(
            candles,
            [],
            1.3010,
            1.3010,
            50.0,
            open_positions=1,
            open_position_ticket=112233,
            open_position_direction="BUY",
            open_position_entry_price=1.3000,
            open_position_current_price=1.3010,
            open_position_profit=25.0,
            open_position_profit_points=10.0,
        )
    )

    assert decision.signal == "HOLD"
    assert decision.position_action == "NONE"
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "position_manager_v1"
    assert decision.analysis["data_quality_guard_active"] is True
    assert "dados_repetidos" in decision.analysis["management_reasons"]


def test_open_position_management_closes_profitable_trade_on_reversal():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.3000, 1.3006, 1.2998, 1.3004),
        build_candle("2026-04-03 12:05:00", 1.3004, 1.3010, 1.3002, 1.3008),
        build_candle("2026-04-03 12:10:00", 1.3008, 1.3014, 1.3006, 1.3011),
        build_candle("2026-04-03 12:15:00", 1.3011, 1.3017, 1.3009, 1.3014),
        build_candle("2026-04-03 12:20:00", 1.3014, 1.3020, 1.3011, 1.3017),
        build_candle("2026-04-03 12:25:00", 1.3017, 1.3022, 1.3014, 1.3019),
        build_candle("2026-04-03 12:30:00", 1.3019, 1.3024, 1.3015, 1.3020),
        build_candle("2026-04-03 12:35:00", 1.30195, 1.3032, 1.3015, 1.3016),
    ]
    higher_timeframe_candles = [
        build_candle("2026-04-03 08:00:00", 1.2990, 1.3008, 1.2988, 1.3003),
        build_candle("2026-04-03 09:00:00", 1.3003, 1.3010, 1.2998, 1.3006),
        build_candle("2026-04-03 10:00:00", 1.3006, 1.3016, 1.3001, 1.3010),
        build_candle("2026-04-03 11:00:00", 1.3010, 1.3020, 1.3005, 1.3014),
        build_candle("2026-04-03 12:00:00", 1.3014, 1.3022, 1.3009, 1.3016),
    ]

    decision = evaluate_snapshot(
        build_snapshot(
            candles,
            higher_timeframe_candles,
            1.3014,
            1.3018,
            49.0,
            open_positions=1,
            open_position_ticket=123456,
            open_position_direction="BUY",
            open_position_entry_price=1.3004,
            open_position_current_price=1.3016,
            open_position_profit=45.0,
            open_position_profit_points=12.0,
        )
    )

    assert decision.signal == "HOLD"
    assert decision.position_action == "CLOSE"
    assert decision.position_ticket == 123456
    assert decision.analysis is not None
    assert decision.analysis["engine"] == "position_manager_v1"


def test_open_position_management_protects_profit_without_new_entry():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2070, 1.2074, 1.2062, 1.2066),
        build_candle("2026-04-03 12:05:00", 1.2066, 1.2068, 1.2057, 1.2060),
        build_candle("2026-04-03 12:10:00", 1.2060, 1.2062, 1.2052, 1.2056),
        build_candle("2026-04-03 12:15:00", 1.2056, 1.2059, 1.2050, 1.2054),
        build_candle("2026-04-03 12:20:00", 1.2054, 1.2056, 1.2048, 1.2051),
        build_candle("2026-04-03 12:25:00", 1.2051, 1.2053, 1.2046, 1.2049),
        build_candle("2026-04-03 12:30:00", 1.2049, 1.2050, 1.2044, 1.2047),
        build_candle("2026-04-03 12:35:00", 1.2049, 1.2054, 1.2038, 1.2053),
    ]
    higher_timeframe_candles = [
        build_candle("2026-04-03 08:00:00", 1.2080, 1.2085, 1.2058, 1.2068),
        build_candle("2026-04-03 09:00:00", 1.2068, 1.2072, 1.2054, 1.2061),
        build_candle("2026-04-03 10:00:00", 1.2061, 1.2066, 1.2049, 1.2058),
        build_candle("2026-04-03 11:00:00", 1.2058, 1.2061, 1.2048, 1.2052),
        build_candle("2026-04-03 12:00:00", 1.2052, 1.2059, 1.2046, 1.2054),
    ]

    decision = evaluate_snapshot(
        build_snapshot(
            candles,
            higher_timeframe_candles,
            1.2048,
            1.2050,
            51.0,
            open_positions=1,
            open_position_ticket=654321,
            open_position_direction="BUY",
            open_position_entry_price=1.2040,
            open_position_current_price=1.2053,
            open_position_profit=52.0,
            open_position_profit_points=13.0,
        )
    )

    assert decision.signal == "HOLD"
    assert decision.position_action == "PROTECT"
    assert decision.position_stop_loss is not None
    assert decision.analysis is not None
    assert decision.analysis["management_action"] == "PROTECT"


def test_open_position_management_closes_profitable_trade_on_time_stop_and_stagnation():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2050, 1.2054, 1.2048, 1.2051),
        build_candle("2026-04-03 12:05:00", 1.2051, 1.2052, 1.2049, 1.2050),
        build_candle("2026-04-03 12:10:00", 1.2050, 1.2051, 1.2048, 1.2049),
        build_candle("2026-04-03 12:15:00", 1.2049, 1.2051, 1.2047, 1.2050),
        build_candle("2026-04-03 12:20:00", 1.2050, 1.2052, 1.2049, 1.2050),
        build_candle("2026-04-03 12:25:00", 1.2050, 1.2051, 1.2048, 1.2049),
        build_candle("2026-04-03 12:30:00", 1.2049, 1.2051, 1.2048, 1.2050),
        build_candle("2026-04-03 12:35:00", 1.2050, 1.2052, 1.2049, 1.2050),
    ]

    decision = evaluate_snapshot(
        build_snapshot(
            candles,
            [],
            1.2050,
            1.2049,
            50.0,
            open_positions=1,
            open_position_ticket=991122,
            open_position_direction="BUY",
            open_position_entry_price=1.2045,
            open_position_current_price=1.2050,
            open_position_profit=18.0,
            open_position_profit_points=6.0,
            open_position_opened_at="2026-04-03T10:50:00+00:00",
            captured_at="2026-04-03T12:35:00+00:00",
        ),
        management_settings={
            "position_time_stop_minutes": 30,
            "position_stagnation_window_candles": 4,
            "break_even_trigger_points": 5,
            "trailing_trigger_points": 14,
        },
    )

    assert decision.signal == "HOLD"
    assert decision.position_action == "CLOSE"
    assert decision.analysis is not None
    assert decision.analysis["management_action"] == "CLOSE"
    assert "time_stop" in decision.analysis["management_reasons"]
    assert decision.analysis["stagnation_detected"] is True


def test_open_position_management_uses_structural_trailing_when_profit_expands():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2070, 1.2074, 1.2062, 1.2066),
        build_candle("2026-04-03 12:05:00", 1.2066, 1.2068, 1.2057, 1.2060),
        build_candle("2026-04-03 12:10:00", 1.2060, 1.2062, 1.2052, 1.2056),
        build_candle("2026-04-03 12:15:00", 1.2056, 1.2059, 1.2050, 1.2054),
        build_candle("2026-04-03 12:20:00", 1.2054, 1.2056, 1.2048, 1.2051),
        build_candle("2026-04-03 12:25:00", 1.2051, 1.2053, 1.2046, 1.2049),
        build_candle("2026-04-03 12:30:00", 1.2049, 1.2050, 1.2044, 1.2047),
        build_candle("2026-04-03 12:35:00", 1.2049, 1.2054, 1.2038, 1.2053),
    ]
    higher_timeframe_candles = [
        build_candle("2026-04-03 08:00:00", 1.2080, 1.2085, 1.2058, 1.2068),
        build_candle("2026-04-03 09:00:00", 1.2068, 1.2072, 1.2054, 1.2061),
        build_candle("2026-04-03 10:00:00", 1.2061, 1.2066, 1.2049, 1.2058),
        build_candle("2026-04-03 11:00:00", 1.2058, 1.2061, 1.2048, 1.2052),
        build_candle("2026-04-03 12:00:00", 1.2052, 1.2059, 1.2046, 1.2054),
    ]

    decision = evaluate_snapshot(
        build_snapshot(
            candles,
            higher_timeframe_candles,
            1.2048,
            1.2050,
            51.0,
            open_positions=1,
            open_position_ticket=554433,
            open_position_direction="BUY",
            open_position_entry_price=1.2040,
            open_position_current_price=1.2053,
            open_position_profit=48.0,
            open_position_profit_points=13.0,
        ),
        management_settings={
            "break_even_trigger_points": 6,
            "trailing_trigger_points": 10,
            "position_stagnation_window_candles": 4,
        },
    )

    assert decision.signal == "HOLD"
    assert decision.position_action == "PROTECT"
    assert decision.position_stop_loss is not None
    assert decision.analysis is not None
    assert "trailing_estrutural" in decision.analysis["management_reasons"]


def test_setup_and_context_memory_adjust_confidence_and_risk():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2070, 1.2074, 1.2062, 1.2066),
        build_candle("2026-04-03 12:05:00", 1.2066, 1.2068, 1.2057, 1.2060),
        build_candle("2026-04-03 12:10:00", 1.2060, 1.2062, 1.2052, 1.2056),
        build_candle("2026-04-03 12:15:00", 1.2056, 1.2059, 1.2050, 1.2054),
        build_candle("2026-04-03 12:20:00", 1.2054, 1.2056, 1.2048, 1.2051),
        build_candle("2026-04-03 12:25:00", 1.2051, 1.2053, 1.2046, 1.2049),
        build_candle("2026-04-03 12:30:00", 1.2049, 1.2050, 1.2044, 1.2047),
        build_candle("2026-04-03 12:35:00", 1.2049, 1.2054, 1.2038, 1.2053),
    ]
    snapshot = build_snapshot(candles, [], 1.2048, 1.2050, 51.0)
    baseline = evaluate_snapshot(snapshot)
    assert baseline.analysis is not None

    context_key = _build_memory_context_key(baseline.signal, dict(baseline.analysis))
    enriched_snapshot = build_snapshot(
        candles,
        [],
        1.2048,
        1.2050,
        51.0,
        local_memory={
            "recent_win_rate": 0.58,
            "recent_pnl": 4.0,
            "setup_stats": {
                baseline.analysis["setup"]: {"recent_trades": 6, "recent_win_rate": 0.83, "recent_pnl": 28.0},
            },
            "context_stats": {
                context_key: {"recent_trades": 5, "recent_win_rate": 0.8, "recent_pnl": 20.0},
            },
        },
    )

    enriched = evaluate_snapshot(enriched_snapshot)

    assert enriched.confidence > baseline.confidence
    assert enriched.analysis is not None
    assert "setup_favoravel" in enriched.analysis["memory_adjustments"]
    assert "contexto_favoravel" in enriched.analysis["memory_adjustments"]


def test_analyze_zones_detects_repeated_touches_and_false_breakout():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.2020, 1.2024, 1.2001, 1.2016),
        build_candle("2026-04-03 12:05:00", 1.2016, 1.2020, 1.2002, 1.2015),
        build_candle("2026-04-03 12:10:00", 1.2015, 1.2019, 1.2000, 1.2013),
        build_candle("2026-04-03 12:15:00", 1.2013, 1.2016, 1.2001, 1.2012),
        build_candle("2026-04-03 12:20:00", 1.2012, 1.2015, 1.1995, 1.2014),
        build_candle("2026-04-03 12:25:00", 1.2014, 1.2018, 1.1992, 1.2016),
    ]

    zones = analyze_zones(candles)

    assert zones["support_touches"] >= 3
    assert zones["false_breakout_signal"] == "bullish"


def test_analyze_structure_detects_bos_signal():
    candles = [
        build_candle("2026-04-03 12:00:00", 1.1980, 1.1990, 1.1978, 1.1988),
        build_candle("2026-04-03 12:05:00", 1.1988, 1.1994, 1.1985, 1.1992),
        build_candle("2026-04-03 12:10:00", 1.1992, 1.1995, 1.1987, 1.1989),
        build_candle("2026-04-03 12:15:00", 1.1989, 1.2001, 1.1988, 1.1998),
        build_candle("2026-04-03 12:20:00", 1.1998, 1.2000, 1.1990, 1.1992),
        build_candle("2026-04-03 12:25:00", 1.1992, 1.2008, 1.1991, 1.2006),
        build_candle("2026-04-03 12:30:00", 1.2006, 1.2007, 1.1997, 1.1999),
        build_candle("2026-04-03 12:35:00", 1.1999, 1.2013, 1.1998, 1.2012),
    ]
    higher = [
        build_candle("2026-04-03 08:00:00", 1.1960, 1.1972, 1.1958, 1.1969),
        build_candle("2026-04-03 09:00:00", 1.1969, 1.1982, 1.1966, 1.1978),
        build_candle("2026-04-03 10:00:00", 1.1978, 1.1988, 1.1973, 1.1982),
        build_candle("2026-04-03 11:00:00", 1.1982, 1.1992, 1.1979, 1.1988),
        build_candle("2026-04-03 12:00:00", 1.1988, 1.2005, 1.1985, 1.2002),
    ]

    structure = analyze_structure(candles, higher)

    assert structure["bos_signal"] == "bullish"
    assert structure["state"] in {"bullish", "range"}