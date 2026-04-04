"""
Script principal para execução do robô.
"""

import pandas as pd
from robo.datafeed import DataFeed
from robo.strategy import sinal_score
from robo.executor import execute_order
from robo.risk import calculate_risk
from robo.logger import log_info, log_error
from robo.config import *


def main():
    try:
        # Configura DataFeed para streaming em tempo real
        feed = DataFeed(CSV_PATH, TIMEFRAME, DELAY)

        # Loop de dados simulados
        for candle in feed.stream():
            history = feed.get_last_n_bars(50)
            score = sinal_score(history)
            if score > 0:
                signal = 1
            elif score < 0:
                signal = -1
            else:
                signal = 0
            price = candle['close']
            position_value = price * POSITION_SIZE
            risk = calculate_risk(position_value, RISK_PERCENTAGE)

            if signal != 0:
                success = execute_order(signal, SYMBOL, POSITION_SIZE)
                if success:
                    log_info(f"Ordem executada: {signal} {SYMBOL} a {price}")
                else:
                    log_error("Falha na execução da ordem")

    except Exception as e:
        log_error(str(e))


if __name__ == "__main__":
    main()
