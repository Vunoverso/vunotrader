import sys
import os
from datetime import datetime

# Ajusta path para importar do app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.price_action import VunoCandle, detect_pin_bar, detect_engulfing, get_sr_zones, check_market_structure, score_setup

def run_lab():
    print("="*60)
    print(" VUNO PRICE ACTION LAB - Analisador de Estrutura VPE")
    print("="*60)
    
    # Mock de candles para demonstração
    # [High, Low, Open, Close, Volume]
    raw_data = [
        [1925.5, 1920.0, 1921.0, 1924.5, 1000], # Bullish
        [1926.0, 1923.0, 1924.5, 1925.8, 1100], # Bullish
        [1928.0, 1925.0, 1925.8, 1927.5, 1200], # Bullish
        [1935.0, 1925.0, 1927.5, 1928.0, 1500], # PIN BAR BULLISH (Pavio longo inferior)
        [1930.0, 1928.0, 1928.0, 1929.5, 900],  # Recuo
        [1931.0, 1926.0, 1929.5, 1927.0, 2000], # ENGOLFO BEARISH (Cobre o anterior)
    ]
    
    candles = [VunoCandle(d[0], d[1], d[2], d[3], d[4]) for d in raw_data]
    atr = 2.5 # Mock ATR
    
    print(f"\n1. Analisando Estrutura de Mercado...")
    structure = check_market_structure(candles)
    print(f"   Resultado: {structure.upper()}")
    
    print(f"\n2. Mapeando Cloud Zones (Suporte/Resistência)...")
    zones = get_sr_zones(candles, atr)
    for z in zones:
        print(f"   - Zona de {z['type'].upper()} em {z['price']:.2f} (Toques: {z['touches']})")

    print(f"\n3. Verificando Padrões e Score VPE (Último Candle)...")
    curr = candles[-1]
    prev = candles[-2]
    
    score, factors = score_setup(curr, prev, zones, structure, atr)
    
    print(f"   Score Final: {score:.2f}")
    print(f"   Fatores Detectados: {', '.join(factors)}")
    
    if score >= 0.60:
        print("\n[VPE VERDICT] SINAL DE ALTA CONVICÇÃO DETECTADO.")
    else:
        print("\n[VPE VERDICT] Aguardando maior confluência.")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    run_lab()
