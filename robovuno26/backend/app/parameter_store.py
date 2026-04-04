from __future__ import annotations

DEFAULT_USER_PARAMETERS = {
    "risk_per_trade": 0.5,
    "max_spread_points": 30.0,
    "default_lot": 0.01,
    "stop_loss_points": 180,
    "take_profit_points": 360,
    "max_positions_per_symbol": 1,
    "reentry_cooldown_seconds": 60,
    "max_command_age_seconds": 45,
    "deviation_points": 20,
    "execution_retries": 3,
    "pause_new_orders": False,
    "use_local_fallback": True,
    "market_session_guard_enabled": True,
    "decision_engine_mode": "HYBRID",
    "operational_timeframe": "M5",
    "confirmation_timeframe": "H1",
    "daily_loss_limit": 0.0,
    "max_equity_drawdown_pct": 0.0,
    "break_even_trigger_points": 8,
    "trailing_trigger_points": 14,
    "position_time_stop_minutes": 90,
    "position_stagnation_window_candles": 6,
    "news_pause_enabled": True,
    "news_pause_symbols": "*",
    "news_pause_countries": "",
    "news_pause_before_minutes": 30,
    "news_pause_after_minutes": 30,
    "news_pause_impact": "HIGH",
    "performance_gate_enabled": True,
    "performance_gate_min_profit_factor": 1.3,
    "performance_gate_min_trades": 100,
    "validated_backtest_profit_factor": 0.0,
    "validated_backtest_trades": 0,
}


def with_parameter_scope(
    payload: dict,
    *,
    parameter_scope: str,
    scope_robot_instance_id: int | None = None,
    scope_robot_name: str | None = None,
    scope_inherited: bool = False,
) -> dict:
    scoped = dict(payload)
    scoped["parameter_scope"] = parameter_scope
    scoped["scope_robot_instance_id"] = scope_robot_instance_id
    scoped["scope_robot_name"] = scope_robot_name
    scoped["scope_inherited"] = scope_inherited
    return scoped


def serialize_user_parameters(row: dict | None, tenant_id: int) -> dict:
    payload = dict(DEFAULT_USER_PARAMETERS)
    updated_at = ""

    if row:
        payload.update(
            {
                "risk_per_trade": float(row["risk_per_trade"]),
                "max_spread_points": float(row["max_spread_points"]),
                "default_lot": float(row["default_lot"]),
                "stop_loss_points": int(row["stop_loss_points"]),
                "take_profit_points": int(row["take_profit_points"]),
                "max_positions_per_symbol": int(row["max_positions_per_symbol"]),
                "reentry_cooldown_seconds": int(row["reentry_cooldown_seconds"]),
                "max_command_age_seconds": int(row["max_command_age_seconds"]),
                "deviation_points": int(row["deviation_points"]),
                "execution_retries": int(row["execution_retries"]),
                "pause_new_orders": bool(row["pause_new_orders"]),
                "use_local_fallback": bool(row["use_local_fallback"]),
                "market_session_guard_enabled": bool(row["market_session_guard_enabled"]),
                "decision_engine_mode": str(row["decision_engine_mode"]),
                "operational_timeframe": str(row["operational_timeframe"]),
                "confirmation_timeframe": str(row["confirmation_timeframe"]),
                "daily_loss_limit": float(row["daily_loss_limit"]),
                "max_equity_drawdown_pct": float(row["max_equity_drawdown_pct"]),
                "break_even_trigger_points": int(row["break_even_trigger_points"]),
                "trailing_trigger_points": int(row["trailing_trigger_points"]),
                "position_time_stop_minutes": int(row["position_time_stop_minutes"]),
                "position_stagnation_window_candles": int(row["position_stagnation_window_candles"]),
                "news_pause_enabled": bool(row["news_pause_enabled"]),
                "news_pause_symbols": str(row["news_pause_symbols"]),
                "news_pause_countries": str(row["news_pause_countries"]),
                "news_pause_before_minutes": int(row["news_pause_before_minutes"]),
                "news_pause_after_minutes": int(row["news_pause_after_minutes"]),
                "news_pause_impact": str(row["news_pause_impact"]),
                "performance_gate_enabled": bool(row["performance_gate_enabled"]),
                "performance_gate_min_profit_factor": float(row["performance_gate_min_profit_factor"]),
                "performance_gate_min_trades": int(row["performance_gate_min_trades"]),
                "validated_backtest_profit_factor": float(row["validated_backtest_profit_factor"]),
                "validated_backtest_trades": int(row["validated_backtest_trades"]),
            }
        )
        updated_at = str(row["updated_at"])

    payload["tenant_id"] = tenant_id
    payload["updated_at"] = updated_at
    return payload


def get_user_parameters(connection, tenant_id: int) -> dict:
    row = connection.execute(
        "SELECT * FROM user_parameters WHERE tenant_id = ?",
        (tenant_id,),
    ).fetchone()
    return serialize_user_parameters(row, tenant_id)


def get_effective_user_parameters(
    connection,
    tenant_id: int,
    robot_instance_id: int | None = None,
    robot_name: str | None = None,
) -> dict:
    tenant_parameters = get_user_parameters(connection, tenant_id)
    if robot_instance_id is None:
        return with_parameter_scope(tenant_parameters, parameter_scope="tenant")

    row = connection.execute(
        "SELECT * FROM robot_instance_parameters WHERE tenant_id = ? AND robot_instance_id = ?",
        (tenant_id, robot_instance_id),
    ).fetchone()
    payload = serialize_user_parameters(row, tenant_id) if row else tenant_parameters
    return with_parameter_scope(
        payload,
        parameter_scope="robot",
        scope_robot_instance_id=robot_instance_id,
        scope_robot_name=robot_name,
        scope_inherited=row is None,
    )


def upsert_user_parameters(
    connection,
    tenant_id: int,
    values: dict,
    updated_at: str,
) -> dict:
    merged = dict(DEFAULT_USER_PARAMETERS)
    merged.update(values)

    connection.execute(
        """
        INSERT INTO user_parameters (
            tenant_id, risk_per_trade, max_spread_points, default_lot,
            stop_loss_points, take_profit_points, max_positions_per_symbol,
            reentry_cooldown_seconds, max_command_age_seconds, deviation_points,
            execution_retries, pause_new_orders, use_local_fallback,
            market_session_guard_enabled, decision_engine_mode, operational_timeframe, confirmation_timeframe,
            daily_loss_limit, max_equity_drawdown_pct, break_even_trigger_points,
            trailing_trigger_points, position_time_stop_minutes, position_stagnation_window_candles,
            news_pause_enabled, news_pause_symbols, news_pause_countries,
            news_pause_before_minutes, news_pause_after_minutes, news_pause_impact,
            performance_gate_enabled, performance_gate_min_profit_factor,
            performance_gate_min_trades, validated_backtest_profit_factor,
            validated_backtest_trades, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(tenant_id) DO UPDATE SET
            risk_per_trade = excluded.risk_per_trade,
            max_spread_points = excluded.max_spread_points,
            default_lot = excluded.default_lot,
            stop_loss_points = excluded.stop_loss_points,
            take_profit_points = excluded.take_profit_points,
            max_positions_per_symbol = excluded.max_positions_per_symbol,
            reentry_cooldown_seconds = excluded.reentry_cooldown_seconds,
            max_command_age_seconds = excluded.max_command_age_seconds,
            deviation_points = excluded.deviation_points,
            execution_retries = excluded.execution_retries,
            pause_new_orders = excluded.pause_new_orders,
            use_local_fallback = excluded.use_local_fallback,
            market_session_guard_enabled = excluded.market_session_guard_enabled,
            decision_engine_mode = excluded.decision_engine_mode,
            operational_timeframe = excluded.operational_timeframe,
            confirmation_timeframe = excluded.confirmation_timeframe,
            daily_loss_limit = excluded.daily_loss_limit,
            max_equity_drawdown_pct = excluded.max_equity_drawdown_pct,
            break_even_trigger_points = excluded.break_even_trigger_points,
            trailing_trigger_points = excluded.trailing_trigger_points,
            position_time_stop_minutes = excluded.position_time_stop_minutes,
            position_stagnation_window_candles = excluded.position_stagnation_window_candles,
            news_pause_enabled = excluded.news_pause_enabled,
            news_pause_symbols = excluded.news_pause_symbols,
            news_pause_countries = excluded.news_pause_countries,
            news_pause_before_minutes = excluded.news_pause_before_minutes,
            news_pause_after_minutes = excluded.news_pause_after_minutes,
            news_pause_impact = excluded.news_pause_impact,
            performance_gate_enabled = excluded.performance_gate_enabled,
            performance_gate_min_profit_factor = excluded.performance_gate_min_profit_factor,
            performance_gate_min_trades = excluded.performance_gate_min_trades,
            validated_backtest_profit_factor = excluded.validated_backtest_profit_factor,
            validated_backtest_trades = excluded.validated_backtest_trades,
            updated_at = excluded.updated_at
        """,
        (
            tenant_id,
            float(merged["risk_per_trade"]),
            float(merged["max_spread_points"]),
            float(merged["default_lot"]),
            int(merged["stop_loss_points"]),
            int(merged["take_profit_points"]),
            int(merged["max_positions_per_symbol"]),
            int(merged["reentry_cooldown_seconds"]),
            int(merged["max_command_age_seconds"]),
            int(merged["deviation_points"]),
            int(merged["execution_retries"]),
            1 if merged["pause_new_orders"] else 0,
            1 if merged["use_local_fallback"] else 0,
            1 if merged["market_session_guard_enabled"] else 0,
            str(merged["decision_engine_mode"]),
            str(merged["operational_timeframe"]),
            str(merged["confirmation_timeframe"]),
            float(merged["daily_loss_limit"]),
            float(merged["max_equity_drawdown_pct"]),
            int(merged["break_even_trigger_points"]),
            int(merged["trailing_trigger_points"]),
            int(merged["position_time_stop_minutes"]),
            int(merged["position_stagnation_window_candles"]),
            1 if merged["news_pause_enabled"] else 0,
            str(merged["news_pause_symbols"]),
            str(merged["news_pause_countries"]),
            int(merged["news_pause_before_minutes"]),
            int(merged["news_pause_after_minutes"]),
            str(merged["news_pause_impact"]),
            1 if merged["performance_gate_enabled"] else 0,
            float(merged["performance_gate_min_profit_factor"]),
            int(merged["performance_gate_min_trades"]),
            float(merged["validated_backtest_profit_factor"]),
            int(merged["validated_backtest_trades"]),
            updated_at,
        ),
    )

    return get_effective_user_parameters(connection, tenant_id)


def upsert_robot_instance_parameters(
    connection,
    tenant_id: int,
    robot_instance_id: int,
    values: dict,
    updated_at: str,
    robot_name: str | None = None,
) -> dict:
    merged = dict(DEFAULT_USER_PARAMETERS)
    merged.update(values)

    connection.execute(
        """
        INSERT INTO robot_instance_parameters (
            tenant_id, robot_instance_id, risk_per_trade, max_spread_points, default_lot,
            stop_loss_points, take_profit_points, max_positions_per_symbol,
            reentry_cooldown_seconds, max_command_age_seconds, deviation_points,
            execution_retries, pause_new_orders, use_local_fallback,
            market_session_guard_enabled, decision_engine_mode, operational_timeframe, confirmation_timeframe,
            daily_loss_limit, max_equity_drawdown_pct, break_even_trigger_points,
            trailing_trigger_points, position_time_stop_minutes, position_stagnation_window_candles,
            news_pause_enabled, news_pause_symbols, news_pause_countries,
            news_pause_before_minutes, news_pause_after_minutes, news_pause_impact,
            performance_gate_enabled, performance_gate_min_profit_factor,
            performance_gate_min_trades, validated_backtest_profit_factor,
            validated_backtest_trades, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(robot_instance_id) DO UPDATE SET
            risk_per_trade = excluded.risk_per_trade,
            max_spread_points = excluded.max_spread_points,
            default_lot = excluded.default_lot,
            stop_loss_points = excluded.stop_loss_points,
            take_profit_points = excluded.take_profit_points,
            max_positions_per_symbol = excluded.max_positions_per_symbol,
            reentry_cooldown_seconds = excluded.reentry_cooldown_seconds,
            max_command_age_seconds = excluded.max_command_age_seconds,
            deviation_points = excluded.deviation_points,
            execution_retries = excluded.execution_retries,
            pause_new_orders = excluded.pause_new_orders,
            use_local_fallback = excluded.use_local_fallback,
            market_session_guard_enabled = excluded.market_session_guard_enabled,
            decision_engine_mode = excluded.decision_engine_mode,
            operational_timeframe = excluded.operational_timeframe,
            confirmation_timeframe = excluded.confirmation_timeframe,
            daily_loss_limit = excluded.daily_loss_limit,
            max_equity_drawdown_pct = excluded.max_equity_drawdown_pct,
            break_even_trigger_points = excluded.break_even_trigger_points,
            trailing_trigger_points = excluded.trailing_trigger_points,
            position_time_stop_minutes = excluded.position_time_stop_minutes,
            position_stagnation_window_candles = excluded.position_stagnation_window_candles,
            news_pause_enabled = excluded.news_pause_enabled,
            news_pause_symbols = excluded.news_pause_symbols,
            news_pause_countries = excluded.news_pause_countries,
            news_pause_before_minutes = excluded.news_pause_before_minutes,
            news_pause_after_minutes = excluded.news_pause_after_minutes,
            news_pause_impact = excluded.news_pause_impact,
            performance_gate_enabled = excluded.performance_gate_enabled,
            performance_gate_min_profit_factor = excluded.performance_gate_min_profit_factor,
            performance_gate_min_trades = excluded.performance_gate_min_trades,
            validated_backtest_profit_factor = excluded.validated_backtest_profit_factor,
            validated_backtest_trades = excluded.validated_backtest_trades,
            updated_at = excluded.updated_at
        """,
        (
            tenant_id,
            robot_instance_id,
            float(merged["risk_per_trade"]),
            float(merged["max_spread_points"]),
            float(merged["default_lot"]),
            int(merged["stop_loss_points"]),
            int(merged["take_profit_points"]),
            int(merged["max_positions_per_symbol"]),
            int(merged["reentry_cooldown_seconds"]),
            int(merged["max_command_age_seconds"]),
            int(merged["deviation_points"]),
            int(merged["execution_retries"]),
            1 if merged["pause_new_orders"] else 0,
            1 if merged["use_local_fallback"] else 0,
            1 if merged["market_session_guard_enabled"] else 0,
            str(merged["decision_engine_mode"]),
            str(merged["operational_timeframe"]),
            str(merged["confirmation_timeframe"]),
            float(merged["daily_loss_limit"]),
            float(merged["max_equity_drawdown_pct"]),
            int(merged["break_even_trigger_points"]),
            int(merged["trailing_trigger_points"]),
            int(merged["position_time_stop_minutes"]),
            int(merged["position_stagnation_window_candles"]),
            1 if merged["news_pause_enabled"] else 0,
            str(merged["news_pause_symbols"]),
            str(merged["news_pause_countries"]),
            int(merged["news_pause_before_minutes"]),
            int(merged["news_pause_after_minutes"]),
            str(merged["news_pause_impact"]),
            1 if merged["performance_gate_enabled"] else 0,
            float(merged["performance_gate_min_profit_factor"]),
            int(merged["performance_gate_min_trades"]),
            float(merged["validated_backtest_profit_factor"]),
            int(merged["validated_backtest_trades"]),
            updated_at,
        ),
    )

    return get_effective_user_parameters(
        connection,
        tenant_id,
        robot_instance_id=robot_instance_id,
        robot_name=robot_name,
    )
