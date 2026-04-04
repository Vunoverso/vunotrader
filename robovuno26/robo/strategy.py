"""
Módulo de estratégia e geração de sinais.
"""

import numpy as np
import pandas as pd

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Gera sinais de compra e venda baseado em médias móveis."""
    df["signal"] = 0
    df["ma_short"] = df["close"].rolling(window=10).mean()
    df["ma_long"] = df["close"].rolling(window=50).mean()
    df.loc[df["ma_short"] > df["ma_long"], "signal"] = 1  # Compra
    df.loc[df["ma_short"] < df["ma_long"], "signal"] = -1  # Venda
    return df

def sinal_score(df: pd.DataFrame, short_window: int = 10, long_window: int = 50) -> float:
    """Calcula pontuação de sinal baseado na diferença entre médias móveis."""
    if df.empty or len(df) < long_window:
        return 0.0
    ma_short = df['close'].rolling(window=short_window).mean().iloc[-1]
    ma_long = df['close'].rolling(window=long_window).mean().iloc[-1]
    return ma_short - ma_long
