from __future__ import annotations

import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from ..admin_saas_activity_store import record_billing_event
from ..audit import record_audit_event
from ..admin_saas_store import should_auto_grant_platform_admin
from ..database import get_connection, is_integrity_error
from ..deps import get_session_context, now_utc
from ..models import LoginRequest, LogoutResponse, RegisterRequest, SessionUserResponse, TokenResponse
from ..security import generate_token, hash_password, verify_password
from ..subscription_store import ensure_default_trial_subscription


router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_HOURS = max(1, int(os.getenv("SESSION_HOURS", "8")))
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "vuno_session")
SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN")
SESSION_COOKIE_PATH = os.getenv("SESSION_COOKIE_PATH", "/")
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "lax").strip().lower()
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
MAX_LOGIN_ATTEMPTS = max(2, int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")))
LOGIN_WINDOW_MINUTES = max(1, int(os.getenv("LOGIN_WINDOW_MINUTES", "15")))
LOGIN_BLOCK_MINUTES = max(1, int(os.getenv("LOGIN_BLOCK_MINUTES", "20")))
TOO_MANY_ATTEMPTS_DETAIL = "Muitas tentativas de login. Tente novamente em alguns minutos."

if SESSION_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    SESSION_COOKIE_SAMESITE = "lax"
if SESSION_COOKIE_SAMESITE == "none" and not SESSION_COOKIE_SECURE:
    SESSION_COOKIE_SECURE = True


def context_to_response(row) -> SessionUserResponse:
    return SessionUserResponse(
        user_id=int(row["user_id"]),
        email=str(row["email"]),
        tenant_id=int(row["tenant_id"]),
        tenant_name=str(row["tenant_name"]),
        role=str(row["role"]),
        is_platform_admin=bool(row["is_platform_admin"]),
    )


def build_tenant_name(email: str, explicit_name: str | None) -> tuple[str, str]:
    seed = explicit_name.strip() if explicit_name else f"Workspace {email.split('@', maxsplit=1)[0]}"
    slug_base = re.sub(r"[^a-z0-9]+", "-", seed.lower()).strip("-") or "tenant"
    slug = f"{slug_base}-{secrets.token_hex(3)}"
    return seed, slug


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        candidate = forwarded.split(",", maxsplit=1)[0].strip()
        if candidate:
            return candidate
    if request.client and request.client.host:
        return request.client.host.strip()
    return "unknown"


def check_login_throttle(connection, identifier: str) -> None:
    now = now_utc()
    row = connection.execute(
        """
        SELECT attempts, window_started_at, blocked_until
        FROM login_attempts
        WHERE identifier = ?
        """,
        (identifier,),
    ).fetchone()
    if not row:
        return

    blocked_until = parse_iso_datetime(str(row["blocked_until"]) if row["blocked_until"] else None)
    if blocked_until and blocked_until > now:
        retry_after = max(1, int((blocked_until - now).total_seconds()))
        raise HTTPException(
            status_code=429,
            detail=TOO_MANY_ATTEMPTS_DETAIL,
            headers={"Retry-After": str(retry_after)},
        )

    window_started_at = parse_iso_datetime(str(row["window_started_at"]) if row["window_started_at"] else None)
    if not window_started_at or now - window_started_at > timedelta(minutes=LOGIN_WINDOW_MINUTES):
        connection.execute("DELETE FROM login_attempts WHERE identifier = ?", (identifier,))


def register_failed_login_attempt(connection, identifier: str) -> int | None:
    now = now_utc()
    now_iso = now.isoformat()
    row = connection.execute(
        """
        SELECT attempts, window_started_at
        FROM login_attempts
        WHERE identifier = ?
        """,
        (identifier,),
    ).fetchone()

    blocked_until_iso: str | None = None
    if not row:
        attempts = 1
        window_started = now
        connection.execute(
            """
            INSERT INTO login_attempts (identifier, attempts, window_started_at, blocked_until, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (identifier, attempts, window_started.isoformat(), blocked_until_iso, now_iso),
        )
    else:
        attempts = int(row["attempts"] or 0)
        window_started = parse_iso_datetime(str(row["window_started_at"]) if row["window_started_at"] else None)
        if not window_started or now - window_started > timedelta(minutes=LOGIN_WINDOW_MINUTES):
            attempts = 1
            window_started = now
        else:
            attempts += 1

        if attempts >= MAX_LOGIN_ATTEMPTS:
            blocked_until = now + timedelta(minutes=LOGIN_BLOCK_MINUTES)
            blocked_until_iso = blocked_until.isoformat()

        connection.execute(
            """
            UPDATE login_attempts
            SET attempts = ?, window_started_at = ?, blocked_until = ?, updated_at = ?
            WHERE identifier = ?
            """,
            (attempts, window_started.isoformat(), blocked_until_iso, now_iso, identifier),
        )

    if blocked_until_iso:
        blocked_until = parse_iso_datetime(blocked_until_iso)
        if blocked_until and blocked_until > now:
            return max(1, int((blocked_until - now).total_seconds()))
    return None


def set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    max_age = max(1, int((expires_at - now_utc()).total_seconds()))
    cookie_kwargs = {
        "key": SESSION_COOKIE_NAME,
        "value": token,
        "max_age": max_age,
        "expires": max_age,
        "path": SESSION_COOKIE_PATH,
        "httponly": True,
        "secure": SESSION_COOKIE_SECURE,
        "samesite": SESSION_COOKIE_SAMESITE,
    }
    if SESSION_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = SESSION_COOKIE_DOMAIN
    response.set_cookie(**cookie_kwargs)


def clear_session_cookie(response: Response) -> None:
    cookie_kwargs = {"key": SESSION_COOKIE_NAME, "path": SESSION_COOKIE_PATH}
    if SESSION_COOKIE_DOMAIN:
        cookie_kwargs["domain"] = SESSION_COOKIE_DOMAIN
    response.delete_cookie(**cookie_kwargs)


def ensure_login_attempts_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS login_attempts (
            identifier TEXT PRIMARY KEY,
            attempts INTEGER NOT NULL DEFAULT 0,
            window_started_at TEXT NOT NULL,
            blocked_until TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_login_attempts_updated_at ON login_attempts(updated_at)"
    )


@router.post("/register", response_model=SessionUserResponse)
def register(payload: RegisterRequest) -> SessionUserResponse:
    created_at = now_utc().isoformat()
    email = payload.email.lower().strip()
    password_hash = hash_password(payload.password)
    tenant_name, tenant_slug = build_tenant_name(email, payload.tenant_name)
    auto_platform_admin = should_auto_grant_platform_admin(email)

    try:
        with get_connection() as connection:
            user_cursor = connection.execute(
                "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                (email, password_hash, created_at),
            )
            user_id = int(user_cursor.lastrowid)
            tenant_cursor = connection.execute(
                "INSERT INTO tenants (name, slug, created_at) VALUES (?, ?, ?)",
                (tenant_name, tenant_slug, created_at),
            )
            tenant_id = int(tenant_cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO profiles (user_id, tenant_id, role, is_default, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, tenant_id, "owner", 1, created_at),
            )
            if auto_platform_admin:
                connection.execute(
                    "UPDATE users SET is_platform_admin = 1 WHERE id = ?",
                    (user_id,),
                )
            record_audit_event(
                connection,
                tenant_id=tenant_id,
                event_type="user_registered",
                payload={"source": "bootstrap", "is_platform_admin": auto_platform_admin},
                user_id=user_id,
            )
            trial_subscription = ensure_default_trial_subscription(
                connection,
                tenant_id=tenant_id,
                created_at=created_at,
            )
            if trial_subscription:
                record_billing_event(
                    connection,
                    tenant_id=tenant_id,
                    subscription_id=int(trial_subscription["subscription_id"]),
                    event_type="subscription_created",
                    status="recorded",
                    provider="internal",
                    payload={
                        "plan_code": trial_subscription.get("plan_code"),
                        "plan_name": trial_subscription.get("plan_name"),
                        "trial_days": trial_subscription.get("trial_days"),
                    },
                    created_at=created_at,
                )
                record_audit_event(
                    connection,
                    tenant_id=tenant_id,
                    event_type="subscription_trial_started",
                    payload=trial_subscription,
                    user_id=user_id,
                )
    except Exception as exc:
        if is_integrity_error(exc):
            raise HTTPException(status_code=409, detail="Usuario ja existe") from exc
        raise

    return SessionUserResponse(
        user_id=user_id,
        email=email,
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        role="owner",
        is_platform_admin=auto_platform_admin,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> TokenResponse:
    email = payload.email.lower().strip()
    login_identifier = f"{email}|{get_client_ip(request)}"
    with get_connection() as connection:
        ensure_login_attempts_table(connection)
        now_iso = now_utc().isoformat()
        connection.execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso,))
        check_login_throttle(connection, login_identifier)

        user = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

        if not user or not verify_password(payload.password, user["password_hash"]):
            retry_after = register_failed_login_attempt(connection, login_identifier)
            connection.commit()
            if retry_after:
                raise HTTPException(
                    status_code=429,
                    detail=TOO_MANY_ATTEMPTS_DETAIL,
                    headers={"Retry-After": str(retry_after)},
                )
            raise HTTPException(status_code=401, detail="Credenciais invalidas")

        context = connection.execute(
            """
            SELECT users.id AS user_id, users.email, tenants.id AS tenant_id, tenants.name AS tenant_name, profiles.role
            , users.is_platform_admin
            FROM users
            JOIN profiles ON profiles.user_id = users.id AND profiles.is_default = 1
            JOIN tenants ON tenants.id = profiles.tenant_id
            WHERE users.id = ?
            """,
            (user["id"],),
        ).fetchone()
        connection.execute("DELETE FROM login_attempts WHERE identifier = ?", (login_identifier,))
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (int(user["id"]),))
        access_token = generate_token()
        expires_at = now_utc() + timedelta(hours=SESSION_HOURS)
        connection.execute(
            "INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (user["id"], access_token, now_utc().isoformat(), expires_at.isoformat()),
        )
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="user_logged_in",
            payload={"session_scope": "default_tenant"},
            user_id=int(user["id"]),
        )

    set_session_cookie(response, access_token, expires_at)
    return TokenResponse(
        access_token=access_token,
        expires_at=expires_at.isoformat(),
        user=context_to_response(context),
    )


@router.get("/me", response_model=SessionUserResponse)
def me(context=Depends(get_session_context)) -> SessionUserResponse:
    return context_to_response(context)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    context=Depends(get_session_context),
) -> LogoutResponse:
    token = str(context["session_token"])
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM sessions WHERE token = ? AND user_id = ?",
            (token, int(context["user_id"])),
        )
        record_audit_event(
            connection,
            tenant_id=int(context["tenant_id"]),
            event_type="user_logged_out",
            payload={"session_scope": "default_tenant"},
            user_id=int(context["user_id"]),
        )

    clear_session_cookie(response)
    return LogoutResponse(status="sessao_encerrada")
