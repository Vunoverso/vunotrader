"""
Testes para backtest do robô.
"""

import pandas as pd
import pytest
from robo.strategy import generate_signals


def test_generate_signals():
    # Dados fictícios
    data = {
        'close': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                  9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    }
    df = pd.DataFrame(data)
    df = generate_signals(df)

    # Após pontos de cruzamento, sinais devem existir
    assert 'signal' in df.columns
    assert set(df['signal'].unique()).issubset({-1, 0, 1})
