"""
VunoTrader Cloud Signal Engine
Análise técnica pura (sem sklearn, sem .pkl) — roda direto no Render.

Indicadores calculados:
  RSI(14), MACD(12,26,9), EMA(9/21/50/200), ATR(14),
  Bollinger Bands(20), Momentum, Volume Ratio.

Decisão final: combinação ponderada dos indicadores + filtro de regime.
"""
from __future__ import annotations

import math
from typing import List, Tuple, Dict, Any, Optional
from app.core.price_action import (
    VunoCandle, 
    score_setup, 
    get_sr_zones, 
    check_market_structure,
    detect_pin_bar,
    detect_engulfing
)

# ── Tipos internos ──────────────────────────────────────────────────────
Candle = List[float]   # [timestamp, open, high, low, close, volume]
Closes = List[float]
Highs  = List[float]
Lows   = List[float]
Vols   = List[float]


# ── Indicadores ─────────────────────────────────────────────────────────

def _ema(values: Closes, period: int) -> List[float]:
    if len(values) < period:
        return []
    k = 2.0 / (period + 1)
    result = [sum(values[:period]) / period]
    for v in values[period:]:
        result.append(v * k + result[-1] * (1 - k))
    return result


def _rsi(closes: Closes, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains  = [max(d, 0.0) for d in deltas[-period:]]
    losses = [max(-d, 0.0) for d in deltas[-period:]]
    avg_g  = sum(gains) / period
    avg_l  = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100.0 - (100.0 / (1 + rs))


def _macd(closes: Closes) -> Tuple[float, float, float]:
    """Retorna (macd_line, signal_line, histogram)."""
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    if not ema12 or not ema26:
        return 0.0, 0.0, 0.0
    # Alinha pelo menor
    min_len = min(len(ema12), len(ema26))
    macd_line = [ema12[-min_len + i] - ema26[-min_len + i] for i in range(min_len)]
    signal_line = _ema(macd_line, 9)
    if not signal_line:
        return macd_line[-1], 0.0, macd_line[-1]
    hist = macd_line[-1] - signal_line[-1]
    return macd_line[-1], signal_line[-1], hist


def _atr(highs: Highs, lows: Lows, closes: Closes, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i - 1]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-period:]) / period


def _bollinger(closes: Closes, period: int = 20) -> Tuple[float, float, float]:
    """Retorna (upper, middle, lower)."""
    if len(closes) < period:
        mid = closes[-1]
        return mid, mid, mid
    window = closes[-period:]
    mid = sum(window) / period
    std = math.sqrt(sum((v - mid) ** 2 for v in window) / period)
    return mid + 2 * std, mid, mid - 2 * std


def _volume_ratio(vols: Vols, period: int = 20) -> float:
    if len(vols) < period + 1:
        return 1.0
    avg = sum(vols[-period - 1:-1]) / period
    if avg == 0:
        return 1.0
    return vols[-1] / avg


def _momentum(closes: Closes, period: int = 10) -> float:
    if len(closes) < period + 1:
        return 0.0
    base = closes[-(period + 1)]
    if base == 0:
        return 0.0
    return (closes[-1] - base) / base * 100.0


def _adx(highs: Highs, lows: Lows, closes: Closes, period: int = 14) -> float:
    """Average Directional Index (Wilder). Retorna força da tendência (0-100)."""
    if len(closes) < period * 2:
        return 20.0
    
    tr, pdm, ndm = [], [], []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i-1]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
        
        move_up = h - highs[i-1]
        move_down = lows[i-1] - l
        
        if move_up > move_down and move_up > 0:
            pdm.append(move_up)
            ndm.append(0)
        elif move_down > move_up and move_down > 0:
            pdm.append(0)
            ndm.append(move_down)
        else:
            pdm.append(0)
            ndm.append(0)
            
    # Wilder's Smoothing
    def smooth(data, p):
        s = [sum(data[:p])]
        for v in data[p:]:
            s.append(s[-1] - (s[-1] / p) + v)
        return s

    str_s = smooth(tr, period)
    spdm_s = smooth(pdm, period)
    sndm_s = smooth(ndm, period)
    
    dx = []
    for i in range(len(str_s)):
        if str_s[i] == 0:
            dx.append(0)
            continue
        pdi = 100 * spdm_s[i] / str_s[i]
        ndi = 100 * sndm_s[i] / str_s[i]
        div = pdi + ndi
        dx.append(100 * abs(pdi - ndi) / div if div != 0 else 0)
        
    return sum(dx[-period:]) / period if dx else 20.0


def _stochastic(highs: Highs, lows: Lows, closes: Closes, k_period: int = 14, d_period: int = 3) -> Tuple[float, float]:
    """Estocástico (%K, %D)."""
    if len(closes) < k_period + d_period:
        return 50.0, 50.0
    
    k_vals = []
    for i in range(len(closes) - k_period + 1):
        window_high = max(highs[i : i + k_period])
        window_low = min(lows[i : i + k_period])
        diff = window_high - window_low
        if diff == 0:
            k_vals.append(50.0)
        else:
            k_vals.append(100 * (closes[i + k_period - 1] - window_low) / diff)
            
    pk = k_vals[-1]
    pd = sum(k_vals[-d_period:]) / d_period
    return pk, pd


# ── Motor de decisão ────────────────────────────────────────────────────

class SignalResult:
    def __init__(
        self,
        signal: str,
        confidence: float,
        risk_pct: float,
        rationale: str,
        regime: str,
        price: float = 0.0,
        sl: float = 0.0,
        tp: float = 0.0,
        score: float = 0.0,
        atr_pct: float = 0.0,
        volume_ratio: float = 0.0,
        rsi: float = 50.0,
        momentum_20: float = 0.0,
    ):
        self.signal     = signal        # "BUY" | "SELL" | "HOLD"
        self.confidence = confidence    # 0.0 – 1.0
        self.risk_pct   = risk_pct      # % do capital
        self.rationale  = rationale
        self.regime     = regime        # "tendencia" | "lateral" | "volatil"
        self.price      = price
        self.sl         = sl
        self.tp         = tp
        self.score      = score
        self.atr_pct    = atr_pct
        self.volume_ratio = volume_ratio
        self.rsi        = rsi
        self.momentum_20 = momentum_20


def analyse(
    candles: list[Candle], 
    risk_base: float = 2.0,
    sl_mode: str = "atr",
    sl_value: float = 2.0,
    tp_rr: float = 2.0
) -> SignalResult:
    """
    Processa lista de candles e retorna um SignalResult.
    Meta: 68% de assertividade equilibrada com frequência.
    """
    if len(candles) < 60:
        return SignalResult("HOLD", 0.0, 0.0, "Histórico insuficiente (<60 candles)", "lateral")

    closes = [c[4] for c in candles]
    highs  = [c[2] for c in candles]
    lows   = [c[3] for c in candles]
    vols   = [c[5] for c in candles]

    # ── Indicadores Base ───────────────────────────────────────────────
    rsi  = _rsi(closes)
    macd_val, macd_sig, macd_hist = _macd(closes)
    atr  = _atr(highs, lows, closes)
    bb_upper, bb_mid, bb_lower = _bollinger(closes)
    vol_ratio  = _volume_ratio(vols)
    mom10      = _momentum(closes, 10)
    mom20      = _momentum(closes, 20)
    
    # ── Novos Indicadores de Inteligência ──────────────────────────────
    adx      = _adx(highs, lows, closes)
    stoch_k, stoch_d = _stochastic(highs, lows, closes)

    ema9_arr  = _ema(closes, 9)
    ema21_arr = _ema(closes, 21)
    ema50_arr = _ema(closes, 50)

    ema9  = ema9_arr[-1]  if ema9_arr  else closes[-1]
    ema21 = ema21_arr[-1] if ema21_arr else closes[-1]
    ema50 = ema50_arr[-1] if ema50_arr else closes[-1]
    price = closes[-1]

    # ── Regime de mercado Dinâmico ──────────────────────────────────────
    # ADX > 25 indica tendência forte. ADX < 18 indica lateralização.
    atr_pct = atr / price if price > 0 else 0.0
    
    if atr_pct > 0.015:
        regime = "volatil"
    elif adx > 25:
        regime = "tendencia"
    elif adx < 15: # Estrechamos a lateral para evitar flip-flop
        regime = "lateral"
    else:
        # Padrão anterior se ADX estiver em zona cinzenta
        if (ema9 > ema21 > ema50) or (ema9 < ema21 < ema50):
            regime = "tendencia"
        else:
            regime = "lateral"

    # ── Scores de sinal (–1 bearish … +1 bullish) ──────────────────────
    scores_map = {}

    # 1. RSI (Peso Variável)
    if rsi < 30: scores_map['rsi'] = 1.0
    elif rsi > 70: scores_map['rsi'] = -1.0
    elif rsi < 40: scores_map['rsi'] = 0.5
    elif rsi > 60: scores_map['rsi'] = -0.5
    else: scores_map['rsi'] = 0.0

    # 2. MACD (Seguidor de Tendência)
    if macd_val > macd_sig and macd_hist > 0:
        scores_map['macd'] = 0.8 if macd_hist > 0.0001 else 0.4
    elif macd_val < macd_sig and macd_hist < 0:
        scores_map['macd'] = -0.8 if macd_hist < -0.0001 else -0.4
    else:
        scores_map['macd'] = 0.0

    # 3. EMA (Cruzamento e Alinhamento)
    if ema9 > ema21 and ema21 > ema50: scores_map['ema'] = 0.9
    elif ema9 < ema21 and ema21 < ema50: scores_map['ema'] = -0.9
    elif ema9 > ema21: scores_map['ema'] = 0.5
    elif ema9 < ema21: scores_map['ema'] = -0.5
    else: scores_map['ema'] = 0.0

    # 4. Bollinger
    bb_pos = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) != 0 else 0.5
    if bb_pos < 0.15: scores_map['bb'] = 0.7
    elif bb_pos > 0.85: scores_map['bb'] = -0.7
    else: scores_map['bb'] = 0.0

    # 5. Stochastic (Novo filtro de reversão)
    if stoch_k < 20 and stoch_k > stoch_d: scores_map['stoch'] = 0.8  # Cruzou pra cima no fundo
    elif stoch_k > 80 and stoch_k < stoch_d: scores_map['stoch'] = -0.8 # Cruzou pra baixo no topo
    elif stoch_k < 25: scores_map['stoch'] = 0.4
    elif stoch_k > 75: scores_map['stoch'] = -0.4
    else: scores_map['stoch'] = 0.0

    # ── Ajuste de Pesos por Regime ──────────────────────────────────────
    # Se Tendência: MACD e EMA valem mais.
    # Se Lateral: RSI, BB e Estocástico valem mais.
    if regime == "tendencia":
        w = {"macd": 0.35, "ema": 0.35, "rsi": 0.10, "bb": 0.10, "stoch": 0.10}
    elif regime == "lateral":
        w = {"rsi": 0.30, "stoch": 0.30, "bb": 0.20, "macd": 0.10, "ema": 0.10}
    else: # Volátil
        w = {"macd": 0.20, "ema": 0.20, "rsi": 0.20, "bb": 0.20, "stoch": 0.20}

    raw_score = sum(scores_map[k] * w[k] for k in w)

    # Volume confirma
    vol_mult = min(vol_ratio, 2.0)
    raw_score *= (0.8 + 0.2 * min(vol_mult, 1.5))

    # Penaliza mercado excessivamente volátil
    if regime == "volatil":
        raw_score *= 0.7

    # ── Limiar de decisão (Equilibrado para evitar inatividade) ──────────
    # Conservador p/ 68%, mas flexível em tendências claras.
    THRESHOLD_ENTRY = 0.38
    
    if raw_score >= THRESHOLD_ENTRY:
        signal = "BUY"
    elif raw_score <= -THRESHOLD_ENTRY:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Confiança baseada na força do sinal
    confidence = abs(raw_score) * 1.5
    confidence = max(0.4, min(0.95, confidence))
    
    if signal == "HOLD":
        confidence = 0.0
        risk = 0.0
    else:
        # Risco base ponderado pela confiança
        risk = risk_base * confidence
        risk = max(0.5, min(3.5, risk))
        if regime == "volatil": risk *= 0.5

    # ── [VPE] Análise de Price Action (Estrutura e Zonas) ───────────────
    vuno_candles = [VunoCandle(c[2], c[3], c[1], c[4], c[5]) for c in candles]
    v_curr = vuno_candles[-1]
    v_prev = vuno_candles[-2] if len(vuno_candles) >= 2 else None
    
    # Detecção de Zonas e Estrutura VPE
    vpe_zones = get_sr_zones(vuno_candles, atr)
    vpe_struct = check_market_structure(vuno_candles)
    vpe_score, vpe_factors = score_setup(v_curr, v_prev, vpe_zones, vpe_struct, atr)

    # ── Racional em Português (Inteligente - VPE) ──────────────────────
    reasons = []
    if signal != "HOLD":
        if vpe_struct == "bullish" and signal == "BUY": reasons.append("tendência de alta confirmada (H1/H4)")
        if vpe_struct == "bearish" and signal == "SELL": reasons.append("tendência de baixa confirmada (H1/H4)")
        
        # Confluências VPE
        for f in vpe_factors:
            if "PIN_BAR" in f: reasons.append("rejeição institucional (Pin Bar)")
            if "ENGULFING" in f: reasons.append("força de momentum (Engolfo)")
            if "ZONE" in f: reasons.append("em zona de suporte/resistência relevante")
            if "INSIDE_BAR" in f: reasons.append("compressão para rompimento")
            
        if vol_ratio > 1.4: reasons.append("fluxo de volume acima da média")
    else:
        if vpe_score > 0.4:
            reasons.append(f"setup em formação ({vpe_score:.2f}), aguardando confirmação {vpe_struct}")
        elif adx < 15:
            reasons.append("mercado parado (ADX baixo), evitando ruído")
        else:
            reasons.append("ausência de confluência Price Action")

    friendly_text = " e ".join(reasons[:2]).capitalize() + "." if reasons else "Aguardando sinal claro."
    
    # ── Racional final (VPE + tech info) ──────────────────────────────
    vpe_factors_str = ",".join(vpe_factors)
    tech_info = f"score={raw_score:.2f}|vpe={vpe_score:.2f}|ADX={adx:.0f}|{vpe_struct}|factors={vpe_factors_str}"
    rationale = f"[{vpe_struct.upper()}] {friendly_text} | tech:{tech_info}"


    # ── Cálculo de SL e TP (Configurável via DB) ──────────────────────
    sl, tp = 0.0, 0.0
    if signal != "HOLD":
        # ── STOP LOSS ──
        if sl_mode == "fixed_points":
            sl_dist = sl_value
        else: # atr
            sl_dist = atr * sl_value
            
        if signal == "BUY":
            sl = price - sl_dist
            # Proteção VPE: Se houver zona suporte próxima, ajusta o SL abaixo dela
            for z in vpe_zones:
                if z["type"] == "support" and z["bottom"] < price and z["bottom"] > (price - sl_dist * 1.2):
                    sl = min(sl, z["bottom"] - (atr * 0.2)) # SL folgado abaixo da zona
                    break
            tp = price + (sl_dist * tp_rr)
        elif signal == "SELL":
            sl = price + sl_dist
            # Proteção VPE: Se houver zona resistência próxima, ajusta o SL acima dela
            for z in vpe_zones:
                if z["type"] == "resistance" and z["top"] > price and z["top"] < (price + sl_dist * 1.2):
                    sl = max(sl, z["top"] + (atr * 0.2)) # SL folgado acima da zona
                    break
            tp = price - (sl_dist * tp_rr)

    return SignalResult(
        signal=signal,
        confidence=round(confidence, 4),
        risk_pct=round(risk, 3),
        rationale=rationale,
        regime=regime,
        price=price,
        sl=round(sl, 5),
        tp=round(tp, 5),
        score=round(raw_score, 4),
        atr_pct=round(atr_pct, 6),
        volume_ratio=round(vol_ratio, 4),
        rsi=round(rsi, 2),
        momentum_20=round(mom20, 4),
    )


def check_smart_exit(
    candles: list[Candle], 
    side: str, 
    entry_price: float, 
    sl: float, 
    tp: float
) -> Tuple[bool, str]:
    """
    Verifica se a operação atual deve ser encerrada antecipadamente (Smart Exit).
    Retorna (should_exit, reason)
    """
    if len(candles) < 20: return False, ""

    closes = [c[4] for c in candles]
    highs  = [c[2] for c in candles]
    lows   = [c[3] for c in candles]
    price  = closes[-1]
    atr    = _atr(highs, lows, closes)
    
    # ── VPE Price Action ────────────────────────────────────────────────
    v_candles = [VunoCandle(c[2], c[3], c[1], c[4], c[5]) for c in candles]
    v_curr = v_candles[-1]
    v_prev = v_candles[-2]
    zones = get_sr_zones(v_candles, atr)
    struct = check_market_structure(v_candles)

    # 1. Reversão por Price Action (Candle de Força oposto em zona S/R)
    if side == "buy":
        is_pin, _, p_type = detect_pin_bar(v_curr)
        is_eng, _, e_type = detect_engulfing(v_prev, v_curr)
        
        # Se COMPRA e sinal de VENDA (Engolfo/Pin Bar) em resistência
        if (is_pin and p_type == "bearish") or (is_eng and e_type == "bearish"):
            for z in zones:
                if z["type"] == "resistance" and z["bottom"] <= v_curr.high <= z["top"]:
                    return True, "Reversão detectada em zona de resistência (VPE)"
        
        # Se a tendência do preço cruzar a EMA50 para baixo
        if struct == "bearish":
            return True, "Estrutura de mercado mudou para Baixa (VPE)"

    elif side == "sell":
        is_pin, _, p_type = detect_pin_bar(v_curr)
        is_eng, _, e_type = detect_engulfing(v_prev, v_curr)
        
        # Se VENDA e sinal de COMPRA em suporte
        if (is_pin and p_type == "bullish") or (is_eng and e_type == "bullish"):
            for z in zones:
                if z["type"] == "support" and z["bottom"] <= v_curr.low <= z["top"]:
                    return True, "Reversão detectada em zona de suporte (VPE)"
                    
        if struct == "bullish":
            return True, "Estrutura de mercado mudou para Alta (VPE)"

    return False, ""
