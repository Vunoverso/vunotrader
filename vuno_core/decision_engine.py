from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler


log = logging.getLogger("VunoDecisionEngine")

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_RF = ROOT_DIR / "brain_model_rf.pkl"
DEFAULT_MODEL_GB = ROOT_DIR / "brain_model_gb.pkl"
DEFAULT_MODEL_SCALER = ROOT_DIR / "brain_model_scaler.pkl"


@dataclass(slots=True)
class DecisionRuntimeConfig:
    min_confidence: float = 0.62
    risk_base: float = 2.0
    risk_max: float = 4.0
    risk_min: float = 0.5


class FeatureBuilder:
    """Constrói features técnicas a partir de dados OHLCV."""

    @staticmethod
    def build(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()

        for period in [5, 9, 21, 50, 200]:
            d[f"ema_{period}"] = d["close"].ewm(span=period).mean()

        delta = d["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        d["rsi"] = 100 - (100 / (1 + rs))

        ema12 = d["close"].ewm(span=12).mean()
        ema26 = d["close"].ewm(span=26).mean()
        d["macd"] = ema12 - ema26
        d["macd_signal"] = d["macd"].ewm(span=9).mean()
        d["macd_hist"] = d["macd"] - d["macd_signal"]

        ma20 = d["close"].rolling(20).mean()
        std20 = d["close"].rolling(20).std()
        d["bb_upper"] = ma20 + (2 * std20)
        d["bb_lower"] = ma20 - (2 * std20)
        d["bb_width"] = (d["bb_upper"] - d["bb_lower"]) / ma20
        d["bb_pos"] = (d["close"] - d["bb_lower"]) / (d["bb_upper"] - d["bb_lower"] + 1e-10)

        high_low = d["high"] - d["low"]
        high_close = (d["high"] - d["close"].shift()).abs()
        low_close = (d["low"] - d["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        d["atr"] = tr.rolling(14).mean()
        d["atr_pct"] = d["atr"] / d["close"]

        d["momentum_5"] = d["close"].pct_change(5)
        d["momentum_10"] = d["close"].pct_change(10)
        d["momentum_20"] = d["close"].pct_change(20)

        if "volume" in d.columns:
            d["volume_ratio"] = d["volume"] / d["volume"].rolling(20).mean()
        else:
            d["volume_ratio"] = 1.0

        d["cross_9_21"] = np.sign(d["ema_9"] - d["ema_21"])
        d["cross_21_50"] = np.sign(d["ema_21"] - d["ema_50"])
        d["cross_50_200"] = np.sign(d["ema_50"] - d["ema_200"])

        d["dist_ema9"] = (d["close"] - d["ema_9"]) / d["close"]
        d["dist_ema21"] = (d["close"] - d["ema_21"]) / d["close"]
        d["dist_ema50"] = (d["close"] - d["ema_50"]) / d["close"]

        return d.dropna()

    @staticmethod
    def get_feature_cols() -> list[str]:
        return [
            "rsi", "macd", "macd_signal", "macd_hist",
            "bb_width", "bb_pos", "atr_pct",
            "momentum_5", "momentum_10", "momentum_20",
            "volume_ratio",
            "cross_9_21", "cross_21_50", "cross_50_200",
            "dist_ema9", "dist_ema21", "dist_ema50",
        ]

    @staticmethod
    def detect_regime(features_row: pd.Series) -> str:
        atr_pct = float(features_row.get("atr_pct", 0))
        bb_width = float(features_row.get("bb_width", 0))
        cross_9 = float(features_row.get("cross_9_21", 0))
        cross_21 = float(features_row.get("cross_21_50", 0))
        cross_50 = float(features_row.get("cross_50_200", 0))
        dist_50 = abs(float(features_row.get("dist_ema50", 0)))
        mom_20 = abs(float(features_row.get("momentum_20", 0)))

        aligned_up = cross_9 > 0 and cross_21 > 0 and cross_50 > 0
        aligned_down = cross_9 < 0 and cross_21 < 0 and cross_50 < 0
        is_trending = (aligned_up or aligned_down) and dist_50 > 0.008 and mom_20 > 0.01
        is_volatile = atr_pct > 0.015 or bb_width > 0.06

        if is_volatile:
            return "volatil"
        if is_trending:
            return "tendencia"
        return "lateral"


class TradingModel:
    """Ensemble RF + GB reutilizável pelo brain e por conectores locais."""

    def __init__(self, runtime: DecisionRuntimeConfig):
        self.runtime = runtime
        self.rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=20,
            random_state=42,
            n_jobs=-1,
        )
        self.gb = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=42,
        )
        self.scaler = StandardScaler()
        self.trained = False
        self.accuracy = 0.0
        self.feature_importance: dict[str, float] = {}

    def prepare_labels(self, df: pd.DataFrame, forward_bars: int = 5) -> pd.Series:
        future_return = df["close"].shift(-forward_bars) / df["close"] - 1
        threshold = df["atr_pct"].mean() * 0.5
        return (future_return > threshold).astype(int)

    def train(self, df: pd.DataFrame) -> bool:
        try:
            features = FeatureBuilder.build(df)
            feat_cols = FeatureBuilder.get_feature_cols()
            labels = self.prepare_labels(features)

            valid_idx = features.index.intersection(labels.dropna().index)
            X = features.loc[valid_idx, feat_cols]
            y = labels.loc[valid_idx]

            if len(X) < 100:
                log.warning("Dados insuficientes para treino (< 100 amostras)")
                return False

            X_scaled = self.scaler.fit_transform(X)

            cv_rf = cross_val_score(self.rf, X_scaled, y, cv=5, scoring="accuracy")
            cv_gb = cross_val_score(self.gb, X_scaled, y, cv=5, scoring="accuracy")

            self.accuracy = max(cv_rf.mean(), cv_gb.mean())
            log.info("CV Accuracy — RF: %.3f | GB: %.3f", cv_rf.mean(), cv_gb.mean())

            self.rf.fit(X_scaled, y)
            self.gb.fit(X_scaled, y)

            self.feature_importance = dict(zip(feat_cols, self.rf.feature_importances_))
            self.trained = True
            log.info("Modelo treinado | Accuracy: %.3f | Amostras: %s", self.accuracy, len(X))
            return True
        except Exception as exc:
            log.error("Erro no treino: %s", exc)
            return False

    def predict(self, features_row: pd.DataFrame) -> dict:
        if not self.trained:
            return {"signal": "HOLD", "confidence": 0.0, "risk": 0.0}

        try:
            feat_cols = FeatureBuilder.get_feature_cols()
            X = features_row[feat_cols]
            X_scaled = self.scaler.transform(X)

            prob_rf = self.rf.predict_proba(X_scaled)[0]
            prob_gb = self.gb.predict_proba(X_scaled)[0]
            prob = (prob_rf + prob_gb) / 2

            confidence_buy = prob[1]
            confidence_sell = prob[0]
            confidence = max(confidence_buy, confidence_sell)
            signal = "BUY" if confidence_buy > confidence_sell else "SELL"

            if confidence < self.runtime.min_confidence:
                signal = "HOLD"

            risk = self._calculate_dynamic_risk(confidence)
            rationale = self._generate_rationale(signal, confidence, features_row)

            return {
                "signal": signal,
                "confidence": round(float(confidence), 4),
                "risk": round(risk, 2),
                "prob_buy": round(float(confidence_buy), 4),
                "prob_sell": round(float(confidence_sell), 4),
                "rationale": rationale,
            }
        except Exception as exc:
            log.error("Erro na predição: %s", exc)
            return {"signal": "HOLD", "confidence": 0.0, "risk": 0.0}

    def _generate_rationale(self, signal: str, confidence: float, row: pd.DataFrame) -> str:
        try:
            feat = row.iloc[0] if hasattr(row, "iloc") else row

            rsi = float(feat.get("rsi", 50))
            macd_hist = float(feat.get("macd_hist", 0))
            bb_pos = float(feat.get("bb_pos", 0.5))
            atr_pct = float(feat.get("atr_pct", 0))
            mom_5 = float(feat.get("momentum_5", 0))
            vol_ratio = float(feat.get("volume_ratio", 1))
            cross_9 = float(feat.get("cross_9_21", 0))

            clues: list[str] = []

            if rsi >= 70:
                clues.append(f"RSI sobrecomprado ({rsi:.1f})")
            elif rsi <= 30:
                clues.append(f"RSI sobrevendido ({rsi:.1f})")
            else:
                clues.append(f"RSI neutro ({rsi:.1f})")

            if macd_hist > 0:
                clues.append("MACD histograma positivo (momentum de alta)")
            elif macd_hist < 0:
                clues.append("MACD histograma negativo (momentum de baixa)")

            if bb_pos > 0.85:
                clues.append("preço próximo da banda superior (Bollinger)")
            elif bb_pos < 0.15:
                clues.append("preço próximo da banda inferior (Bollinger)")

            if atr_pct > 0.015:
                clues.append(f"volatilidade elevada (ATR {atr_pct*100:.2f}%)")
            elif atr_pct < 0.004:
                clues.append(f"volatilidade comprimida (ATR {atr_pct*100:.2f}%)")

            if abs(mom_5) > 0.005:
                dir_str = "alta" if mom_5 > 0 else "baixa"
                clues.append(f"momentum de {dir_str} nos últimos 5 candles ({mom_5*100:.2f}%)")

            if vol_ratio > 1.5:
                clues.append(f"volume acima da média ({vol_ratio:.1f}x)")
            elif vol_ratio < 0.6:
                clues.append("volume abaixo da média")

            if cross_9 > 0:
                clues.append("EMA9 acima da EMA21 (tendência de curto prazo: alta)")
            elif cross_9 < 0:
                clues.append("EMA9 abaixo da EMA21 (tendência de curto prazo: baixa)")

            if confidence >= 0.80:
                conviction = "alta convicção"
            elif confidence >= 0.72:
                conviction = "convicção moderada"
            else:
                conviction = "baixa convicção"

            signal_str = {"BUY": "COMPRA", "SELL": "VENDA", "HOLD": "AGUARDAR"}.get(signal, signal)
            if not clues:
                return f"Sinal {signal_str} ({conviction}, confiança {confidence*100:.1f}%)"

            context = " | ".join(clues[:4])
            return f"{signal_str} ({conviction}, {confidence*100:.1f}%): {context}"
        except Exception:
            return f"Sinal {signal} com confiança {confidence*100:.1f}%"

    def _calculate_dynamic_risk(self, confidence: float) -> float:
        if confidence >= 0.80:
            return self.runtime.risk_max
        if confidence >= 0.72:
            return self.runtime.risk_base
        if confidence >= self.runtime.min_confidence:
            return self.runtime.risk_min
        return 0.0


class DecisionEngine:
    """Núcleo puro de decisão compartilhado entre conectores."""

    def __init__(self, model: TradingModel, runtime: DecisionRuntimeConfig):
        self.model = model
        self.runtime = runtime

    def analyze_market(
        self,
        candles_df: pd.DataFrame,
        *,
        win_rate: float = 0.5,
        mode: str = "demo",
        max_risk_real: float | None = None,
    ) -> dict:
        if len(candles_df) < 50:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "risk": 0.0,
                "rationale": "Dados insuficientes",
                "regime": "lateral",
                "feature_snapshot": None,
                "atr_pct": 0.0,
            }

        features = FeatureBuilder.build(candles_df)
        if len(features) == 0:
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "risk": 0.0,
                "rationale": "Features indisponíveis",
                "regime": "lateral",
                "feature_snapshot": None,
                "atr_pct": 0.0,
            }

        last_row = features.iloc[-1:]
        last_series = last_row.iloc[0]
        regime = FeatureBuilder.detect_regime(last_series)
        prediction = self.model.predict(last_row)

        if win_rate < 0.45:
            prediction["signal"] = "HOLD"
            prediction["risk"] = 0.0
            prediction["reason"] = f"Win rate baixo: {win_rate:.1%}"
        elif win_rate > 0.65:
            prediction["risk"] = min(float(prediction.get("risk", 0) or 0) * 1.2, self.runtime.risk_max)

        if str(mode).lower() == "real" and max_risk_real is not None:
            prediction["risk"] = min(float(prediction.get("risk", 0) or 0), float(max_risk_real))

        rationale = prediction.get("rationale") or prediction.get("reason", "")
        if rationale:
            rationale = f"[{regime.upper()}] {rationale} | WR={win_rate:.0%}"
        else:
            rationale = f"[{regime.upper()}] Ensemble RF+GB | WR={win_rate:.0%}"

        feature_snapshot = {
            key: float(last_series.get(key, 0) or 0)
            for key in FeatureBuilder.get_feature_cols()
        }

        return {
            "signal": prediction.get("signal", "HOLD"),
            "confidence": float(prediction.get("confidence", 0) or 0),
            "risk": float(prediction.get("risk", 0) or 0),
            "prob_buy": float(prediction.get("prob_buy", 0) or 0),
            "prob_sell": float(prediction.get("prob_sell", 0) or 0),
            "rationale": rationale,
            "regime": regime,
            "win_rate": float(win_rate),
            "feature_snapshot": feature_snapshot,
            "atr_pct": float(last_series.get("atr_pct", 0) or 0),
            "last_row": last_row,
        }


def generate_bootstrap_market_data(n: int = 600) -> pd.DataFrame:
    np.random.seed(42)
    base = 1.1000
    noise = np.random.normal(0, 0.002, n).cumsum()
    close = base + noise
    open_ = close + np.random.normal(0, 0.0005, n)
    high = np.maximum(open_, close) + np.abs(np.random.normal(0.0008, 0.0004, n))
    low = np.minimum(open_, close) - np.abs(np.random.normal(0.0008, 0.0004, n))
    return pd.DataFrame({
        "time": pd.date_range(end=pd.Timestamp.utcnow(), periods=n, freq="min"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(100, 1000, n).astype(float),
    })


def load_model_weights(
    model: TradingModel,
    rf_path: str | Path = DEFAULT_MODEL_RF,
    gb_path: str | Path = DEFAULT_MODEL_GB,
    scaler_path: str | Path = DEFAULT_MODEL_SCALER,
) -> bool:
    """Carrega pesos RF/GB/Scaler do disco para o modelo informado."""
    rf_file = Path(rf_path)
    gb_file = Path(gb_path)
    scaler_file = Path(scaler_path)
    if not rf_file.exists() or not gb_file.exists() or not scaler_file.exists():
        return False

    try:
        with rf_file.open("rb") as f:
            model.rf = pickle.load(f)
        with gb_file.open("rb") as f:
            model.gb = pickle.load(f)
        with scaler_file.open("rb") as f:
            model.scaler = pickle.load(f)

        model.trained = True
        return True
    except Exception as exc:
        log.warning("Falha ao carregar pesos do modelo: %s", exc)
        return False


def save_model_weights(
    model: TradingModel,
    rf_path: str | Path = DEFAULT_MODEL_RF,
    gb_path: str | Path = DEFAULT_MODEL_GB,
    scaler_path: str | Path = DEFAULT_MODEL_SCALER,
) -> bool:
    """Persiste pesos RF/GB/Scaler do modelo em disco."""
    if not model.trained:
        return False

    rf_file = Path(rf_path)
    gb_file = Path(gb_path)
    scaler_file = Path(scaler_path)
    try:
        rf_file.parent.mkdir(parents=True, exist_ok=True)
        gb_file.parent.mkdir(parents=True, exist_ok=True)
        scaler_file.parent.mkdir(parents=True, exist_ok=True)
        with rf_file.open("wb") as f:
            pickle.dump(model.rf, f)
        with gb_file.open("wb") as f:
            pickle.dump(model.gb, f)
        with scaler_file.open("wb") as f:
            pickle.dump(model.scaler, f)
        return True
    except Exception as exc:
        log.warning("Falha ao salvar pesos do modelo: %s", exc)
        return False