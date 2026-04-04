"""
Módulo de configuração de parâmetros.
"""

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
POSITION_SIZE = float(os.getenv("POSITION_SIZE", 1.0))
RISK_PERCENTAGE = float(os.getenv("RISK_PERCENTAGE", 0.01))
SYMBOL = os.getenv("SYMBOL", "BTCUSD")
START_DATE = os.getenv("START_DATE", "2020-01-01")
END_DATE = os.getenv("END_DATE", "2021-01-01")

# Parâmetros para DataFeed
CSV_PATH = os.getenv("CSV_PATH", "dados/BTCUSDT_1min.csv")
TIMEFRAME = os.getenv("TIMEFRAME", "1min")
DELAY = float(os.getenv("DELAY", 0.5))
