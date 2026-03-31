from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.services.auth import AuthenticatedUser

router = APIRouter()


class TradingProfileResponse(BaseModel):
    name: str = "moderado"
    description: str = ""
    max_global_positions: int = 3
    max_positions_per_symbol: int = 1
    max_correlated_positions: int = 2
    max_spread_points: float = 30.0
    min_atr_pct: float = 0.00035
    default_volume: float = 0.02
    default_sl_points: float = 120
    default_tp_points: float = 120
    max_consecutive_losses: int = 3
    confidence_threshold: float = 0.65


class TradingProfileRequest(BaseModel):
    profile_name: str = "moderado"


PROFILE_DEFAULTS: dict[str, TradingProfileResponse] = {
    "conservador": TradingProfileResponse(
        name="conservador",
        description="Entrada seletiva, risco baixo, poucas posições abertas simultaneamente.",
        max_global_positions=2,
        max_positions_per_symbol=1,
        max_correlated_positions=1,
        max_spread_points=15.0,
        min_atr_pct=0.0005,
        default_volume=0.01,
        default_sl_points=150,
        default_tp_points=150,
        max_consecutive_losses=2,
        confidence_threshold=0.72,
    ),
    "moderado": TradingProfileResponse(
        name="moderado",
        description="Entrada balanceada, risco médio, até 3 posições diversificadas.",
        max_global_positions=3,
        max_positions_per_symbol=1,
        max_correlated_positions=2,
        max_spread_points=30.0,
        min_atr_pct=0.00035,
        default_volume=0.02,
        default_sl_points=120,
        default_tp_points=120,
        max_consecutive_losses=3,
        confidence_threshold=0.65,
    ),
    "agressivo": TradingProfileResponse(
        name="agressivo",
        description="Entrada dinâmica, risco elevado, até 5 posições com correlação permitida.",
        max_global_positions=5,
        max_positions_per_symbol=2,
        max_correlated_positions=3,
        max_spread_points=50.0,
        min_atr_pct=0.0002,
        default_volume=0.05,
        default_sl_points=80,
        default_tp_points=80,
        max_consecutive_losses=4,
        confidence_threshold=0.55,
    ),
}


@router.get("/trading-profiles")
def list_trading_profiles() -> list[TradingProfileResponse]:
    """Lista todos os perfis de trading disponíveis."""
    return list(PROFILE_DEFAULTS.values())


@router.get("/trading-profile")
def get_trading_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TradingProfileResponse:
    """Recupera o perfil de trading salvo do usuário (padrão: moderado)."""
    profile_name = "moderado"
    return PROFILE_DEFAULTS.get(profile_name, PROFILE_DEFAULTS["moderado"])


@router.post("/trading-profile")
def set_trading_profile(
    req: TradingProfileRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> TradingProfileResponse:
    """Salva o perfil de trading selecionado para o usuário."""
    profile = PROFILE_DEFAULTS.get(req.profile_name.lower(), PROFILE_DEFAULTS["moderado"])
    return profile
