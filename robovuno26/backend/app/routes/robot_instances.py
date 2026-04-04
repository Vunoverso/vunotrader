from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..agent_package import build_agent_package, build_agent_package_filename
from ..audit import record_audit_event
from ..database import get_connection
from ..deps import get_session_context, now_utc
from ..instrument_catalog import (
    build_bridge_name,
    list_instrument_profiles,
    parse_discovered_symbols,
    parse_selected_symbols,
    serialize_catalog_symbols,
    serialize_selected_symbols,
)
from ..models import (
    CreateRobotInstanceRequest,
    InstrumentProfileResponse,
    RobotInstanceResponse,
    UpdateRobotInstanceRequest,
)
from ..parameter_store import get_effective_user_parameters
from ..runtime_policy import evaluate_live_mode_news_gate, evaluate_performance_gate
from ..security import generate_token
from ..subscription_store import build_subscription_entitlements


router = APIRouter(prefix="/api", tags=["robot-instances"])


def _collect_active_symbols(primary_symbol: str, selected_symbols: list[str]) -> list[str]:
    seen: set[str] = set()
    symbols: list[str] = []
    for raw in [primary_symbol, *selected_symbols]:
        symbol = str(raw or "").strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)
    return symbols


def ensure_mode_allowed(
    connection,
    *,
    tenant_id: int,
    user_id: int,
    name: str,
    mode: str,
    primary_symbol: str = "",
    selected_symbols: list[str] | None = None,
    robot_instance_id: int | None = None,
) -> None:
    parameters = get_effective_user_parameters(connection, tenant_id, robot_instance_id=robot_instance_id)
    performance_gate = evaluate_performance_gate(parameters)
    active_symbols = _collect_active_symbols(primary_symbol, selected_symbols or [])
    news_gate = evaluate_live_mode_news_gate(parameters, tracked_symbols=active_symbols)
    if mode in {"DEMO", "REAL"} and performance_gate["enabled"] and not performance_gate["passed"]:
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="robot_instance_creation_blocked",
            payload={
                "name": name,
                "mode": mode,
                "reason": "performance_gate",
                "required_profit_factor": performance_gate["min_profit_factor"],
                "required_trades": performance_gate["min_trades"],
                "validated_profit_factor": performance_gate["validated_profit_factor"],
                "validated_trades": performance_gate["validated_trades"],
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "Edge minimo ainda nao validado. Antes de liberar DEMO/REAL, informe na aba Protecoes "
                f"profit factor >= {performance_gate['min_profit_factor']:.2f} e pelo menos "
                f"{performance_gate['min_trades']} trades simulados. "
                f"Hoje o registro esta em PF {performance_gate['validated_profit_factor']:.2f} "
                f"com {performance_gate['validated_trades']} trade(s)."
            ),
        )
    if mode in {"DEMO", "REAL"} and not news_gate["passed"]:
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="robot_instance_creation_blocked",
            payload={
                "name": name,
                "mode": mode,
                "reason": "news_gate",
                "news_pause_enabled": news_gate["enabled"],
                "configured_symbols": news_gate["configured_symbols"],
                "required_symbols": news_gate["required_symbols"],
                "uncovered_symbols": news_gate["uncovered_symbols"],
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )
        if not news_gate["enabled"]:
            detail = (
                "Antes de liberar DEMO/REAL, ative a pausa por noticia na aba Protecoes. "
                "Ela passou a ser obrigatoria para segurar eventos de alto impacto antes de novas entradas."
            )
        elif news_gate["uncovered_symbols"]:
            uncovered = ", ".join(news_gate["uncovered_symbols"])
            configured = ", ".join(news_gate["configured_symbols"]) or "nenhum"
            detail = (
                "Antes de liberar DEMO/REAL, a pausa por noticia precisa cobrir os ativos desta instancia. "
                f"Ativos sem cobertura: {uncovered}. Hoje a configuracao protege: {configured}. "
                "Use '*' para cobertura geral ou liste todos os ativos monitorados na aba Protecoes."
            )
        else:
            detail = (
                "Antes de liberar DEMO/REAL, configure os ativos protegidos por noticia na aba Protecoes. "
                "Use '*' para cobertura geral ou informe explicitamente os ativos monitorados."
            )
        raise HTTPException(status_code=422, detail=detail)


def ensure_plan_robot_capacity(
    connection,
    *,
    tenant_id: int,
    user_id: int,
    robot_name: str,
) -> None:
    entitlements = build_subscription_entitlements(connection, tenant_id)
    max_bots = entitlements["limits"].get("max_bots")
    if max_bots is None:
        return

    current_total_row = connection.execute(
        "SELECT COUNT(*) AS total FROM robot_instances WHERE tenant_id = ? AND is_active = 1",
        (tenant_id,),
    ).fetchone()
    current_total = int(current_total_row["total"] or 0)
    if current_total < int(max_bots):
        return

    record_audit_event(
        connection,
        tenant_id=tenant_id,
        event_type="robot_instance_creation_blocked",
        payload={
            "name": robot_name,
            "reason": "plan_limit_max_bots",
            "plan_code": entitlements.get("plan_code"),
            "plan_name": entitlements.get("plan_name"),
            "status": entitlements.get("status"),
            "current_total": current_total,
            "max_bots": max_bots,
        },
        user_id=user_id,
    )
    raise HTTPException(
        status_code=403,
        detail=(
            f"Seu plano {entitlements.get('plan_name') or 'atual'} permite ate {max_bots} robo(s) ativo(s). "
            f"Hoje sua conta ja possui {current_total} instancia(s) cadastrada(s)."
        ),
    )


def build_robot_instance_response(row) -> RobotInstanceResponse:
    return RobotInstanceResponse(
        robot_instance_id=int(row["id"]),
        name=str(row["name"]),
        token=str(row["token"]),
        mode=str(row["mode"]),
        broker_profile=str(row["broker_profile"] or "CUSTOM"),
        primary_symbol=str(row["primary_symbol"] or ""),
        chart_timeframe=str(row["chart_timeframe"] or "M5"),
        selected_symbols=parse_selected_symbols(row["selected_symbols_json"]),
        bridge_name=str(row["bridge_name"] or build_bridge_name(int(row["id"]))),
        discovered_symbols=parse_discovered_symbols(row["discovered_symbols_json"]),
        symbols_detected_at=str(row["symbols_detected_at"]) if row["symbols_detected_at"] else None,
    )


@router.get("/instrument-profiles", response_model=list[InstrumentProfileResponse])
def get_instrument_profiles() -> list[InstrumentProfileResponse]:
    return [InstrumentProfileResponse(**profile) for profile in list_instrument_profiles()]


@router.post("/robot-instances", response_model=RobotInstanceResponse)
@router.post("/devices", response_model=RobotInstanceResponse, include_in_schema=False)
def create_robot_instance(
    payload: CreateRobotInstanceRequest,
    context=Depends(get_session_context),
) -> RobotInstanceResponse:
    created_at = now_utc().isoformat()
    token = generate_token()
    mode = payload.mode
    selected_symbols_json = serialize_selected_symbols(payload.selected_symbols)
    discovered_symbols_json = serialize_catalog_symbols([])
    tenant_id = int(context["tenant_id"])
    user_id = int(context["user_id"])
    robot_name = payload.name.strip()

    with get_connection() as connection:
        ensure_plan_robot_capacity(
            connection,
            tenant_id=tenant_id,
            user_id=user_id,
            robot_name=robot_name,
        )
        ensure_mode_allowed(
            connection,
            tenant_id=tenant_id,
            user_id=user_id,
            name=robot_name,
            mode=mode,
            primary_symbol=payload.primary_symbol,
            selected_symbols=payload.selected_symbols,
        )
        cursor = connection.execute(
            """
            INSERT INTO robot_instances (
                tenant_id, name, token, mode, broker_profile, primary_symbol, chart_timeframe,
                selected_symbols_json, discovered_symbols_json, bridge_name, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tenant_id,
                robot_name,
                token,
                mode,
                payload.broker_profile,
                payload.primary_symbol,
                payload.chart_timeframe,
                selected_symbols_json,
                discovered_symbols_json,
                "",
                created_at,
            ),
        )
        robot_instance_id = int(cursor.lastrowid)
        bridge_name = build_bridge_name(robot_instance_id)
        connection.execute(
            "UPDATE robot_instances SET bridge_name = ? WHERE id = ?",
            (bridge_name, robot_instance_id),
        )
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="robot_instance_created",
            payload={
                "name": robot_name,
                "mode": mode,
                "broker_profile": payload.broker_profile,
                "primary_symbol": payload.primary_symbol,
                "chart_timeframe": payload.chart_timeframe,
                "selected_symbols": payload.selected_symbols,
                "bridge_name": bridge_name,
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )

    return RobotInstanceResponse(
        robot_instance_id=robot_instance_id,
        name=robot_name,
        token=token,
        mode=mode,
        broker_profile=payload.broker_profile,
        primary_symbol=payload.primary_symbol,
        chart_timeframe=payload.chart_timeframe,
        selected_symbols=payload.selected_symbols,
        bridge_name=bridge_name,
        discovered_symbols=[],
        symbols_detected_at=None,
    )


@router.put("/robot-instances/{robot_instance_id}", response_model=RobotInstanceResponse)
def update_robot_instance(
    robot_instance_id: int,
    payload: UpdateRobotInstanceRequest,
    context=Depends(get_session_context),
) -> RobotInstanceResponse:
    tenant_id = int(context["tenant_id"])
    user_id = int(context["user_id"])
    robot_name = payload.name.strip()
    selected_symbols_json = serialize_selected_symbols(payload.selected_symbols)

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT id, token, bridge_name, discovered_symbols_json, symbols_detected_at
            FROM robot_instances
            WHERE id = ? AND tenant_id = ? AND is_active = 1
            """,
            (robot_instance_id, tenant_id),
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")

        ensure_mode_allowed(
            connection,
            tenant_id=tenant_id,
            user_id=user_id,
            name=robot_name,
            mode=payload.mode,
            primary_symbol=payload.primary_symbol,
            selected_symbols=payload.selected_symbols,
            robot_instance_id=robot_instance_id,
        )

        connection.execute(
            """
            UPDATE robot_instances
            SET name = ?, mode = ?, broker_profile = ?, primary_symbol = ?, chart_timeframe = ?, selected_symbols_json = ?
            WHERE id = ? AND tenant_id = ?
            """,
            (
                robot_name,
                payload.mode,
                payload.broker_profile,
                payload.primary_symbol,
                payload.chart_timeframe,
                selected_symbols_json,
                robot_instance_id,
                tenant_id,
            ),
        )
        updated_row = connection.execute(
            """
            SELECT
                id,
                name,
                token,
                mode,
                broker_profile,
                primary_symbol,
                chart_timeframe,
                selected_symbols_json,
                discovered_symbols_json,
                bridge_name,
                symbols_detected_at
            FROM robot_instances
            WHERE id = ? AND tenant_id = ?
            """,
            (robot_instance_id, tenant_id),
        ).fetchone()
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="robot_instance_updated",
            payload={
                "name": robot_name,
                "mode": payload.mode,
                "broker_profile": payload.broker_profile,
                "primary_symbol": payload.primary_symbol,
                "chart_timeframe": payload.chart_timeframe,
                "selected_symbols": payload.selected_symbols,
                "bridge_name": str(existing["bridge_name"] or build_bridge_name(robot_instance_id)),
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )

    if not updated_row:
        raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")

    return build_robot_instance_response(updated_row)


@router.get("/robot-instances/{robot_instance_id}/agent-package")
def download_agent_package(
    robot_instance_id: int,
    request: Request,
    context=Depends(get_session_context),
) -> Response:
    with get_connection() as connection:
        robot = connection.execute(
            """
            SELECT
                id,
                name,
                token,
                mode,
                bridge_name,
                broker_profile,
                primary_symbol,
                chart_timeframe,
                selected_symbols_json
            FROM robot_instances
            WHERE id = ? AND tenant_id = ? AND is_active = 1
            """,
            (robot_instance_id, int(context["tenant_id"])),
        ).fetchone()

    if not robot:
        raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")

    backend_url = str(request.base_url).rstrip("/")
    try:
        package_bytes = build_agent_package(
            robot_name=str(robot["name"]),
            robot_token=str(robot["token"]),
            backend_url=backend_url,
            mode=str(robot["mode"]),
            bridge_name=str(robot["bridge_name"] or build_bridge_name(int(robot["id"]))),
            broker_profile=str(robot["broker_profile"] or "CUSTOM"),
            primary_symbol=str(robot["primary_symbol"] or ""),
            chart_timeframe=str(robot["chart_timeframe"] or "M5"),
            selected_symbols=parse_selected_symbols(robot["selected_symbols_json"]),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    with get_connection() as connection:
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="agent_package_downloaded",
            payload={
                "name": str(robot["name"]),
                "mode": str(robot["mode"]),
                "source": "painel",
                "bridge_name": str(robot["bridge_name"] or build_bridge_name(int(robot["id"]))),
            },
            user_id=int(context["user_id"]),
            robot_instance_id=int(robot["id"]),
        )

    filename = build_agent_package_filename(str(robot["name"]), str(robot["mode"]))
    return Response(
        content=package_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/robot-instances/{robot_instance_id}")
def delete_robot_instance(
    robot_instance_id: int,
    context=Depends(get_session_context),
) -> dict[str, object]:
    tenant_id = int(context["tenant_id"])
    user_id = int(context["user_id"])

    with get_connection() as connection:
        existing = connection.execute(
            """
            SELECT id, name, mode, bridge_name
            FROM robot_instances
            WHERE id = ? AND tenant_id = ? AND is_active = 1
            """,
            (robot_instance_id, tenant_id),
        ).fetchone()

        if not existing:
            raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")

        connection.execute(
            "UPDATE robot_instances SET is_active = 0, last_status = ? WHERE id = ? AND tenant_id = ?",
            ("DELETED", robot_instance_id, tenant_id),
        )
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="robot_instance_deleted",
            payload={
                "name": str(existing["name"]),
                "mode": str(existing["mode"]),
                "bridge_name": str(existing["bridge_name"] or build_bridge_name(robot_instance_id)),
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )

    return {
        "status": "deleted",
        "robot_instance_id": robot_instance_id,
        "name": str(existing["name"]),
    }
