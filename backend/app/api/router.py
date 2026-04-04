from fastapi import APIRouter

from app.api.routes import account, agent, auth, health, mt5

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(mt5.router, prefix="/mt5", tags=["mt5"])
