from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


DEFAULT_DEV_ORIGINS = "http://127.0.0.1:8000,http://localhost:3000"
VALID_APP_ENVS = {"development", "staging", "production"}
LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@dataclass(frozen=True, slots=True)
class AppSettings:
    app_env: str
    service_name: str
    service_version: str
    cors_allow_origins: list[str]
    log_level: str
    log_json: bool
    error_alert_webhook_url: str | None
    error_alert_timeout_seconds: float
    request_log_exclude_paths: set[str]


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def normalize_app_env(value: str | None) -> str:
    normalized = (value or "development").strip().lower()
    if normalized not in VALID_APP_ENVS:
        return "development"
    return normalized


def normalize_origin(origin: str) -> str:
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Origem CORS invalida: {origin}")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(f"Origem CORS deve conter apenas scheme+host[:port]: {origin}")
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_cors_allow_origins(app_env: str, raw: str | None) -> list[str]:
    source = raw if raw is not None else DEFAULT_DEV_ORIGINS
    origins: list[str] = []
    seen: set[str] = set()
    for candidate in source.split(","):
        item = candidate.strip()
        if not item:
            continue
        if item == "*":
            raise ValueError("CORS_ALLOW_ORIGINS nao aceita '*' com credenciais habilitadas")
        normalized = normalize_origin(item)
        if normalized not in seen:
            origins.append(normalized)
            seen.add(normalized)

    if not origins:
        raise ValueError("CORS_ALLOW_ORIGINS precisa conter ao menos uma origem")

    localhost_origins = []
    non_https_origins = []
    for origin in origins:
        parsed = urlparse(origin)
        host = parsed.hostname or ""
        if host in LOCALHOST_HOSTS:
            localhost_origins.append(origin)
        if parsed.scheme != "https":
            non_https_origins.append(origin)

    if app_env in {"staging", "production"} and localhost_origins:
        raise ValueError(
            "CORS_ALLOW_ORIGINS em staging/production nao pode conter localhost/127.0.0.1"
        )

    if app_env == "production" and non_https_origins:
        raise ValueError("CORS_ALLOW_ORIGINS em production deve usar somente https")

    return origins


def parse_excluded_paths(raw: str | None) -> set[str]:
    source = raw or "/api/health"
    paths = {item.strip() for item in source.split(",") if item.strip()}
    return paths or {"/api/health"}


def load_settings() -> AppSettings:
    app_env = normalize_app_env(os.getenv("APP_ENV"))
    log_json_default = app_env in {"staging", "production"}
    timeout_raw = os.getenv("ERROR_ALERT_TIMEOUT_SECONDS", "2.5").strip()
    try:
        alert_timeout = max(0.5, float(timeout_raw))
    except ValueError:
        alert_timeout = 2.5

    return AppSettings(
        app_env=app_env,
        service_name=os.getenv("SERVICE_NAME", "vuno-trader-saas").strip() or "vuno-trader-saas",
        service_version=os.getenv("SERVICE_VERSION", "0.3.0").strip() or "0.3.0",
        cors_allow_origins=parse_cors_allow_origins(app_env, os.getenv("CORS_ALLOW_ORIGINS")),
        log_level=(os.getenv("LOG_LEVEL", "INFO").strip() or "INFO").upper(),
        log_json=env_bool("LOG_JSON", log_json_default),
        error_alert_webhook_url=(os.getenv("ERROR_ALERT_WEBHOOK_URL", "").strip() or None),
        error_alert_timeout_seconds=alert_timeout,
        request_log_exclude_paths=parse_excluded_paths(os.getenv("REQUEST_LOG_EXCLUDE_PATHS")),
    )
