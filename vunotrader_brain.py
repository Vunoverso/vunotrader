"""
VunoTrader — Python ML Brain
Versão: 2.0 | 29/03/2026

Função:
- Treina modelo ML com histórico de preços
- Analisa mercado em tempo real
- Ajusta parâmetros dinamicamente
- Envia sinais de entrada pro MT5 via socket
- Aprende com cada resultado

Instalação:
pip install pandas numpy scikit-learn MetaTrader5 ta-lib-python
"""

import socket
import json
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
import threading
import os
import re
import importlib
import hashlib
import hmac

try:
    from supabase import create_client, Client as SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    # Import dinâmico para manter o pacote opcional sem gerar alerta estático.
    bp = importlib.import_module("brainpy")
    BRAINPY_AVAILABLE = True
    BRAINPY_IMPORT_ERROR = ""
except Exception as e:
    bp = None
    BRAINPY_AVAILABLE = False
    BRAINPY_IMPORT_ERROR = str(e)

try:
    from dotenv import load_dotenv
    # Carrega brain.env na raiz do projeto (não versionado)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain.env"))
except ImportError:
    pass  # python-dotenv opcional; variáveis podem ser definidas no ambiente

# ─── Configuração de logging ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('vunotrader_brain.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('VunoTrader')

# ─── Configurações ────────────────────────────────────────────────
# Credenciais Supabase lidas do ambiente (nunca hardcoded)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

CONFIG = {
    "socket_host":       "127.0.0.1",
    "socket_port":       9999,
    "retrain_interval":  3600,      # Retreinar a cada 1 hora (segundos)
    "signal_interval":   30,        # Enviar sinal a cada 30 segundos
    "min_confidence":    0.62,      # Confiança mínima para enviar sinal (62%)
    "risk_base":         2.0,       # Risco base por operação (%)
    "risk_max":          4.0,       # Risco máximo por operação (%)
    "risk_min":          0.5,       # Risco mínimo por operação (%)
    "history_file":      "VunoTrader_history.csv",
    "model_file":        "vunotrader_model.pkl",
    "lookback_candles":  500,       # Candles para treino
    "enable_brainpy":    os.environ.get("ENABLE_BRAINPY", "0") == "1",  # uso opcional
}


# ─── Feature Engineering ─────────────────────────────────────────
class FeatureBuilder:
    """Constrói features técnicas a partir de dados OHLCV"""

    @staticmethod
    def build(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()

        # Médias móveis
        for period in [5, 9, 21, 50, 200]:
            d[f'ema_{period}'] = d['close'].ewm(span=period).mean()

        # RSI
        delta = d['close'].diff()
        gain  = delta.clip(lower=0).rolling(14).mean()
        loss  = (-delta.clip(upper=0)).rolling(14).mean()
        rs    = gain / loss.replace(0, np.nan)
        d['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = d['close'].ewm(span=12).mean()
        ema26 = d['close'].ewm(span=26).mean()
        d['macd']        = ema12 - ema26
        d['macd_signal'] = d['macd'].ewm(span=9).mean()
        d['macd_hist']   = d['macd'] - d['macd_signal']

        # Bollinger Bands
        ma20      = d['close'].rolling(20).mean()
        std20     = d['close'].rolling(20).std()
        d['bb_upper'] = ma20 + (2 * std20)
        d['bb_lower'] = ma20 - (2 * std20)
        d['bb_width'] = (d['bb_upper'] - d['bb_lower']) / ma20
        d['bb_pos']   = (d['close'] - d['bb_lower']) / (d['bb_upper'] - d['bb_lower'] + 1e-10)

        # ATR (volatilidade)
        high_low   = d['high'] - d['low']
        high_close = (d['high'] - d['close'].shift()).abs()
        low_close  = (d['low']  - d['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        d['atr'] = tr.rolling(14).mean()
        d['atr_pct'] = d['atr'] / d['close']  # ATR normalizado

        # Momentum
        d['momentum_5']  = d['close'].pct_change(5)
        d['momentum_10'] = d['close'].pct_change(10)
        d['momentum_20'] = d['close'].pct_change(20)

        # Volume relativo
        if 'volume' in d.columns:
            d['volume_ratio'] = d['volume'] / d['volume'].rolling(20).mean()
        else:
            d['volume_ratio'] = 1.0

        # Cruzamentos de médias (sinais)
        d['cross_9_21']  = np.sign(d['ema_9']  - d['ema_21'])
        d['cross_21_50'] = np.sign(d['ema_21'] - d['ema_50'])
        d['cross_50_200']= np.sign(d['ema_50'] - d['ema_200'])

        # Distância do preço às médias (normalizada)
        d['dist_ema9']  = (d['close'] - d['ema_9'])  / d['close']
        d['dist_ema21'] = (d['close'] - d['ema_21']) / d['close']
        d['dist_ema50'] = (d['close'] - d['ema_50']) / d['close']

        return d.dropna()

    @staticmethod
    def get_feature_cols() -> list:
        return [
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_width', 'bb_pos', 'atr_pct',
            'momentum_5', 'momentum_10', 'momentum_20',
            'volume_ratio',
            'cross_9_21', 'cross_21_50', 'cross_50_200',
            'dist_ema9', 'dist_ema21', 'dist_ema50'
        ]

    @staticmethod
    def detect_regime(features_row: pd.Series) -> str:
        """
        Classifica o regime de mercado atual em 3 categorias:
        - tendencia: EMAs alinhadas, spread significativo
        - lateral: EMAs proximas, volatilidade baixa
        - volatil: ATR elevado, sinais contraditorios
        """
        atr_pct   = float(features_row.get('atr_pct', 0))
        bb_width  = float(features_row.get('bb_width', 0))
        cross_9   = float(features_row.get('cross_9_21', 0))
        cross_21  = float(features_row.get('cross_21_50', 0))
        cross_50  = float(features_row.get('cross_50_200', 0))
        dist_50   = abs(float(features_row.get('dist_ema50', 0)))
        mom_20    = abs(float(features_row.get('momentum_20', 0)))

        # Tendencia: EMAs alinhadas na mesma direcao
        aligned_up   = cross_9 > 0 and cross_21 > 0 and cross_50 > 0
        aligned_down = cross_9 < 0 and cross_21 < 0 and cross_50 < 0
        is_trending  = (aligned_up or aligned_down) and dist_50 > 0.008 and mom_20 > 0.01

        # Volatil: ATR alto OU Bollinger muito largo
        is_volatile = atr_pct > 0.015 or bb_width > 0.06

        if is_volatile:
            return "volatil"
        if is_trending:
            return "tendencia"
        return "lateral"


# ─── Modelo ML ───────────────────────────────────────────────────
class TradingModel:
    """
    Ensemble de RandomForest + GradientBoosting
    Aprende com histórico e prevê direção do próximo movimento
    """

    def __init__(self):
        self.rf  = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=20,
            random_state=42,
            n_jobs=-1
        )
        self.gb  = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
        self.scaler    = StandardScaler()
        self.trained   = False
        self.accuracy  = 0.0
        self.feature_importance = {}

    def prepare_labels(self, df: pd.DataFrame, forward_bars: int = 5) -> pd.Series:
        """
        Label: 1 (compra) se preço subir X% nos próximos N candles
               0 (neutro/venda) caso contrário
        """
        future_return = df['close'].shift(-forward_bars) / df['close'] - 1
        threshold     = df['atr_pct'].mean() * 0.5
        return (future_return > threshold).astype(int)

    def train(self, df: pd.DataFrame) -> bool:
        try:
            features = FeatureBuilder.build(df)
            feat_cols = FeatureBuilder.get_feature_cols()
            labels    = self.prepare_labels(features)

            # Alinhar
            valid_idx = features.index.intersection(labels.dropna().index)
            X = features.loc[valid_idx, feat_cols]
            y = labels.loc[valid_idx]

            if len(X) < 100:
                log.warning("Dados insuficientes para treino (< 100 amostras)")
                return False

            # Normalizar
            X_scaled = self.scaler.fit_transform(X)

            # Cross-validation
            cv_rf = cross_val_score(self.rf, X_scaled, y, cv=5, scoring='accuracy')
            cv_gb = cross_val_score(self.gb, X_scaled, y, cv=5, scoring='accuracy')

            self.accuracy = max(cv_rf.mean(), cv_gb.mean())
            log.info(f"CV Accuracy — RF: {cv_rf.mean():.3f} | GB: {cv_gb.mean():.3f}")

            # Treinar modelos completos
            self.rf.fit(X_scaled, y)
            self.gb.fit(X_scaled, y)

            # Feature importance
            self.feature_importance = dict(zip(
                feat_cols,
                self.rf.feature_importances_
            ))

            self.trained = True
            log.info(f"Modelo treinado | Accuracy: {self.accuracy:.3f} | Amostras: {len(X)}")
            return True

        except Exception as e:
            log.error(f"Erro no treino: {e}")
            return False

    def predict(self, features_row: pd.DataFrame) -> dict:
        """Retorna sinal + confiança + risco sugerido"""
        if not self.trained:
            return {"signal": "HOLD", "confidence": 0.0, "risk": 0.0}

        try:
            feat_cols = FeatureBuilder.get_feature_cols()
            X = features_row[feat_cols].values.reshape(1, -1)
            X_scaled = self.scaler.transform(X)

            # Ensemble: média das probabilidades
            prob_rf = self.rf.predict_proba(X_scaled)[0]
            prob_gb = self.gb.predict_proba(X_scaled)[0]
            prob    = (prob_rf + prob_gb) / 2

            confidence_buy  = prob[1]
            confidence_sell = prob[0]
            confidence      = max(confidence_buy, confidence_sell)

            if confidence_buy > confidence_sell:
                signal = "BUY"
            else:
                signal = "SELL"

            if confidence < CONFIG["min_confidence"]:
                signal = "HOLD"

            # Risco dinâmico baseado na confiança
            risk = self._calculate_dynamic_risk(confidence)

            # Rationale rico em linguagem humana
            rationale = self._generate_rationale(signal, confidence, features_row)

            return {
                "signal":     signal,
                "confidence": round(float(confidence), 4),
                "risk":       round(risk, 2),
                "prob_buy":   round(float(confidence_buy), 4),
                "prob_sell":  round(float(confidence_sell), 4),
                "rationale":  rationale,
            }

        except Exception as e:
            log.error(f"Erro na predição: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "risk": 0.0}

    def _generate_rationale(self, signal: str, confidence: float, row: pd.DataFrame) -> str:
        """
        Gera explicação em linguagem humana a partir dos valores dos indicadores.
        Usa feature_importance para priorizar as features mais relevantes no contexto atual.
        """
        try:
            feat = row.iloc[0] if hasattr(row, 'iloc') else row

            rsi       = float(feat.get('rsi', 50))
            macd_hist = float(feat.get('macd_hist', 0))
            bb_pos    = float(feat.get('bb_pos', 0.5))
            atr_pct   = float(feat.get('atr_pct', 0))
            mom_5     = float(feat.get('momentum_5', 0))
            vol_ratio = float(feat.get('volume_ratio', 1))
            cross_9   = float(feat.get('cross_9_21', 0))

            clues = []

            # RSI
            if rsi >= 70:
                clues.append(f"RSI sobrecomprado ({rsi:.1f})")
            elif rsi <= 30:
                clues.append(f"RSI sobrevendido ({rsi:.1f})")
            else:
                clues.append(f"RSI neutro ({rsi:.1f})")

            # MACD histograma
            if macd_hist > 0:
                clues.append("MACD histograma positivo (momentum de alta)")
            elif macd_hist < 0:
                clues.append("MACD histograma negativo (momentum de baixa)")

            # Posição nas Bollinger Bands
            if bb_pos > 0.85:
                clues.append("preço próximo da banda superior (Bollinger)")
            elif bb_pos < 0.15:
                clues.append("preço próximo da banda inferior (Bollinger)")

            # Volatilidade
            if atr_pct > 0.015:
                clues.append(f"volatilidade elevada (ATR {atr_pct*100:.2f}%)")
            elif atr_pct < 0.004:
                clues.append(f"volatilidade comprimida (ATR {atr_pct*100:.2f}%)")

            # Momentum curto
            if abs(mom_5) > 0.005:
                dir_str = "alta" if mom_5 > 0 else "baixa"
                clues.append(f"momentum de {dir_str} nos últimos 5 candles ({mom_5*100:.2f}%)")

            # Volume
            if vol_ratio > 1.5:
                clues.append(f"volume acima da média ({vol_ratio:.1f}x)")
            elif vol_ratio < 0.6:
                clues.append("volume abaixo da média")

            # Tendência de médias
            if cross_9 > 0:
                clues.append("EMA9 acima da EMA21 (tendência de curto prazo: alta)")
            elif cross_9 < 0:
                clues.append("EMA9 abaixo da EMA21 (tendência de curto prazo: baixa)")

            # Convicção
            if confidence >= 0.80:
                conviction = "alta convicção"
            elif confidence >= 0.72:
                conviction = "convicção moderada"
            else:
                conviction = "baixa convicção"

            signal_str = {"BUY": "COMPRA", "SELL": "VENDA", "HOLD": "AGUARDAR"}.get(signal, signal)

            if not clues:
                return f"Sinal {signal_str} ({conviction}, confiança {confidence*100:.1f}%)"

            context = " | ".join(clues[:4])  # limita a 4 para não ficar longo
            return f"{signal_str} ({conviction}, {confidence*100:.1f}%): {context}"
        except Exception:
            return f"Sinal {signal} com confiança {confidence*100:.1f}%"

    def _calculate_dynamic_risk(self, confidence: float) -> float:
        """
        Ajusta risco automaticamente:
        - Confiança alta (>80%) → risco maior
        - Confiança baixa (62-70%) → risco mínimo
        """
        if confidence >= 0.80:
            return CONFIG["risk_max"]
        elif confidence >= 0.72:
            return CONFIG["risk_base"]
        elif confidence >= 0.62:
            return CONFIG["risk_min"]
        return 0.0


# ─── Gerenciador de Aprendizado ──────────────────────────────────
class LearningManager:
    """Carrega histórico do CSV e retroalimenta o modelo"""

    def __init__(self, history_file: str):
        self.history_file = history_file
        self.history      = []

    def load(self):
        if not os.path.exists(self.history_file):
            log.info("Sem histórico anterior — começando do zero")
            return

        try:
            df = pd.read_csv(self.history_file)
            self.history = df.to_dict('records')
            wins  = sum(1 for t in self.history if t.get('result') == 'WIN')
            total = len(self.history)
            wr    = wins / total if total > 0 else 0
            log.info(f"Histórico carregado: {total} trades | Win Rate: {wr:.1%}")
        except Exception as e:
            log.error(f"Erro ao carregar histórico: {e}")

    def get_win_rate(self, last_n: int = 50) -> float:
        if not self.history:
            return 0.5
        recent = self.history[-last_n:]
        wins   = sum(1 for t in recent if t.get('result') == 'WIN')
        return wins / len(recent)

    def get_performance_metrics(self) -> dict:
        if not self.history:
            return {}
        df = pd.DataFrame(self.history)
        return {
            "total_trades":  len(df),
            "win_rate":      self.get_win_rate(),
            "avg_profit":    df[df['result'] == 'WIN']['profit'].mean() if 'profit' in df else 0,
            "avg_loss":      df[df['result'] == 'LOSS']['profit'].mean() if 'profit' in df else 0,
            "profit_factor": abs(
                df[df['result'] == 'WIN']['profit'].sum() /
                (df[df['result'] == 'LOSS']['profit'].sum() + 1e-10)
            ) if 'profit' in df else 0,
        }


# ─── Helper: snapshot de features para flywheel ─────────────────
_SNAPSHOT_KEYS = (
    "rsi", "macd", "macd_signal", "macd_hist",
    "bb_width", "bb_pos", "atr_pct",
    "momentum_5", "momentum_10", "momentum_20",
    "volume_ratio",
    "cross_9_21", "cross_21_50", "cross_50_200",
    "dist_ema9", "dist_ema21", "dist_ema50",
)

def _build_feature_snapshot(msg: dict) -> dict | None:
    """
    Extrai features técnicas de um msg dict (vindo do MT5 ou do decision payload).
    Aceita tanto um sub-dict 'features' quanto chaves diretas no topo do msg.
    Retorna None se nenhuma feature estiver disponível.
    """
    # Prioridade 1: sub-dict 'features' enviado explicitamente pelo MT5
    if isinstance(msg.get("features"), dict) and msg["features"]:
        return {k: float(v) for k, v in msg["features"].items() if v is not None}

    # Prioridade 2: chaves soltas no topo do msg
    snap = {k: float(msg[k]) for k in _SNAPSHOT_KEYS if msg.get(k) is not None}
    return snap if snap else None


# ─── Camada de Persistência Supabase ────────────────────────────
class SupabaseLogger:
    """
    Persiste decisões e resultados de trades no Supabase.
    Usada pelo MT5Bridge para registrar cada operação com rastreabilidade.
    Requer variáveis de ambiente: SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY
    """

    def __init__(self):
        self._client: "SupabaseClient | None" = None
        if SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_SERVICE_KEY:
            try:
                self._client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
                log.info("Supabase conectado. Persistência de trades ativa.")
            except Exception as e:
                log.warning(f"Falha ao conectar Supabase: {e}. Operando sem persistência.")
        else:
            log.warning("Supabase não configurado. Setando SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY para ativar persistência.")

    @property
    def active(self) -> bool:
        return self._client is not None

    def validate_robot_identity(
        self,
        organization_id: str,
        user_profile_id: str,
        robot_instance_id: str,
        robot_token: str,
        mode: str,
    ) -> tuple[bool, float | None, str | None]:
        """Valida robot_id/token e retorna politica de risco para modo real."""
        if not self.active:
            return False, None, "Supabase indisponivel"

        if not organization_id or not user_profile_id or not robot_instance_id or not robot_token:
            return False, None, "Identificacao incompleta"

        token_hash = hashlib.sha256(robot_token.encode("utf-8")).hexdigest()

        try:
            resp = (
                self._client.table("robot_instances")
                .select("id, status, profile_id, organization_id, robot_token_hash, allowed_modes, real_trading_enabled, max_risk_real")
                .eq("id", robot_instance_id)
                .eq("organization_id", organization_id)
                .eq("profile_id", user_profile_id)
                .limit(1)
                .maybe_single()
                .execute()
            )
            row = resp.data or None
            if not row:
                return False, None, "Robo nao encontrado"

            if row.get("status") != "active":
                return False, None, "Robo inativo"

            stored_hash = str(row.get("robot_token_hash") or "")
            if not stored_hash:
                return False, None, "Token nao configurado"

            if not hmac.compare_digest(stored_hash, token_hash):
                return False, None, "Token invalido"

            allowed_modes = [str(m).lower() for m in (row.get("allowed_modes") or ["demo"]) if str(m).strip()]
            mode_normalized = str(mode or "demo").lower()
            if mode_normalized not in allowed_modes:
                return False, None, f"Modo {mode_normalized} nao permitido para este robo"

            if mode_normalized == "real" and not bool(row.get("real_trading_enabled")):
                return False, None, "Robo sem autorizacao para conta real"

            max_risk_real = float(row.get("max_risk_real") or 1.5)
            return True, max_risk_real, None
        except Exception as e:
            msg = str(e)
            if "robot_instances" in msg and "schema cache" in msg:
                log.error("[Supabase] Migration robot_instances nao aplicada no banco remoto.")
            else:
                log.error("[Supabase] Falha ao validar robot_instance: %s", e)
            return False, None, "Falha de validacao do robo"

    def log_decision(self, user_id: str, mode: str, symbol: str, timeframe: str,
                     side: str, confidence: float, risk_pct: float,
                     rationale: str, organization_id: str | None = None,
                     robot_instance_id: str | None = None) -> str | None:
        """Insere um registro em trade_decisions. Retorna o UUID gerado."""
        if not self.active:
            return None
        if not _normalize_uuid(user_id):
            log.warning("[Supabase] Decisao nao registrada: user_id ausente/invalido")
            return None
        try:
            trade_id = f"{symbol}-{int(time.time() * 1000)}"
            resp = self._client.table("trade_decisions").insert({
                "trade_id":        trade_id,
                "user_id":         user_id,
                "organization_id": organization_id,
                "robot_instance_id": robot_instance_id,
                "mode":            mode,
                "symbol":          symbol,
                "timeframe":       timeframe,
                "side":            side,
                "confidence":      confidence,
                "risk_pct":        risk_pct,
                "rationale":       rationale,
            }).execute()
            decision_id = resp.data[0]["id"] if resp.data else None
            log.info(f"[Supabase] Decisão registrada: {decision_id} | {side} {symbol}")
            return decision_id
        except Exception as e:
            log.error(f"[Supabase] Erro ao registrar decisão: {e}")
            return None

    def log_trade_open(self, decision_id: str, broker_ticket: str | None,
                       entry_price: float, stop_loss: float, take_profit: float,
                       lot: float, organization_id: str | None = None,
                       robot_instance_id: str | None = None) -> str | None:
        """Insere um executed_trade com status 'open'. Retorna o UUID."""
        if not self.active or not decision_id:
            return None
        try:
            resp = self._client.table("executed_trades").insert({
                "trade_decision_id": decision_id,
                "organization_id":   organization_id,
                "robot_instance_id": robot_instance_id,
                "broker_ticket":     broker_ticket,
                "entry_price":       entry_price,
                "stop_loss":         stop_loss,
                "take_profit":       take_profit,
                "lot":               lot,
                "status":            "open",
                "opened_at":         datetime.utcnow().isoformat(),
            }).execute()
            trade_id = resp.data[0]["id"] if resp.data else None
            log.info(f"[Supabase] Trade aberto: {trade_id}")
            return trade_id
        except Exception as e:
            log.error(f"[Supabase] Erro ao registrar trade aberto: {e}")
            return None

    def log_trade_close(self, executed_trade_id: str, result: str,
                        pnl_money: float, pnl_points: float,
                        win_loss_reason: str,
                        organization_id: str | None = None,
                        robot_instance_id: str | None = None):
        """Atualiza executed_trade para 'closed' e insere trade_outcome."""
        if not self.active or not executed_trade_id:
            return
        try:
            # Fechar o trade
            self._client.table("executed_trades").update({
                "status":    "closed",
                "closed_at": datetime.utcnow().isoformat(),
            }).eq("id", executed_trade_id).execute()

            # Inserir resultado
            self._client.table("trade_outcomes").insert({
                "executed_trade_id": executed_trade_id,
                "organization_id":   organization_id,
                "robot_instance_id": robot_instance_id,
                "result":            result.lower(),
                "pnl_money":         pnl_money,
                "pnl_points":        pnl_points,
                "win_loss_reason":   win_loss_reason,
            }).execute()

            log.info(f"[Supabase] Trade fechado: {executed_trade_id} | {result} | PnL: {pnl_money:.2f}")
        except Exception as e:
            log.error(f"[Supabase] Erro ao fechar trade: {e}")

    def log_anonymized_event(
        self,
        decision_id: str | None,
        outcome_id: str | None,
        mode: str,
        symbol: str,
        timeframe: str,
        side: str,
        confidence: float,
        risk_pct: float,
        result: str | None,
        pnl_points: float | None,
        regime: str | None,
        atr_pct: float | None,
        user_id: str,
        org_id: str,
        feature_snapshot: dict | None = None,
        model_version: str | None = None,
    ):
        """
        Persiste em anonymized_trade_events para flywheel de dados.
        User/org são hasheados antes de gravar — nunca expõe identidade.
        """
        if not self.active:
            return
        try:
            anon_user = hashlib.sha256(f"user:{user_id}:salt-vuno-v1".encode()).hexdigest()
            anon_org  = hashlib.sha256(f"org:{org_id}:salt-vuno-v1".encode()).hexdigest()
            self._client.table("anonymized_trade_events").insert({
                "source_trade_decision_id": decision_id,
                "source_trade_outcome_id":  outcome_id,
                "anonymous_user_hash":      anon_user,
                "anonymous_org_hash":       anon_org,
                "mode":                     mode,
                "symbol":                   symbol,
                "timeframe":                timeframe,
                "side":                     side,
                "confidence":               confidence,
                "risk_pct":                 risk_pct,
                "result":                   result,
                "pnl_points":               pnl_points,
                "regime":                   regime,
                "volatility":               atr_pct,
                "feature_snapshot":         feature_snapshot,
                "model_version":            model_version,
            }).execute()
        except Exception as e:
            log.debug(f"[Supabase] Falha ao gravar anonymized_event: {e}")

    def heartbeat(self, robot_instance_id: str | None):
        """Atualiza last_seen_at da instancia de robo. Chamado a cada MARKET_DATA."""
        if not self.active or not robot_instance_id:
            return
        try:
            self._client.table("robot_instances").update({
                "last_seen_at": datetime.utcnow().isoformat(),
            }).eq("id", robot_instance_id).execute()
        except Exception as e:
            log.debug(f"[Supabase] Falha no heartbeat: {e}")

    # Cache simples: {user_id: (params_dict, expires_at)}
    _risk_params_cache: dict = {}
    # Cache de drawdown diário: {robot_id: (pnl_total, expires_at)}
    _drawdown_cache: dict = {}

    def get_daily_drawdown(self, robot_id: str | None, user_id: str) -> float:
        """
        Retorna o PnL total do dia atual para o robô.
        Negativo = prejuízo acumulado. Positivo = lucro.
        Cache de 60 segundos para evitar queries a cada candle.
        """
        import time as _time
        cache_key = robot_id or user_id
        now = _time.monotonic()
        cached = self._drawdown_cache.get(cache_key)
        if cached and cached[1] > now:
            return cached[0]

        if not self.active:
            return 0.0
        try:
            today_str = datetime.utcnow().strftime("%Y-%m-%d")
            query = (
                self._client.table("trade_outcomes")
                .select("pnl_money")
                .gte("created_at", f"{today_str}T00:00:00+00:00")
            )
            if robot_id:
                query = query.eq("robot_instance_id", robot_id)
            res = query.execute()
            total = sum(float(r.get("pnl_money") or 0) for r in (res.data or []))
            self._drawdown_cache[cache_key] = (total, now + 60)
            return total
        except Exception as e:
            log.debug(f"[Supabase] get_daily_drawdown falhou: {e}")
            self._drawdown_cache[cache_key] = (0.0, now + 30)
            return 0.0

    def save_lesson(
        self,
        org_id: str,
        profile_id: str,
        robot_id: str | None,
        period_start: str,
        period_end: str,
        title: str,
        summary: str,
        regime: str | None,
        category: str,
        total_trades: int,
        win_rate: float,
        avg_confidence: float,
        total_pnl: float,
        raw_stats: dict | None,
    ) -> str | None:
        """Persiste uma lição gerada automaticamente em lessons_learned."""
        if not self.active or not org_id or not profile_id:
            return None
        try:
            resp = self._client.table("lessons_learned").insert({
                "organization_id":  org_id,
                "profile_id":       profile_id,
                "robot_instance_id": robot_id,
                "period_start":     period_start,
                "period_end":       period_end,
                "title":            title,
                "summary":          summary,
                "regime":           regime,
                "category":         category,
                "total_trades":     total_trades,
                "win_rate_pct":     round(win_rate * 100, 2),
                "avg_confidence":   round(avg_confidence, 3),
                "total_pnl":        round(total_pnl, 2),
                "raw_stats":        raw_stats,
                "generated_by":     "brain_auto",
            }).execute()
            lesson_id = resp.data[0]["id"] if resp.data else None
            log.info(f"[Supabase] Lição salva: {lesson_id} | {title}")
            return lesson_id
        except Exception as e:
            log.debug(f"[Supabase] save_lesson falhou: {e}")
            return None

    def get_risk_params(self, user_id: str) -> dict:
        """Retorna max_consecutive_losses, drawdown_pause_pct e auto_reduce_risk para o usuario.
        Cache de 5 minutos para nao sobrecarregar o Supabase a cada MARKET_DATA."""
        import time as _time
        now = _time.monotonic()
        cached = self._risk_params_cache.get(user_id)
        if cached and cached[1] > now:
            return cached[0]

        defaults = {"max_consecutive_losses": 3, "drawdown_pause_pct": 5.0, "auto_reduce_risk": True, "capital_usd": 10000.0}
        if not self.active:
            return defaults
        try:
            res = self._client.table("user_parameters").select(
                "max_consecutive_losses, drawdown_pause_pct, auto_reduce_risk, capital_usd"
            ).eq("user_id", user_id).limit(1).maybe_single().execute()
            if res.data:
                merged = {**defaults, **{k: v for k, v in res.data.items() if v is not None}}
                self._risk_params_cache[user_id] = (merged, now + 300)
                return merged
        except Exception as e:
            log.debug(f"[Supabase] get_risk_params falhou: {e}")
        self._risk_params_cache[user_id] = (defaults, now + 60)
        return defaults


def _normalize_uuid(value: str | None) -> str | None:
    """Retorna UUID normalizado ou None quando ausente/invalido."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", raw):
        return raw.lower()
    return None


# ─── Servidor Socket (comunicação com MT5) ───────────────────────
class MT5Bridge:
    """
    Servidor TCP que recebe dados do MT5 e envia sinais de volta
    Protocolo: JSON via socket TCP na porta 9999
    """

    def __init__(self, host: str, port: int, model: TradingModel,
                 learner: LearningManager, db: SupabaseLogger):
        self.host    = host
        self.port    = port
        self.model   = model
        self.learner = learner
        self.db      = db
        self.server  = None
        self.running = False
        self.last_df = None
        # Mapa ticket → (decision_id, executed_trade_id) para fechar depois
        self._open_trades: dict[str, tuple[str | None, str | None]] = {}
        # Contador de perdas consecutivas por robot_id (reset ao vencer)
        self._consec_losses: dict[str, int] = {}

    def start(self):
        self.running = True
        self.server  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        self.server.settimeout(1.0)
        log.info(f"MT5 Bridge aguardando conexão em {self.host}:{self.port}")

        while self.running:
            try:
                conn, addr = self.server.accept()
                threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    log.error(f"Erro no servidor: {e}")

    def _handle_client(self, conn: socket.socket, addr):
        log.info(f"MT5 conectado: {addr}")
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    break

                message = json.loads(data.decode('utf-8'))
                response = self._process_message(message)
                conn.sendall(json.dumps(response).encode('utf-8'))

        except Exception as e:
            log.error(f"Erro na conexão: {e}")
        finally:
            conn.close()
            log.info(f"MT5 desconectado: {addr}")

    def _process_message(self, msg: dict) -> dict:
        msg_type = msg.get('type', '')

        # MT5 enviando dados de mercado → retornar sinal
        if msg_type == 'MARKET_DATA':
            return self._handle_market_data(msg)

        # MT5 reportando resultado de operação → aprender
        elif msg_type == 'TRADE_RESULT':
            return self._handle_trade_result(msg)

        # MT5 pedindo status do modelo
        elif msg_type == 'STATUS':
            return self._handle_status()

        return {"type": "ERROR", "message": "Tipo desconhecido"}

    def _handle_market_data(self, msg: dict) -> dict:
        try:
            candles  = msg.get('candles', [])
            symbol   = msg.get('symbol', 'UNKNOWN')
            timeframe= msg.get('timeframe', 'M5')
            mode     = msg.get('mode', 'demo')
            user_id  = _normalize_uuid(msg.get('user_id', ''))
            org_id   = _normalize_uuid(msg.get('organization_id', None))
            robot_id = _normalize_uuid(msg.get('robot_id', None))
            robot_token = str(msg.get('robot_token', '') or '').strip()

            if not user_id or not org_id or not robot_id or not robot_token:
                return {
                    "type": "SIGNAL",
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "risk": 0.0,
                    "reason": "Identificacao incompleta: user_id, organization_id, robot_id e robot_token sao obrigatorios",
                }

            is_valid_robot, max_risk_real, robot_err = self.db.validate_robot_identity(
                org_id,
                user_id,
                robot_id,
                robot_token,
                mode,
            )
            if not is_valid_robot:
                return {
                    "type": "SIGNAL",
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "risk": 0.0,
                    "reason": robot_err or "Robo nao autorizado para este usuario/organizacao",
                }

            # Verificar proteção de perdas consecutivas
            risk_params = self.db.get_risk_params(user_id)
            max_consec = int(risk_params.get("max_consecutive_losses") or 3)
            current_consec = self._consec_losses.get(robot_id, 0)
            if current_consec >= max_consec:
                log.warning(f"[RISCO] Robot {robot_id}: {current_consec} perdas consecutivas >= limite {max_consec}. Sinal bloqueado.")
                return {
                    "type": "SIGNAL",
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "risk": 0.0,
                    "paused": True,
                    "reason": f"Motor pausado: {current_consec} perdas consecutivas (limite: {max_consec}). Revise a estrategia no painel.",
                }

            # Verificar drawdown diário
            drawdown_pct_limit = float(risk_params.get("drawdown_pause_pct") or 5.0)
            capital = float(risk_params.get("capital_usd") or 10000.0)
            if drawdown_pct_limit > 0 and capital > 0:
                daily_pnl = self.db.get_daily_drawdown(robot_id, user_id)
                drawdown_limit_money = -(drawdown_pct_limit / 100.0) * capital
                if daily_pnl <= drawdown_limit_money:
                    pct_atual = abs(daily_pnl) / capital * 100
                    log.warning(
                        f"[RISCO] Robot {robot_id}: drawdown diário {pct_atual:.1f}% >= limite {drawdown_pct_limit:.1f}%. "
                        f"PnL dia: {daily_pnl:.2f} | limite: {drawdown_limit_money:.2f}"
                    )
                    return {
                        "type": "SIGNAL",
                        "signal": "HOLD",
                        "confidence": 0.0,
                        "risk": 0.0,
                        "paused": True,
                        "paused_reason": "drawdown",
                        "reason": (
                            f"Motor pausado: drawdown diário atingiu {pct_atual:.1f}% "
                            f"(limite: {drawdown_pct_limit:.1f}%). Retoma amanhã."
                        ),
                    }

            if len(candles) < 50:
                return {"type": "SIGNAL", "signal": "HOLD",
                        "confidence": 0.0, "risk": 0.0,
                        "reason": "Dados insuficientes"}

            df = pd.DataFrame(candles,
                              columns=['time','open','high','low','close','volume'])
            df['close'] = pd.to_numeric(df['close'])
            df['high']  = pd.to_numeric(df['high'])
            df['low']   = pd.to_numeric(df['low'])

            features = FeatureBuilder.build(df)
            if len(features) == 0:
                return {"type": "SIGNAL", "signal": "HOLD",
                        "confidence": 0.0, "risk": 0.0}

            last_row = features.iloc[-1:]
            regime = FeatureBuilder.detect_regime(last_row.iloc[0])

            prediction = self.model.predict(last_row)

            win_rate = self.learner.get_win_rate()
            if win_rate < 0.45:
                prediction['signal'] = 'HOLD'
                prediction['reason'] = f'Win rate baixo: {win_rate:.1%}'
            elif win_rate > 0.65:
                prediction['risk'] = min(prediction['risk'] * 1.2, CONFIG['risk_max'])

            # Em modo real, limitar risco ao teto da policy do robo.
            if mode == "real" and max_risk_real is not None:
                prediction['risk'] = min(float(prediction['risk']), float(max_risk_real))

            # Rationale final: inclui regime e win_rate
            rationale = prediction.get('rationale') or prediction.get('reason', '')
            atr_pct   = float(last_row.iloc[0].get('atr_pct', 0))
            if rationale:
                rationale = f"[{regime.upper()}] {rationale} | WR={win_rate:.0%}"
            else:
                rationale = f"[{regime.upper()}] Ensemble RF+GB | WR={win_rate:.0%}"

            # Heartbeat: atualiza last_seen_at para o dashboard ler estado real
            self.db.heartbeat(robot_id)

            # Persistir decisão no Supabase (independente de ser HOLD ou não)
            decision_id = self.db.log_decision(
                user_id=user_id,
                organization_id=org_id,
                robot_instance_id=robot_id,
                mode=mode,
                symbol=symbol,
                timeframe=timeframe,
                side=prediction['signal'].lower() if prediction['signal'] != 'HOLD' else 'hold',
                confidence=prediction['confidence'],
                risk_pct=prediction['risk'],
                rationale=rationale,
            )

            response = {
                "type":        "SIGNAL",
                "signal":      prediction['signal'],
                "confidence":  prediction['confidence'],
                "risk":        prediction['risk'],
                "win_rate":    round(win_rate, 4),
                "regime":      regime,
                "timestamp":   datetime.now().isoformat(),
                "decision_id": decision_id,
            }

            if prediction['signal'] != 'HOLD':
                log.info(f"SINAL: {prediction['signal']} | "
                         f"Confiança: {prediction['confidence']:.1%} | "
                         f"Risco: {prediction['risk']}% | "
                         f"Regime: {regime} | "
                         f"WR: {win_rate:.1%}")

            return response

        except Exception as e:
            log.error(f"Erro ao processar dados: {e}")
            return {"type": "SIGNAL", "signal": "HOLD",
                    "confidence": 0.0, "risk": 0.0}

    def _handle_trade_result(self, msg: dict) -> dict:
        profit      = msg.get('profit', 0)
        points      = msg.get('points', 0)
        ticket      = msg.get('ticket', '')
        decision_id = _normalize_uuid(msg.get('decision_id', None))
        entry_price = msg.get('entry_price', 0)
        stop_loss   = msg.get('stop_loss', 0)
        take_profit = msg.get('take_profit', 0)
        lot         = msg.get('lot', 0)
        org_id      = _normalize_uuid(msg.get('organization_id', None))
        user_id     = _normalize_uuid(msg.get('user_id', ''))
        robot_id    = _normalize_uuid(msg.get('robot_id', None))
        robot_token = str(msg.get('robot_token', '') or '').strip()
        result      = 'WIN' if profit > 0 else ('LOSS' if profit < 0 else 'breakeven')

        if not decision_id:
            log.warning("TRADE_RESULT ignorado para persistencia: decision_id ausente/invalido | ticket=%s", ticket)
            return {"type": "ACK", "status": "Sem decision_id valido", "result": result}

        if not user_id or not org_id or not robot_id or not robot_token:
            return {"type": "ACK", "status": "Identificacao incompleta do robo", "result": result}

        is_valid_robot, _, robot_err = self.db.validate_robot_identity(
            org_id,
            user_id,
            robot_id,
            robot_token,
            str(msg.get("mode", "demo") or "demo"),
        )
        if not is_valid_robot:
            return {"type": "ACK", "status": robot_err or "Robo nao autorizado", "result": result}

        # Registrar o trade aberto (se ainda não está mapeado)
        executed_id: str | None = None
        if decision_id and ticket not in self._open_trades:
            executed_id = self.db.log_trade_open(
                decision_id=decision_id,
                organization_id=org_id,
                robot_instance_id=robot_id,
                broker_ticket=ticket,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                lot=lot,
            )
            self._open_trades[ticket] = (decision_id, executed_id)

        # Se o ticket já estava mapeado, usar o ID já existente
        if ticket in self._open_trades:
            _, executed_id = self._open_trades.pop(ticket, (None, None))

        # Fechar trade e registrar resultado
        self.db.log_trade_close(
            executed_trade_id=executed_id or '',
            result=result,
            pnl_money=float(profit),
            pnl_points=float(points),
            win_loss_reason=f"MT5 ticket {ticket} | PnL: {profit:.2f}",
            organization_id=org_id,
            robot_instance_id=robot_id,
        )

        # Flywheel: gravar evento anonimizado para melhoria do modelo global
        mode_trade = str(msg.get("mode", "demo") or "demo")
        symbol_trade = str(msg.get("symbol", "") or "")
        self.db.log_anonymized_event(
            decision_id=decision_id,
            outcome_id=None,  # será preenchido em versão futura com FK
            mode=mode_trade,
            symbol=symbol_trade,
            timeframe=str(msg.get("timeframe", "") or ""),
            side=str(msg.get("side", "") or ""),
            confidence=float(msg.get("confidence", 0) or 0),
            risk_pct=float(msg.get("risk_pct", 0) or 0),
            result=result.lower(),
            pnl_points=float(points),
            regime=str(msg.get("regime", "") or ""),
            atr_pct=float(msg.get("atr_pct", 0) or 0) or None,
            user_id=user_id or "",
            org_id=org_id or "",
            feature_snapshot=_build_feature_snapshot(msg),
            model_version=str(msg.get("model_version", "") or "") or None,
        )

        # Retroalimentar o aprendizado local
        self.learner.history.append({
            'timestamp': datetime.now().isoformat(),
            'result':    result.upper(),
            'profit':    profit,
            'user_id':   user_id or '',
        })

        # Atualizar contador de perdas consecutivas por robot
        if robot_id:
            if result.upper() == "LOSS":
                self._consec_losses[robot_id] = self._consec_losses.get(robot_id, 0) + 1
                log.info(f"[RISCO] Perdas consecutivas de {robot_id}: {self._consec_losses[robot_id]}")
            else:
                # WIN ou BREAKEVEN resetam o contador
                self._consec_losses[robot_id] = 0

        # Invalidar cache de drawdown para este robô (resultado mudou o PnL do dia)
        if robot_id and robot_id in self.db._drawdown_cache:
            del self.db._drawdown_cache[robot_id]

        # Verificar se há lições para gerar (a cada 50 trades)
        total_local = len(self.learner.history)
        if total_local > 0 and total_local % 50 == 0 and org_id and user_id:
            self._maybe_generate_lesson(org_id, user_id, robot_id)

        log.info(f"Resultado recebido: {result.upper()} | Profit: {profit:.2f} | "
                 f"WR: {self.learner.get_win_rate():.1%}")

        return {"type": "ACK", "status": "Resultado registrado", "result": result}

    def _maybe_generate_lesson(self, org_id: str, user_id: str, robot_id: str | None) -> None:
        """
        Analisa os últimos 50 trades da memória local e gera uma lição automática
        se houver padrão identificável. Salva em lessons_learned via Supabase.
        """
        try:
            last_50 = self.learner.history[-50:]
            if len(last_50) < 10:
                return

            wins   = sum(1 for t in last_50 if str(t.get("result", "")).upper() == "WIN")
            losses = sum(1 for t in last_50 if str(t.get("result", "")).upper() == "LOSS")
            total  = len(last_50)
            wr     = wins / total if total > 0 else 0
            total_pnl = sum(float(t.get("profit", 0)) for t in last_50)

            # Identificar padrão / regime dominante via learner history
            regimes = [str(t.get("regime", "")) for t in last_50 if t.get("regime")]
            regime_dominant = max(set(regimes), key=regimes.count) if regimes else None

            # Gerar título e summary baseados no padrão
            if wr >= 0.65:
                title    = f"Alta consistência detectada — {wr:.0%} win rate em {total} trades"
                category = "general"
                summary  = (
                    f"O robô manteve win rate de {wr:.0%} nos últimos {total} trades "
                    f"(+{wins}W / -{losses}L). PnL acumulado: {total_pnl:+.2f}. "
                    f"Regime dominante: {regime_dominant or 'variado'}. "
                    "Mantenha os parâmetros atuais e considere aumentar o capital gradualmente."
                )
            elif wr <= 0.40:
                title    = f"Atenção: win rate abaixo de 40% nos últimos {total} trades"
                category = "risk_management"
                summary  = (
                    f"O robô registrou win rate de {wr:.0%} ({wins}W/{losses}L) "
                    f"com PnL de {total_pnl:+.2f}. "
                    f"Regime dominante: {regime_dominant or 'variado'}. "
                    "Revise os parâmetros de entrada, reduza o risco por operação "
                    "e considere pausar até nova análise de mercado."
                )
            else:
                title    = f"Desempenho neutro — {wr:.0%} win rate em {total} trades"
                category = "general"
                summary  = (
                    f"Win rate de {wr:.0%} ({wins}W/{losses}L) nos últimos {total} trades. "
                    f"PnL: {total_pnl:+.2f}. Regime: {regime_dominant or 'variado'}. "
                    "Desempenho dentro do esperado — continue monitorando."
                )

            period_end   = datetime.utcnow().isoformat()
            period_start_ts = self.learner.history[-50].get("timestamp") if len(self.learner.history) >= 50 else period_end

            self.db.save_lesson(
                org_id=org_id,
                profile_id=user_id,
                robot_id=robot_id,
                period_start=str(period_start_ts),
                period_end=period_end,
                title=title,
                summary=summary,
                regime=regime_dominant,
                category=category,
                total_trades=total,
                win_rate=wr,
                avg_confidence=0.0,
                total_pnl=total_pnl,
                raw_stats={"wins": wins, "losses": losses, "total": total},
            )
        except Exception as e:
            log.debug(f"[Lessons] _maybe_generate_lesson falhou: {e}")

    def _handle_status(self) -> dict:
        metrics = self.learner.get_performance_metrics()
        return {
            "type":     "STATUS",
            "trained":  self.model.trained,
            "accuracy": round(self.model.accuracy, 4),
            "metrics":  metrics,
        }

    def stop(self):
        self.running = False
        if self.server:
            self.server.close()


# ─── Loop principal de retreino ──────────────────────────────────
class RetrainScheduler:
    """Retreina o modelo periodicamente com dados acumulados"""

    def __init__(self, model: TradingModel, learner: LearningManager):
        self.model   = model
        self.learner = learner

    def generate_sample_data(self, n: int = 600) -> pd.DataFrame:
        """
        Gera dados simulados para demonstração.
        Em produção: substituir por dados reais via MT5 API ou arquivo.
        """
        np.random.seed(42)
        dates  = pd.date_range('2025-01-01', periods=n, freq='1H')
        price  = 1.1000
        prices = []
        for _ in range(n):
            price *= (1 + np.random.normal(0, 0.001))
            prices.append(price)

        close = np.array(prices)
        df = pd.DataFrame({
            'time':   dates,
            'open':   close * (1 + np.random.normal(0, 0.0002, n)),
            'high':   close * (1 + np.abs(np.random.normal(0, 0.0005, n))),
            'low':    close * (1 - np.abs(np.random.normal(0, 0.0005, n))),
            'close':  close,
            'volume': np.random.randint(100, 1000, n).astype(float),
        })
        return df

    def run(self, interval: int):
        while True:
            log.info("Iniciando retreino do modelo...")
            df = self.generate_sample_data(CONFIG['lookback_candles'])
            self.model.train(df)
            log.info(f"Próximo retreino em {interval // 60} minutos")
            time.sleep(interval)


# ─── Entry point ─────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("VunoTrader ML Brain v2.0 iniciando...")
    log.info("=" * 60)

    if CONFIG["enable_brainpy"]:
        if BRAINPY_AVAILABLE:
            log.info(f"brain-py habilitado | versão: {getattr(bp, '__version__', 'desconhecida')}")
        else:
            log.warning(
                "ENABLE_BRAINPY=1, mas brain-py não carregou. "
                f"Motivo: {BRAINPY_IMPORT_ERROR}. Continuando com engine local."
            )
    else:
        log.info("brain-py desabilitado (ENABLE_BRAINPY=0). Usando engine local RF+GB.")

    # Inicializar componentes
    model   = TradingModel()
    learner = LearningManager(CONFIG['history_file'])
    learner.load()
    db      = SupabaseLogger()

    # Treino inicial
    scheduler = RetrainScheduler(model, learner)
    df_inicial = scheduler.generate_sample_data(CONFIG['lookback_candles'])
    model.train(df_inicial)

    # Iniciar retreino em background
    retrain_thread = threading.Thread(
        target=scheduler.run,
        args=(CONFIG['retrain_interval'],),
        daemon=True
    )
    retrain_thread.start()

    # Iniciar bridge com MT5
    bridge = MT5Bridge(
        CONFIG['socket_host'],
        CONFIG['socket_port'],
        model,
        learner,
        db,
    )

    log.info(f"Sistema pronto | Accuracy inicial: {model.accuracy:.3f}")
    log.info(f"Aguardando MT5 na porta {CONFIG['socket_port']}...")

    try:
        bridge.start()
    except KeyboardInterrupt:
        log.info("Encerrando VunoTrader Brain...")
        bridge.stop()


if __name__ == '__main__':
    main()
