import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.security import SecurityHeadersMiddleware

log = logging.getLogger("main")


def create_app() -> FastAPI:
    try:
        settings = get_settings()
    except Exception as exc:
        log.critical(
            "[STARTUP] Falha ao carregar configurações — verifique variáveis de ambiente no Render: %s", exc
        )
        raise

    log.info(
        "[STARTUP] Ambiente: %s | Supabase URL configurada: %s",
        settings.app_env,
        bool(settings.supabase_url),
    )

    app = FastAPI(title=settings.app_name, debug=settings.app_debug)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # MT5 WebRequest não envia Origin header
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Organization-Id"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts + ["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/", tags=["Health"])
    @app.head("/", tags=["Health"])
    async def root():
        return {
            "status": "online",
            "message": "Vuno Price Action Engine is active",
            "version": "2.1.0"
        }

    return app


app = create_app()
