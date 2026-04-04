from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..audit import record_audit_event
from ..database import get_connection
from ..deps import get_session_context, now_utc
from ..models import UserParametersPayload, UserParametersResponse
from ..parameter_store import get_effective_user_parameters, upsert_robot_instance_parameters, upsert_user_parameters
from ..runtime_policy import build_parameters_response_payload


router = APIRouter(prefix="/api", tags=["parameters"])


def load_robot_instance_scope(connection, tenant_id: int, robot_instance_id: int):
    row = connection.execute(
        "SELECT id, name FROM robot_instances WHERE id = ? AND tenant_id = ? AND is_active = 1",
        (robot_instance_id, tenant_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Instancia do robo nao encontrada")
    return row


@router.get("/parameters", response_model=UserParametersResponse)
def read_parameters(
    robot_instance_id: int | None = Query(default=None, ge=1),
    context=Depends(get_session_context),
) -> UserParametersResponse:
    tenant_id = int(context["tenant_id"])
    with get_connection() as connection:
        robot_row = load_robot_instance_scope(connection, tenant_id, robot_instance_id) if robot_instance_id else None
        payload = get_effective_user_parameters(
            connection,
            tenant_id,
            robot_instance_id=robot_instance_id,
            robot_name=str(robot_row["name"]) if robot_row else None,
        )
    return UserParametersResponse(**build_parameters_response_payload(payload))


@router.put("/parameters", response_model=UserParametersResponse)
def write_parameters(
    payload: UserParametersPayload,
    robot_instance_id: int | None = Query(default=None, ge=1),
    context=Depends(get_session_context),
) -> UserParametersResponse:
    updated_at = now_utc().isoformat()
    tenant_id = int(context["tenant_id"])
    user_id = int(context["user_id"])
    with get_connection() as connection:
        robot_row = load_robot_instance_scope(connection, tenant_id, robot_instance_id) if robot_instance_id else None
        if robot_row:
            stored = upsert_robot_instance_parameters(
                connection,
                tenant_id=tenant_id,
                robot_instance_id=robot_instance_id,
                values=payload.model_dump(),
                updated_at=updated_at,
                robot_name=str(robot_row["name"]),
            )
        else:
            stored = upsert_user_parameters(
                connection,
                tenant_id=tenant_id,
                values=payload.model_dump(),
                updated_at=updated_at,
            )
        record_audit_event(
            connection,
            tenant_id=tenant_id,
            event_type="user_parameters_updated",
            payload={
                "parameter_scope": "robot" if robot_row else "tenant",
                "scope_robot_name": str(robot_row["name"]) if robot_row else None,
                "updated_fields": payload.model_dump(),
            },
            user_id=user_id,
            robot_instance_id=robot_instance_id,
        )

    return UserParametersResponse(**build_parameters_response_payload(stored))
