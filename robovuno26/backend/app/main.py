from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .database import get_database_driver, init_db
from .deps import resolve_session_context
from .observability import configure_logging, install_observability
from .routes.agent import router as agent_router
from .routes.admin_saas import router as admin_saas_router
from .routes.auth import router as auth_router
from .routes.monitoring import router as monitoring_router
from .routes.parameters import router as parameters_router
from .routes.robot_instances import router as robot_instances_router
from .routes.subscription import router as subscription_router
from .settings import load_settings


BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
SETTINGS = load_settings()
configure_logging(SETTINGS)
LOGGER = logging.getLogger("vuno.app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    LOGGER.info(
        "application_started",
        extra={
            "event": "startup",
            "app_env": SETTINGS.app_env,
            "service": SETTINGS.service_name,
            "version": SETTINGS.service_version,
            "cors_origins_count": len(SETTINGS.cors_allow_origins),
            "log_json": SETTINGS.log_json,
            "alert_webhook_configured": bool(SETTINGS.error_alert_webhook_url),
            "database_driver": get_database_driver(),
        },
    )
    yield


app = FastAPI(title="Vuno Trader SaaS", version=SETTINGS.service_version, lifespan=lifespan)
install_observability(app, SETTINGS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(auth_router)
app.include_router(robot_instances_router)
app.include_router(parameters_router)
app.include_router(monitoring_router)
app.include_router(agent_router)
app.include_router(subscription_router)
app.include_router(admin_saas_router)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(STATIC_DIR / "public.html")


@app.get("/login")
@app.get("/cadastro")
@app.get("/planos")
@app.get("/trial")
def public_surface() -> FileResponse:
    return FileResponse(STATIC_DIR / "public.html")


@app.get("/ops")
@app.get("/ops/")
def ops_surface(request: Request):
    try:
        resolve_session_context(request)
    except HTTPException:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": SETTINGS.service_name,
        "version": SETTINGS.service_version,
        "env": SETTINGS.app_env,
    }
