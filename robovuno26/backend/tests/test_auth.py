from __future__ import annotations

from datetime import datetime, timezone


def unique_email(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}.{stamp}@example.com"


def test_auth_cookie_session_cycle_and_request_id(client):
    email = unique_email("auth.cycle")
    password = "Senha123!"

    register_resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Teste Auth"},
    )
    assert register_resp.status_code == 200
    assert register_resp.headers.get("X-Request-ID")

    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200
    cookie_header = login_resp.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header
    assert "vuno_session=" in cookie_header

    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    me_payload = me_resp.json()
    assert me_payload["email"] == email

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "sessao_encerrada"

    me_after_logout = client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


def test_login_rate_limit_blocks_after_retries(client):
    email = unique_email("auth.throttle")
    password = "Senha123!"

    register_resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": "Teste Throttle"},
    )
    assert register_resp.status_code == 200

    bad_statuses: list[int] = []
    retry_after = None
    for _ in range(5):
        bad_resp = client.post("/api/auth/login", json={"email": email, "password": "senha_errada"})
        bad_statuses.append(bad_resp.status_code)
        if bad_resp.status_code == 429:
            retry_after = bad_resp.headers.get("Retry-After")
            break

    assert bad_statuses[-1] == 429
    assert retry_after is not None

    blocked_even_with_correct_password = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert blocked_even_with_correct_password.status_code == 429
