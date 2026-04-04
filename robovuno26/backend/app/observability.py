from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from urllib.request import Request as UrlRequest
from urllib.request import urlopen
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .settings import AppSettings

APP_LOGGER = logging.getLogger("vuno.app")
REQUEST_LOGGER = logging.getLogger("vuno.request")


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                continue
            if key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=True, default=str)


def configure_logging(settings: AppSettings) -> None:
    level = getattr(logging, settings.log_level, logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    handler = logging.StreamHandler()
    if settings.log_json:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )

    root.addHandler(handler)


def _send_error_alert(settings: AppSettings, payload: dict[str, object]) -> None:
    if not settings.error_alert_webhook_url:
        return

    request = UrlRequest(
        url=settings.error_alert_webhook_url,
        data=json.dumps(payload, ensure_ascii=True).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.error_alert_timeout_seconds):
            pass
    except Exception as exc:  # pragma: no cover - best effort
        APP_LOGGER.warning("error_alert_delivery_failed", extra={"reason": str(exc)})


def install_observability(app: FastAPI, settings: AppSettings) -> None:
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "").strip() or uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            REQUEST_LOGGER.error(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        path = request.url.path
        if path not in settings.request_log_exclude_paths:
            log_extra = {
                "request_id": request_id,
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else None,
            }
            if response.status_code >= 500:
                REQUEST_LOGGER.error("request_completed", extra=log_extra)
            elif response.status_code >= 400:
                REQUEST_LOGGER.warning("request_completed", extra=log_extra)
            else:
                REQUEST_LOGGER.info("request_completed", extra=log_extra)

        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", uuid4().hex)
        APP_LOGGER.exception(
            "unhandled_exception",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "event": "unhandled_exception",
            },
        )

        alert_payload = {
            "service": settings.service_name,
            "version": settings.service_version,
            "env": settings.app_env,
            "event": "unhandled_exception",
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if settings.error_alert_webhook_url:
            threading.Thread(
                target=_send_error_alert,
                args=(settings, alert_payload),
                daemon=True,
            ).start()

        response = JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor", "request_id": request_id},
        )
        response.headers["X-Request-ID"] = request_id
        return response
