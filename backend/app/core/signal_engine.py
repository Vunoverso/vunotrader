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
from typing import List, Tuple

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


# ── Motor de decisão ────────────────────────────────────────────────────

class SignalResult:
    def __init__(
        self,
        signal: str,
        confidence: float,
        risk_pct: float,
        rationale: str,
        regime: str,
    ):
        self.signal     = signal        # "BUY" | "SELL" | "HOLD"
        self.confidence = confidence    # 0.0 – 1.0
        self.risk_pct   = risk_pct      # % do capital
        self.rationale  = rationale
        self.regime     = regime        # "tendencia" | "lateral" | "volatil"


def analyse(candles: list[Candle], risk_base: float = 2.0) -> SignalResult:
    """
    Processa lista de candles e retorna um SignalResult.
    Cada candle: [timestamp, open, high, low, close, volume]
    """
    if len(candles) < 60:
        return SignalResult("HOLD", 0.0, 0.0, "Histórico insuficiente (<60 candles)", "lateral")

    closes = [c[4] for c in candles]
    highs  = [c[2] for c in candles]
    lows   = [c[3] for c in candles]
    vols   = [c[5] for c in candles]

    # ── Indicadores ────────────────────────────────────────────────────
    rsi  = _rsi(closes)
    macd_val, macd_sig, macd_hist = _macd(closes)
    atr  = _atr(highs, lows, closes)
    bb_upper, bb_mid, bb_lower = _bollinger(closes)
    vol_ratio  = _volume_ratio(vols)
    mom10      = _momentum(closes, 10)
    mom20      = _momentum(closes, 20)

    ema9_arr  = _ema(closes, 9)
    ema21_arr = _ema(closes, 21)
    ema50_arr = _ema(closes, 50)

    ema9  = ema9_arr[-1]  if ema9_arr  else closes[-1]
    ema21 = ema21_arr[-1] if ema21_arr else closes[-1]
    ema50 = ema50_arr[-1] if ema50_arr else closes[-1]
    price = closes[-1]

    # ── Regime de mercado ───────────────────────────────────────────────
    atr_pct = atr / price if price > 0 else 0.0
    if atr_pct > 0.012:
        regime = "volatil"
    elif ema9 > ema21 > ema50 or ema9 < ema21 < ema50:
        regime = "tendencia"
    else:
        regime = "lateral"

    # ── Scores de sinal (–1 bearish … +1 bullish) ──────────────────────
    scores: list[float] = []

    # RSI
    if rsi < 30:
        scores.append(1.0)
    elif rsi > 70:
        scores.append(-1.0)
    elif rsi < 45:
        scores.append(0.4)
    elif rsi > 55:
        scores.append(-0.4)
    else:
        scores.append(0.0)

    # MACD crossover
    if macd_val > macd_sig and macd_hist > 0:
        scores.append(0.8 if macd_hist > 0.0001 else 0.3)
    elif macd_val < macd_sig and macd_hist < 0:
        scores.append(-0.8 if macd_hist < -0.0001 else -0.3)
    else:
        scores.append(0.0)

    # EMA crossover
    if ema9 > ema21 and ema21 > ema50:
        scores.append(0.9)
    elif ema9 < ema21 and ema21 < ema50:
        scores.append(-0.9)
    elif ema9 > ema21:
        scores.append(0.4)
    elif ema9 < ema21:
        scores.append(-0.4)
    else:
        scores.append(0.0)

    # Bollinger Bands
    bb_width = (bb_upper - bb_lower) / bb_mid if bb_mid != 0 else 0.0
    bb_pos   = (price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) != 0 else 0.5
    if bb_pos < 0.15:
        scores.append(0.7)
    elif bb_pos > 0.85:
        scores.append(-0.7)
    else:
        scores.append(0.0)

    # Momentum
    if mom10 > 0.5 and mom20 > 0.3:
        scores.append(0.6)
    elif mom10 < -0.5 and mom20 < -0.3:
        scores.append(-0.6)
    else:
        scores.append(mom10 / 2.0)

    # Volume confirma
    vol_mult = min(vol_ratio, 2.0)
    scores = [s * (0.7 + 0.3 * min(vol_mult, 1.5)) for s in scores]

    # ── Score final ─────────────────────────────────────────────────────
    weights = [0.20, 0.25, 0.25, 0.15, 0.15]
    raw_score = sum(s * w for s, w in zip(scores, weights))

    # Penaliza mercado volátil
    if regime == "volatil":
        raw_score *= 0.6

    # ── Limiar de decisão ───────────────────────────────────────────────
    THRESHOLD_STRONG = 0.45
    THRESHOLD_WEAK   = 0.28

    if raw_score >= THRESHOLD_STRONG:
        signal = "BUY"
        confidence = min(0.95, 0.62 + abs(raw_score) * 0.4)
    elif raw_score <= -THRESHOLD_STRONG:
        signal = "SELL"
        confidence = min(0.95, 0.62 + abs(raw_score) * 0.4)
    elif abs(raw_score) >= THRESHOLD_WEAK and regime == "tendencia":
        signal = "BUY" if raw_score > 0 else "SELL"
        confidence = 0.58 + abs(raw_score) * 0.2
    else:
        signal = "HOLD"
        confidence = 0.0

    # ── Risco dinâmico ──────────────────────────────────────────────────
    if signal == "HOLD":
        risk = 0.0
    else:
        risk = risk_base * confidence
        risk = max(0.5, min(4.0, risk))
        if regime == "volatil":
            risk *= 0.6

    # ── Racional legível ────────────────────────────────────────────────
    rsi_str    = f"RSI={rsi:.1f}"
    macd_str   = f"MACD={'acima' if macd_hist > 0 else 'abaixo'} do sinal"
    ema_str    = f"EMA9{'>' if ema9 > ema21 else '<'}EMA21{'>' if ema21 > ema50 else '<'}EMA50"
    regime_str = f"Regime={regime}"
    vol_str    = f"Vol={vol_ratio:.1f}x"
    bb_str     = f"BBpos={bb_pos:.2f}"
    bb_w_str   = f"BBwidth={bb_width:.4f}"

    rationale = f"{signal}|score={raw_score:.3f}|{rsi_str}|{macd_str}|{ema_str}|{regime_str}|{vol_str}|{bb_str}|{bb_w_str}"

    return SignalResult(
        signal=signal,
        confidence=round(confidence, 4),
        risk_pct=round(risk, 3),
        rationale=rationale,
        regime=regime,
    )
