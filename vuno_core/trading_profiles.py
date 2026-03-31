"""
Perfis de configuração para o motor de trade dinâmico.

Cada perfil define limites de risco e parâmetros de entrada otimizados para um estilo.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradingProfile:
    """Parametrização de risco e entrada para o run-engine-dynamic."""

    name: str
    description: str
    max_global_positions: int
    max_positions_per_symbol: int
    max_correlated_positions: int
    max_spread_points: float
    min_atr_pct: float
    default_volume: float
    default_sl_points: float
    default_tp_points: float
    max_consecutive_losses: int
    confidence_threshold: float


PROFILE_CONSERVATIVE = TradingProfile(
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
)

PROFILE_MODERATE = TradingProfile(
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
)

PROFILE_AGGRESSIVE = TradingProfile(
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
)

PROFILES_BY_NAME: dict[str, TradingProfile] = {
    PROFILE_CONSERVATIVE.name: PROFILE_CONSERVATIVE,
    PROFILE_MODERATE.name: PROFILE_MODERATE,
    PROFILE_AGGRESSIVE.name: PROFILE_AGGRESSIVE,
}


def get_profile(name: str) -> TradingProfile | None:
    """Recupera um perfil pelo nome, case-insensitive."""
    return PROFILES_BY_NAME.get((name or "").lower())


def list_profiles() -> list[TradingProfile]:
    """Lista todos os perfis disponíveis."""
    return [PROFILE_CONSERVATIVE, PROFILE_MODERATE, PROFILE_AGGRESSIVE]
