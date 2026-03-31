#!/usr/bin/env python3
"""
Helper para aplicar perfis de trading ao motor local.

Uso:
  python scripts/apply_trading_profile.py --profile conservador
  python scripts/apply_trading_profile.py --profile moderado
  python scripts/apply_trading_profile.py --profile agressivo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from vuno_core.trading_profiles import PROFILES_BY_NAME, get_profile


def main() -> int:
    parser = argparse.ArgumentParser(description="Aplicar perfis de trading pré-configurados")
    parser.add_argument(
        "--profile",
        choices=list(PROFILES_BY_NAME.keys()),
        default="moderado",
        help="Nome do perfil (conservador, moderado, agressivo)",
    )
    parser.add_argument(
        "--print-command",
        action="store_true",
        help="Exibe o comando run-engine-dynamic pronto com os parâmetros do perfil",
    )
    parser.add_argument(
        "--symbols",
        default="EURUSD,GBPUSD,USDJPY,XAUUSD",
        help="Símbolos para escanear (padrão: EURUSD,GBPUSD,USDJPY,XAUUSD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa modo dry-run (sem enviar ordens reais)",
    )

    args = parser.parse_args()
    profile = get_profile(args.profile)
    if not profile:
        print(f"Perfil '{args.profile}' não encontrado.")
        return 1

    print(f"\n[profile] {profile.name.upper()}: {profile.description}\n")
    print(f"Configurações:")
    print(f"  Posições globais:     até {profile.max_global_positions}")
    print(f"  Posições por símbolo: até {profile.max_positions_per_symbol}")
    print(f"  Correlações permitidas: até {profile.max_correlated_positions}")
    print(f"  Spread máximo:        {profile.max_spread_points:.1f} pontos")
    print(f"  ATR mínimo:           {profile.min_atr_pct:.5f} ({profile.min_atr_pct*100:.3f}%)")
    print(f"  Volume padrão:        {profile.default_volume:.3f}")
    print(f"  Stop loss:            {profile.default_sl_points} pontos")
    print(f"  Take profit:          {profile.default_tp_points} pontos")
    print(f"  Max perdas seguidas:  {profile.max_consecutive_losses}")
    print(f"  Confiança mínima:     {profile.confidence_threshold*100:.0f}%\n")

    if args.print_command:
        py_path = "C:/Users/hause/AppData/Local/Programs/Python/Python312/python.exe"
        dry = "--dry-run" if args.dry_run else ""
        cmd = (
            f"{py_path} scripts/mt5_cmd_bot.py run-engine-dynamic "
            f"--env-file brain.env "
            f"--symbols {args.symbols} "
            f"--timeframe M5 "
            f"--bars 400 "
            f"--interval-sec 10 "
            f"--volume {profile.default_volume} "
            f"--max-spread-points {profile.max_spread_points} "
            f"--min-atr-pct {profile.min_atr_pct} "
            f"--max-global-positions {profile.max_global_positions} "
            f"--max-positions-per-symbol {profile.max_positions_per_symbol} "
            f"--max-correlated-positions {profile.max_correlated_positions} "
            f"--sl-points {profile.default_sl_points} "
            f"--tp-points {profile.default_tp_points} "
            f"--close-opposite "
            f"--mode demo "
            f"--win-rate 0.56 "
            f"{dry}".strip()
        )
        print("Comando pronto para copiar/colar:")
        print(f"\n{cmd}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
