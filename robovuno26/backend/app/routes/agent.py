from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from ..audit import record_audit_event
from ..database import get_connection
from ..decision_engine import evaluate_snapshot
from ..deps import get_robot_instance_context, now_utc
from ..instrument_catalog import (
    merge_primary_symbol,
    parse_discovered_symbols,
    parse_selected_symbols,
    serialize_catalog_symbols,
    serialize_selected_symbols,
)
from ..models import (
    AgentSymbolCatalogRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    RuntimeConfigResponse,
    SnapshotRequest,
    TradeFeedbackRequest,
    UserParametersResponse,
)
from ..parameter_store import get_effective_user_parameters
from ..runtime_policy import (
    attach_runtime_context,
    build_parameters_response_payload,
    evaluate_drawdown_guard,
    build_runtime_guard_decision,
    build_runtime_state,
)


router = APIRouter(prefix="/api/agent", tags=["agent"])


def load_daily_closed_pnl(connection, tenant_id: int, robot_instance_id: int, observed_at) -> float:
    day_start = observed_at.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    row = connection.execute(
        """
        SELECT COALESCE(SUM(pnl), 0) AS daily_closed_pnl
        FROM trade_results
        WHERE tenant_id = ? AND robot_instance_id = ? AND created_at >= ?
        """,
        (tenant_id, robot_instance_id, day_start),
    ).fetchone()
    return float(row["daily_closed_pnl"] or 0.0) if row else 0.0


def apply_runtime_parameters(decision, parameters: dict):
    decision.risk = min(float(decision.risk), float(parameters["risk_per_trade"]))

    if decision.signal != "HOLD":
        if int(decision.stop_loss_points) <= 0:
            decision.stop_loss_points = int(parameters["stop_loss_points"])
        if int(decision.take_profit_points) <= 0:
            decision.take_profit_points = int(parameters["take_profit_points"])

    return decision


@router.get("/runtime-config", response_model=RuntimeConfigResponse)
def runtime_config(robot=Depends(get_robot_instance_context)) -> RuntimeConfigResponse:
    with get_connection() as connection:
        parameters = get_effective_user_parameters(
            connection,
            int(robot["tenant_id"]),
            robot_instance_id=int(robot["robot_instance_id"]),
            robot_name=str(robot["name"]),
        )
    runtime_state = build_runtime_state(
        parameters,
        robot_mode=str(robot["mode"]),
        symbol=str(robot["primary_symbol"] or ""),
        observed_at=now_utc(),
        broker_profile=str(robot["broker_profile"] or "CUSTOM"),
    )

    return RuntimeConfigResponse(
        robot_instance_id=int(robot["robot_instance_id"]),
        robot_name=str(robot["name"]),
        robot_mode=str(robot["mode"]),
        parameters=UserParametersResponse(**build_parameters_response_payload(parameters, robot_mode=str(robot["mode"]))),
        runtime_pause_new_orders=bool(runtime_state["runtime_pause_new_orders"]),
        runtime_pause_reasons=list(runtime_state["runtime_pause_reasons"]),
        operational_timeframe=str(runtime_state["operational_timeframe"]),
        confirmation_timeframe=str(runtime_state["confirmation_timeframe"]),
        news_pause_active=bool(runtime_state["news_pause_active"]),
        performance_gate_passed=bool(runtime_state["performance_gate_passed"]),
    )


@router.post("/decision")
def agent_decision(
    payload: SnapshotRequest,
    robot=Depends(get_robot_instance_context),
) -> dict[str, object]:
    observed_now = now_utc()
    created_at = observed_now.isoformat()

    with get_connection() as connection:
        parameters = get_effective_user_parameters(
            connection,
            int(robot["tenant_id"]),
            robot_instance_id=int(robot["robot_instance_id"]),
            robot_name=str(robot["name"]),
        )
        runtime_state = build_runtime_state(
            parameters,
            robot_mode=str(robot["mode"]),
            symbol=payload.symbol,
            observed_at=observed_now,
            broker_profile=str(robot["broker_profile"] or "CUSTOM"),
        )
        drawdown_guard = evaluate_drawdown_guard(
            parameters,
            payload,
            daily_closed_pnl=load_daily_closed_pnl(
                connection,
                tenant_id=int(robot["tenant_id"]),
                robot_instance_id=int(robot["robot_instance_id"]),
                observed_at=observed_now,
            ),
        )
        runtime_state["drawdown_guard_active"] = bool(drawdown_guard["active"])
        runtime_state["daily_closed_pnl"] = float(drawdown_guard["daily_closed_pnl"])
        runtime_state["daily_loss_limit"] = float(drawdown_guard["daily_loss_limit"])
        runtime_state["balance"] = float(drawdown_guard["balance"])
        runtime_state["equity"] = float(drawdown_guard["equity"])
        runtime_state["equity_drawdown_pct"] = float(drawdown_guard["equity_drawdown_pct"])
        runtime_state["max_equity_drawdown_pct"] = float(drawdown_guard["max_equity_drawdown_pct"])
        if drawdown_guard["active"]:
            existing_reasons = list(runtime_state["runtime_pause_reasons"])
            for reason in drawdown_guard["reasons"]:
                if reason not in existing_reasons:
                    existing_reasons.append(reason)
            runtime_state["runtime_pause_reasons"] = existing_reasons
            runtime_state["runtime_pause_new_orders"] = True
        decision = build_runtime_guard_decision(payload, runtime_state)
        if decision is None:
            decision = attach_runtime_context(
                apply_runtime_parameters(
                    evaluate_snapshot(
                        payload,
                        decision_engine_mode=str(parameters.get("decision_engine_mode", "HYBRID")),
                        management_settings=parameters,
                    ),
                    parameters,
                ),
                payload,
                runtime_state,
            )
        connection.execute(
            """
            INSERT INTO trade_decisions (
                tenant_id, robot_instance_id, symbol, timeframe,
                snapshot_payload, decision_payload, captured_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(robot["tenant_id"]),
                int(robot["robot_instance_id"]),
                payload.symbol,
                payload.timeframe,
                payload.model_dump_json(),
                decision.model_dump_json(),
                payload.captured_at,
                created_at,
            ),
        )
        analysis_engine = str((decision.analysis or {}).get("engine", "")).lower()
        is_position_management = analysis_engine == "position_manager_v1" or str(decision.position_action or "NONE").upper() != "NONE"
        audit_event_type = "position_management_recorded" if is_position_management else "trade_decision_recorded"
        record_audit_event(
            connection,
            tenant_id=int(robot["tenant_id"]),
            event_type=audit_event_type,
            payload={
                "symbol": payload.symbol,
                "timeframe": payload.timeframe,
                "confirmation_timeframe": payload.htf_timeframe,
                "signal": decision.signal,
                "rationale": decision.rationale,
                "position_action": decision.position_action,
                "position_ticket": decision.position_ticket,
                "position_stop_loss": decision.position_stop_loss,
                "position_take_profit": decision.position_take_profit,
                "analysis": decision.analysis,
            },
            robot_instance_id=int(robot["robot_instance_id"]),
        )

    return {
        "robot_instance": {
            "id": int(robot["robot_instance_id"]),
            "name": str(robot["name"]),
            "mode": str(robot["mode"]),
        },
        "decision": decision.model_dump(),
    }


@router.post("/trade-feedback")
def trade_feedback(
    payload: TradeFeedbackRequest,
    robot=Depends(get_robot_instance_context),
) -> dict[str, str]:
    created_at = now_utc().isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO trade_results (
                tenant_id, robot_instance_id, symbol, outcome, pnl, payload, closed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(robot["tenant_id"]),
                int(robot["robot_instance_id"]),
                payload.symbol,
                payload.outcome,
                payload.pnl,
                payload.model_dump_json(),
                payload.closed_at,
                created_at,
            ),
        )
        record_audit_event(
            connection,
            tenant_id=int(robot["tenant_id"]),
            event_type="trade_result_recorded",
            payload={
                "symbol": payload.symbol,
                "outcome": payload.outcome,
                "pnl": payload.pnl,
            },
            robot_instance_id=int(robot["robot_instance_id"]),
        )

    return {"status": "feedback_recebido"}


@router.post("/symbol-catalog")
def symbol_catalog(
    payload: AgentSymbolCatalogRequest,
    robot=Depends(get_robot_instance_context),
) -> dict[str, object]:
    observed_at = now_utc().isoformat()
    discovered_symbols = payload.available_symbols or payload.market_watch_symbols
    tracked_symbols = payload.tracked_symbols

    with get_connection() as connection:
        current = connection.execute(
            """
            SELECT
                id,
                bridge_name,
                primary_symbol,
                chart_timeframe,
                selected_symbols_json,
                discovered_symbols_json
            FROM robot_instances
            WHERE id = ? AND tenant_id = ? AND is_active = 1
            """,
            (int(robot["robot_instance_id"]), int(robot["tenant_id"])),
        ).fetchone()

        if not current:
            raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")

        current_selected = parse_selected_symbols(current["selected_symbols_json"])
        if tracked_symbols:
            current_selected = tracked_symbols

        next_primary_symbol, next_selected_symbols = merge_primary_symbol(
            payload.chart_symbol or current["primary_symbol"],
            current_selected,
        )
        next_chart_timeframe = payload.chart_timeframe or str(current["chart_timeframe"] or "M5")
        next_discovered_json = serialize_catalog_symbols(discovered_symbols)
        next_selected_json = serialize_selected_symbols(next_selected_symbols)

        current_discovered = parse_discovered_symbols(current["discovered_symbols_json"])
        bridge_name_expected = str(current["bridge_name"] or "")
        bridge_name_reported = str(payload.bridge_name or "")
        has_changes = (
            current_discovered != discovered_symbols
            or parse_selected_symbols(current["selected_symbols_json"]) != next_selected_symbols
            or str(current["primary_symbol"] or "") != next_primary_symbol
            or str(current["chart_timeframe"] or "M5") != next_chart_timeframe
            or (bridge_name_reported and bridge_name_expected and bridge_name_reported != bridge_name_expected)
        )

        connection.execute(
            """
            UPDATE robot_instances
            SET discovered_symbols_json = ?, symbols_detected_at = ?, primary_symbol = ?, chart_timeframe = ?, selected_symbols_json = ?
            WHERE id = ?
            """,
            (
                next_discovered_json,
                observed_at,
                next_primary_symbol,
                next_chart_timeframe,
                next_selected_json,
                int(robot["robot_instance_id"]),
            ),
        )

        if has_changes:
            record_audit_event(
                connection,
                tenant_id=int(robot["tenant_id"]),
                event_type="robot_symbols_detected",
                payload={
                    "bridge_name_expected": bridge_name_expected,
                    "bridge_name_reported": bridge_name_reported,
                    "chart_symbol": next_primary_symbol,
                    "chart_timeframe": next_chart_timeframe,
                    "available_symbols_count": len(discovered_symbols),
                    "tracked_symbols": next_selected_symbols,
                    "market_watch_symbols_count": len(payload.market_watch_symbols),
                    "account_login": payload.account_login,
                    "server": payload.server,
                    "company": payload.company,
                    "terminal_name": payload.terminal_name,
                    "exported_at": payload.exported_at,
                },
                robot_instance_id=int(robot["robot_instance_id"]),
            )

    return {
        "status": "catalogo_recebido",
        "symbols_detected": len(discovered_symbols),
        "tracked_symbols": next_selected_symbols,
        "primary_symbol": next_primary_symbol,
        "chart_timeframe": next_chart_timeframe,
    }


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(
    payload: HeartbeatRequest,
    robot=Depends(get_robot_instance_context),
) -> HeartbeatResponse:
    details = payload.details or {}

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE robot_instances
            SET last_status = ?, last_heartbeat_at = ?, last_heartbeat_payload = ?
            WHERE id = ?
            """,
            (
                payload.status,
                payload.observed_at,
                json.dumps(details, ensure_ascii=True),
                int(robot["robot_instance_id"]),
            ),
        )
        if str(robot["last_status"] or "") != payload.status:
            record_audit_event(
                connection,
                tenant_id=int(robot["tenant_id"]),
                event_type="robot_status_changed",
                payload={"status": payload.status, "details": details},
                robot_instance_id=int(robot["robot_instance_id"]),
            )

    return HeartbeatResponse(status=payload.status, last_heartbeat_at=payload.observed_at)
