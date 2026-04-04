from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request

from .database import get_connection

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "vuno_session")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    return authorization.removeprefix("Bearer ").strip()


def parse_session_token(request: Request, authorization: str | None) -> str:
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()

    cookie_token = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token.strip()

    raise HTTPException(status_code=401, detail="Token ausente")


def load_session_context_by_token(connection, token: str):
    return connection.execute(
        """
        SELECT
            users.id AS user_id,
            users.email,
            users.is_platform_admin,
            tenants.id AS tenant_id,
            tenants.name AS tenant_name,
            profiles.role,
            sessions.token AS session_token,
            sessions.expires_at
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        JOIN profiles ON profiles.user_id = users.id AND profiles.is_default = 1
        JOIN tenants ON tenants.id = profiles.tenant_id
        WHERE sessions.token = ?
        """,
        (token,),
    ).fetchone()


def resolve_session_context(request: Request, authorization: str | None = None):
    token = parse_session_token(request, authorization)
    with get_connection() as connection:
        row = load_session_context_by_token(connection, token)

    if not row:
        raise HTTPException(status_code=401, detail="Sessao invalida")

    if datetime.fromisoformat(row["expires_at"]) < now_utc():
        with get_connection() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        raise HTTPException(status_code=401, detail="Sessao expirada")

    return row


def get_session_context(request: Request, authorization: str | None = Header(default=None)):
    return resolve_session_context(request, authorization)


def get_robot_instance_context(
    x_device_token: str | None = Header(default=None),
    x_robot_token: str | None = Header(default=None),
):
    token = x_robot_token or x_device_token
    if not token:
        raise HTTPException(status_code=401, detail="Token do robo ausente")

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                robot_instances.id AS robot_instance_id,
                robot_instances.tenant_id,
                robot_instances.name,
                robot_instances.mode,
                robot_instances.broker_profile,
                robot_instances.primary_symbol,
                robot_instances.chart_timeframe,
                robot_instances.last_status,
                tenants.name AS tenant_name
            FROM robot_instances
            JOIN tenants ON tenants.id = robot_instances.tenant_id
            WHERE robot_instances.token = ? AND robot_instances.is_active = 1
            """,
            (token,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Instancia do robo invalida")

    return row
