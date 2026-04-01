import math
from typing import List, Tuple, Dict, Optional

# Constantes Vuno Price Action Engine (VPE)
PIN_BAR_RATIO_MIN = 2.5
PIN_BAR_RATIO_IDEAL = 3.5
ENGULFING_RATIO_MIN = 1.0
ENGULFING_RATIO_IDEAL = 1.5
SR_ZONE_ATR_MULTIPLIER = 0.2

class VunoCandle:
    def __init__(self, high: float, low: float, open: float, close: float, volume: float):
        self.high = high
        self.low = low
        self.open = open
        self.close = close
        self.volume = volume
        self.body_size = abs(close - open)
        self.total_range = high - low if high != low else 0.00000001
        self.is_bullish = close >= open
        self.is_bearish = open > close
        
        # Shadows
        self.upper_shadow = high - max(open, close)
        self.lower_shadow = min(open, close) - low

def detect_pin_bar(c: VunoCandle) -> Tuple[bool, float, str]:
    """
    Regra VPE: shadow >= 2.5 * body.
    Retorna (is_pin, score, type)
    """
    if c.body_size == 0:
        # Doji com pavio longo pode ser pin bar
        ratio = c.total_range / 0.00000001 
    else:
        # VPE usa o maior pavio para o ratio
        max_shadow = max(c.upper_shadow, c.lower_shadow)
        ratio = max_shadow / c.body_size

    if ratio < PIN_BAR_RATIO_MIN:
        return False, 0.0, ""

    # Determina se é bullish (pavio inferior) ou bearish (pavio superior)
    is_bullish = c.lower_shadow > c.upper_shadow
    
    # Validação de posição do fechamento (deve estar no terço oposto)
    if is_bullish and c.close < (c.low + c.total_range * 0.4): return False, 0.0, ""
    if not is_bullish and c.close > (c.high - c.total_range * 0.4): return False, 0.0, ""

    # Score baseado no ratio ideal (3.5)
    score = min(1.0, ratio / PIN_BAR_RATIO_IDEAL)
    return True, score, "bullish" if is_bullish else "bearish"

def detect_engulfing(prev: VunoCandle, curr: VunoCandle) -> Tuple[bool, float, str]:
    """
    Regra VPE: Corpo2 supera corpo1 em direção oposta.
    Ratio ideal >= 1.5
    """
    if prev.is_bullish == curr.is_bullish:
        return False, 0.0, ""
    
    # Validação de engulfing real (corpo cobre o corpo anterior)
    is_bull_engulf = curr.close > prev.open and curr.open < prev.close and curr.is_bullish
    is_bear_engulf = curr.close < prev.open and curr.open > prev.close and curr.is_bearish
    
    if not (is_bull_engulf or is_bear_engulf):
        return False, 0.0, ""
        
    body_ratio = curr.body_size / (prev.body_size if prev.body_size > 0 else 0.00000001)
    if body_ratio < ENGULFING_RATIO_MIN:
        return False, 0.0, ""
        
    score = min(1.0, body_ratio / ENGULFING_RATIO_IDEAL)
    return True, score, "bullish" if is_bull_engulf else "bearish"

def get_sr_zones(candles: List[VunoCandle], atr: float, n_back: int = 100) -> List[Dict]:
    """
    Detecta zonas S/R (Cloud Zones) usando picos e vales.
    Frequência (touches) aumenta o peso da zona.
    """
    if len(candles) < 20: return []
    
    relevant = candles[-n_back:]
    peaks = []
    troughs = []
    
    # Identificação simples de Swing Highs/Lows
    for i in range(2, len(relevant)-2):
        # Swing High
        if relevant[i].high > relevant[i-1].high and relevant[i].high > relevant[i+1].high:
            peaks.append(relevant[i].high)
        # Swing Low
        if relevant[i].low < relevant[i-1].low and relevant[i].low < relevant[i+1].low:
            troughs.append(relevant[i].low)
            
    zones = []
    thickness = atr * SR_ZONE_ATR_MULTIPLIER
    
    # Agrupar níveis próximos em zonas (clumping)
    def cluster_levels(levels, is_resistance):
        if not levels: return
        levels.sort()
        current_cluster = [levels[0]]
        for l in levels[1:]:
            if l - current_cluster[-1] < thickness * 2:
                current_cluster.append(l)
            else:
                avg = sum(current_cluster) / len(current_cluster)
                zones.append({
                    "type": "resistance" if is_resistance else "support",
                    "price": avg,
                    "top": avg + thickness,
                    "bottom": avg - thickness,
                    "touches": len(current_cluster)
                })
                current_cluster = [l]
        # Last one
        avg = sum(current_cluster) / len(current_cluster)
        zones.append({
            "type": "resistance" if is_resistance else "support",
            "price": avg,
            "top": avg + thickness,
            "bottom": avg - thickness,
            "touches": len(current_cluster)
        })

    cluster_levels(peaks, True)
    cluster_levels(troughs, False)
    
    return [z for z in zones if z["touches"] >= 2] # Filtro de relevância mínimo

def detect_inside_bar(prev: VunoCandle, curr: VunoCandle) -> Tuple[bool, float]:
    """Regra VPE: IB.high < MB.high e IB.low > MB.low (Compressão)."""
    if curr.high < prev.high and curr.low > prev.low:
        return True, 0.6
    return False, 0.0

def check_market_structure(candles: List[VunoCandle]) -> str:
    """
    Identifica Tendência HH/HL ou LH/LL.
    Retorna: 'bullish', 'bearish' ou 'lateral'
    """
    if len(candles) < 20: return "lateral"
    
    closes = [c.close for c in candles[-20:]]
    ema20 = sum(closes) / 20
    ema50 = sum([c.close for c in candles[-50:]]) / 50 if len(candles) >= 50 else ema20
    
    if ema20 > ema50 and candles[-1].close > ema20:
        return "bullish"
    elif ema20 < ema50 and candles[-1].close < ema20:
        return "bearish"
    return "lateral"

def score_setup(
    candle: VunoCandle, 
    prev_candle: Optional[VunoCandle],
    zones: List[Dict], 
    structure: str,
    atr_val: float
) -> Tuple[float, List[str]]:
    """
    O Coração do VPE. Calcula confluência (0.0 - 1.0).
    """
    total_score = 0.0
    factors = []
    
    # 1. Padrão de Candle (25%)
    is_pin, pin_score, pin_type = detect_pin_bar(candle)
    if is_pin:
        total_score += 0.25 * pin_score
        factors.append(f"PIN_BAR_{pin_type.upper()}")
        
    if prev_candle:
        is_eng, eng_score, eng_type = detect_engulfing(prev_candle, candle)
        if is_eng:
            total_score += 0.25 * eng_score
            factors.append(f"ENGULFING_{eng_type.upper()}")
            
        is_ib, ib_score = detect_inside_bar(prev_candle, candle)
        if is_ib:
            total_score += 0.15 * ib_score
            factors.append("INSIDE_BAR")

    # 2. Zona S/R (Cloud Zone) (25%)
    in_zone = False
    for z in zones:
        if z["bottom"] <= candle.low <= z["top"] or z["bottom"] <= candle.high <= z["top"]:
            zone_weight = min(1.0, z["touches"] / 3.0)
            total_score += 0.25 * zone_weight
            factors.append(f"ZONE_{z['type'].upper()}")
            in_zone = True
            break
            
    # 3. Estrutura (20%)
    if structure != "lateral":
        total_score += 0.20
        factors.append(f"STRUCTURE_{structure.upper()}")
        
    # Bônus: Confluência Técnica (Sinal batendo com Estrutura)
    if is_pin and pin_type == structure: total_score += 0.10
    if prev_candle and is_eng and eng_type == structure: total_score += 0.10

    # Bônus: Volume (> 1.2x média anterior)
    # (Poderia ser passado via parâmetro, simplificado aqui)
    
    return min(1.0, total_score), factors
