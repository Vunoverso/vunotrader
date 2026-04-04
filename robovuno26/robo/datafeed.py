"""
Módulo responsável pela coleta de dados de mercado.
"""

import pandas as pd
import numpy as np
import requests
from websocket import create_connection
from dotenv import load_dotenv
import os
import time
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://api.marketdata.example.com")

# TODO: Implementar funções de coleta de dados
def get_historical_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Retorna dados históricos para um ativo."""
    # Placeholder implementation
    url = f"{BASE_URL}/historical?symbol={symbol}&start={start}&end={end}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    # Transformar JSON em DataFrame
    df = pd.DataFrame(data)
    return df

class DataFeed:
    def __init__(self, csv_path: str, timeframe: str = '1min', delay: float = 0.5):
        """
        :param csv_path: Caminho para o arquivo CSV OHLCV
        :param timeframe: Timeframe dos dados (ex: '1min')
        :param delay: Delay entre atualizações para simular tempo real
        """
        self.csv_path = Path(csv_path)
        self.timeframe = timeframe
        self.delay = delay
        self.data = pd.read_csv(self.csv_path, parse_dates=['timestamp'])
        self.current_index = 0
        self.max_index = len(self.data)

    def get_latest(self):
        """Retorna o último candle disponível."""
        if self.current_index == 0:
            return None
        return self.data.iloc[self.current_index - 1]

    def get_last_n_bars(self, n: int):
        """Retorna os últimos n candles disponíveis."""
        if self.current_index == 0:
            return pd.DataFrame()
        return self.data.iloc[max(0, self.current_index - n):self.current_index]

    def stream(self):
        """
        Gera dados em tempo simulado, um por vez.
        Uso típico:
            for candle in feed.stream():
                process(candle)
        """
        while self.current_index < self.max_index:
            current_candle = self.data.iloc[self.current_index]
            yield current_candle
            self.current_index += 1
            time.sleep(self.delay)

    def reset(self):
        """Reinicia a simulação."""
        self.current_index = 0
