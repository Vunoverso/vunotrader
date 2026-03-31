from fastapi import APIRouter

from app.api.routes import account, auth, health, mt5, trading_profile

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(account.router, prefix="/account", tags=["account"])
api_router.include_router(trading_profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(mt5.router, prefix="/mt5", tags=["mt5"])