from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from fastapi import APIRouter, Depends, HTTPException, Query

from ..agent_package import get_package_delivery_mode
from ..database import get_connection
from ..deps import get_session_context, now_utc
from ..instrument_catalog import build_bridge_name, parse_discovered_symbols, parse_selected_symbols
from ..models import (
    AuditEventResponse,
    OperationalSummaryResponse,
    RobotInstanceStatusResponse,
    normalize_position_action_value,
)
from ..parameter_store import get_effective_user_parameters
from ..runtime_policy import build_runtime_state
from ..audit import record_audit_event
from ..subscription_store import build_subscription_entitlements


router = APIRouter(prefix="/api", tags=["monitoring"])


def parse_datetime_filter(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} invalido. Use formato ISO-8601.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.isoformat()


def parse_position_action_filter(value: str | None) -> str | None:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        return normalize_position_action_value(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="position_action invalido. Use NONE, PROTECT ou CLOSE.") from exc


def heartbeat_age_seconds(last_heartbeat_at: str | None, now: datetime) -> int | None:
    if not last_heartbeat_at:
        return None

    try:
        parsed = datetime.fromisoformat(last_heartbeat_at)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    age = int((now - parsed).total_seconds())
    return max(age, 0)


def parse_heartbeat_details(raw_payload: object) -> dict[str, Any] | None:
    if not raw_payload:
        return None

    try:
        parsed = json.loads(str(raw_payload))
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def to_robot_instance_response(
    rows: Iterable,
    online_window_seconds: int,
    package_delivery_mode: str,
    connection,
    tenant_id: int,
) -> list[RobotInstanceStatusResponse]:
    now = now_utc()
    payload: list[RobotInstanceStatusResponse] = []

    for row in rows:
        parameters = get_effective_user_parameters(
            connection,
            tenant_id,
            robot_instance_id=int(row["id"]),
            robot_name=str(row["name"]),
        )
        runtime_state = build_runtime_state(
            parameters,
            robot_mode=str(row["mode"]),
            symbol=str(row["primary_symbol"] or ""),
            observed_at=now,
            broker_profile=str(row["broker_profile"] or "CUSTOM"),
        )
        heartbeat_details = parse_heartbeat_details(row["last_heartbeat_payload"])
        age = heartbeat_age_seconds(
            str(row["last_heartbeat_at"]) if row["last_heartbeat_at"] else None,
            now,
        )
        is_online = bool(row["is_active"]) and age is not None and age <= online_window_seconds
        payload.append(
            RobotInstanceStatusResponse(
                robot_instance_id=int(row["id"]),
                name=str(row["name"]),
                mode=str(row["mode"]),
                broker_profile=str(row["broker_profile"] or "CUSTOM"),
                primary_symbol=str(row["primary_symbol"] or ""),
                chart_timeframe=str(row["chart_timeframe"] or "M5"),
                selected_symbols=parse_selected_symbols(row["selected_symbols_json"]),
                bridge_name=str(row["bridge_name"] or build_bridge_name(int(row["id"]))),
                discovered_symbols=parse_discovered_symbols(row["discovered_symbols_json"]),
                symbols_detected_at=str(row["symbols_detected_at"]) if row["symbols_detected_at"] else None,
                is_active=bool(row["is_active"]),
                last_status=str(row["last_status"]) if row["last_status"] else None,
                last_heartbeat_at=str(row["last_heartbeat_at"]) if row["last_heartbeat_at"] else None,
                last_heartbeat_details=heartbeat_details,
                package_delivery_mode=package_delivery_mode,
                is_online=is_online,
                heartbeat_age_seconds=age,
                runtime_pause_new_orders=bool(runtime_state["runtime_pause_new_orders"]),
                runtime_pause_reasons=list(runtime_state["runtime_pause_reasons"]),
                operational_timeframe=str(runtime_state["operational_timeframe"]),
                confirmation_timeframe=str(runtime_state["confirmation_timeframe"]),
                performance_gate_passed=bool(runtime_state["performance_gate_passed"]),
                news_pause_active=bool(runtime_state["news_pause_active"]),
            )
        )

    return payload


def extend_time_filter(
    where_clauses: list[str],
    params: list[object],
    date_from: str | None,
    date_to: str | None,
    column_name: str,
) -> None:
    if date_from:
        where_clauses.append(f"{column_name} >= ?")
        params.append(date_from)
    if date_to:
        where_clauses.append(f"{column_name} <= ?")
        params.append(date_to)


def ensure_audit_feature_access(connection, *, tenant_id: int, user_id: int) -> None:
    entitlements = build_subscription_entitlements(connection, tenant_id)
    if bool(entitlements.get("has_active_plan")):
        return

    record_audit_event(
        connection,
        tenant_id=tenant_id,
        event_type="saas_feature_blocked",
        payload={
            "feature": "audit_events",
            "required_plan_status": "active",
            "plan_code": entitlements.get("plan_code"),
            "plan_name": entitlements.get("plan_name"),
            "status": entitlements.get("status"),
            "trial_days_left": entitlements.get("trial_days_left"),
        },
        user_id=user_id,
    )
    raise HTTPException(
        status_code=403,
        detail=(
            "Historico detalhado exige plano ativo. "
            f"Plano atual: {entitlements.get('plan_name') or 'sem assinatura'} "
            f"com status {entitlements.get('status') or 'none'}."
        ),
    )


@router.get("/robot-instances", response_model=list[RobotInstanceStatusResponse])
def list_robot_instances(
    search: str | None = Query(default=None, min_length=1, max_length=80),
    mode: str | None = Query(default=None, pattern="^(DEMO|REAL)$"),
    status: str = Query(default="all", pattern="^(all|online|offline)$"),
    online_window_seconds: int = Query(default=120, ge=30, le=3600),
    context=Depends(get_session_context),
) -> list[RobotInstanceStatusResponse]:
    where_clauses = ["tenant_id = ?", "is_active = 1"]
    params: list[object] = [int(context["tenant_id"])]

    if search:
        where_clauses.append("LOWER(name) LIKE ?")
        params.append(f"%{search.lower()}%")

    if mode:
        where_clauses.append("mode = ?")
        params.append(mode)

    query = f"""
        SELECT
            id,
            name,
            mode,
            broker_profile,
            primary_symbol,
            chart_timeframe,
            selected_symbols_json,
            discovered_symbols_json,
            bridge_name,
            symbols_detected_at,
            is_active,
            last_status,
            last_heartbeat_at,
            last_heartbeat_payload
        FROM robot_instances
        WHERE {" AND ".join(where_clauses)}
        ORDER BY id DESC
    """

    with get_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
        payload = to_robot_instance_response(
            rows,
            online_window_seconds,
            get_package_delivery_mode(),
            connection,
            int(context["tenant_id"]),
        )
    if status == "online":
        return [item for item in payload if item.is_online]
    if status == "offline":
        return [item for item in payload if not item.is_online]
    return payload


@router.get("/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = Query(default=None, min_length=2, max_length=80),
    robot_instance_id: int | None = Query(default=None, ge=1),
    position_action: str | None = Query(default=None, min_length=4, max_length=7),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    context=Depends(get_session_context),
) -> list[AuditEventResponse]:
    parsed_from = parse_datetime_filter(date_from, "date_from")
    parsed_to = parse_datetime_filter(date_to, "date_to")

    parsed_position_action = parse_position_action_filter(position_action)

    with get_connection() as connection:
        ensure_audit_feature_access(
            connection,
            tenant_id=int(context["tenant_id"]),
            user_id=int(context["user_id"]),
        )
        where_clauses = ["audit_events.tenant_id = ?"]
        params: list[object] = [int(context["tenant_id"])]

        if event_type:
            where_clauses.append("audit_events.event_type = ?")
            params.append(event_type.strip())

        if robot_instance_id:
            where_clauses.append("audit_events.robot_instance_id = ?")
            params.append(int(robot_instance_id))

        if parsed_position_action:
            if connection.driver == "postgres":
                where_clauses.append(
                    "LOWER(COALESCE(audit_events.payload::jsonb -> 'analysis' ->> 'engine', '')) = 'position_manager_v1'"
                )
                where_clauses.append(
                    "UPPER(COALESCE(audit_events.payload::jsonb ->> 'position_action', audit_events.payload::jsonb -> 'analysis' ->> 'management_action', 'NONE')) = ?"
                )
            else:
                where_clauses.append(
                    "LOWER(COALESCE(json_extract(audit_events.payload, '$.analysis.engine'), '')) = 'position_manager_v1'"
                )
                where_clauses.append(
                    "UPPER(COALESCE(json_extract(audit_events.payload, '$.position_action'), json_extract(audit_events.payload, '$.analysis.management_action'), 'NONE')) = ?"
                )
            params.append(parsed_position_action)

        extend_time_filter(where_clauses, params, parsed_from, parsed_to, "audit_events.created_at")
        params.append(limit)

        query = f"""
            SELECT
                audit_events.id,
                audit_events.event_type,
                audit_events.payload,
                audit_events.robot_instance_id,
                audit_events.user_id,
                audit_events.created_at,
                robot_instances.name AS robot_name
            FROM audit_events
            LEFT JOIN robot_instances ON robot_instances.id = audit_events.robot_instance_id
            WHERE {" AND ".join(where_clauses)}
            ORDER BY audit_events.id DESC
            LIMIT ?
        """

        rows = connection.execute(query, tuple(params)).fetchall()

    payload: list[AuditEventResponse] = []
    for row in rows:
        try:
            event_payload = json.loads(str(row["payload"]))
        except json.JSONDecodeError:
            event_payload = {"raw_payload": str(row["payload"])}

        payload.append(
            AuditEventResponse(
                event_id=int(row["id"]),
                event_type=str(row["event_type"]),
                payload=event_payload,
                robot_instance_id=int(row["robot_instance_id"]) if row["robot_instance_id"] else None,
                robot_name=str(row["robot_name"]) if row["robot_name"] else None,
                user_id=int(row["user_id"]) if row["user_id"] else None,
                created_at=str(row["created_at"]),
            )
        )

    return payload


@router.get("/summary", response_model=OperationalSummaryResponse)
def operational_summary(
    robot_instance_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    online_window_seconds: int = Query(default=120, ge=30, le=3600),
    context=Depends(get_session_context),
) -> OperationalSummaryResponse:
    tenant_id = int(context["tenant_id"])
    parsed_from = parse_datetime_filter(date_from, "date_from")
    parsed_to = parse_datetime_filter(date_to, "date_to")

    decisions_where = ["tenant_id = ?"]
    decisions_params: list[object] = [tenant_id]
    if robot_instance_id:
        decisions_where.append("robot_instance_id = ?")
        decisions_params.append(int(robot_instance_id))
    extend_time_filter(decisions_where, decisions_params, parsed_from, parsed_to, "created_at")

    results_where = ["tenant_id = ?"]
    results_params: list[object] = [tenant_id]
    if robot_instance_id:
        results_where.append("robot_instance_id = ?")
        results_params.append(int(robot_instance_id))
    extend_time_filter(results_where, results_params, parsed_from, parsed_to, "closed_at")

    instances_where = ["tenant_id = ?", "is_active = 1"]
    instances_params: list[object] = [tenant_id]
    if robot_instance_id:
        instances_where.append("id = ?")
        instances_params.append(int(robot_instance_id))

    with get_connection() as connection:
        decisions_rows = connection.execute(
            f"""
            SELECT decision_payload, created_at
            FROM trade_decisions
            WHERE {" AND ".join(decisions_where)}
            """,
            tuple(decisions_params),
        ).fetchall()

        results_row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS results_total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) AS losses,
                COALESCE(SUM(pnl), 0) AS pnl_total,
                COALESCE(AVG(pnl), 0) AS pnl_average,
                COALESCE(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END), 0) AS gross_profit,
                COALESCE(SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END), 0) AS gross_loss,
                MAX(closed_at) AS last_result_at
            FROM trade_results
            WHERE {" AND ".join(results_where)}
            """,
            tuple(results_params),
        ).fetchone()

        instances_rows = connection.execute(
            f"""
            SELECT
                id,
                name,
                mode,
                broker_profile,
                primary_symbol,
                chart_timeframe,
                selected_symbols_json,
                discovered_symbols_json,
                bridge_name,
                symbols_detected_at,
                is_active,
                last_status,
                last_heartbeat_at,
                last_heartbeat_payload
            FROM robot_instances
            WHERE {" AND ".join(instances_where)}
            """,
            tuple(instances_params),
        ).fetchall()
        instance_payload = to_robot_instance_response(
            instances_rows,
            online_window_seconds,
            get_package_delivery_mode(),
            connection,
            tenant_id,
        )
    instances_total = len(instance_payload)
    instances_online = sum(1 for instance in instance_payload if instance.is_online)

    decisions_total = len(decisions_rows)
    buy_signals = 0
    sell_signals = 0
    hold_signals = 0
    last_decision_at: str | None = None

    for row in decisions_rows:
        try:
            decision_payload = json.loads(str(row["decision_payload"]))
        except json.JSONDecodeError:
            decision_payload = {}

        signal = str(decision_payload.get("signal", "")).upper()
        if signal == "BUY":
            buy_signals += 1
        elif signal == "SELL":
            sell_signals += 1
        else:
            hold_signals += 1

        created_at = str(row["created_at"]) if row["created_at"] else None
        if created_at and (last_decision_at is None or created_at > last_decision_at):
            last_decision_at = created_at

    results_total = int(results_row["results_total"] or 0)
    wins = int(results_row["wins"] or 0)
    losses = int(results_row["losses"] or 0)
    pnl_total = float(results_row["pnl_total"] or 0.0)
    pnl_average = float(results_row["pnl_average"] or 0.0)
    gross_profit = float(results_row["gross_profit"] or 0.0)
    gross_loss = float(results_row["gross_loss"] or 0.0)
    last_result_at = str(results_row["last_result_at"]) if results_row["last_result_at"] else None

    win_rate_pct = round((wins / results_total) * 100, 2) if results_total > 0 else 0.0
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else round(gross_profit, 4)

    return OperationalSummaryResponse(
        tenant_id=tenant_id,
        robot_instance_id=int(robot_instance_id) if robot_instance_id else None,
        decisions_total=decisions_total,
        buy_signals=buy_signals,
        sell_signals=sell_signals,
        hold_signals=hold_signals,
        results_total=results_total,
        wins=wins,
        losses=losses,
        win_rate_pct=win_rate_pct,
        pnl_total=round(pnl_total, 2),
        pnl_average=round(pnl_average, 2),
        profit_factor=profit_factor,
        instances_total=instances_total,
        instances_online=instances_online,
        last_decision_at=last_decision_at,
        last_result_at=last_result_at,
    )
