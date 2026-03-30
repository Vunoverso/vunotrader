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

            return {
                "signal":     signal,
                "confidence": round(float(confidence), 4),
                "risk":       round(risk, 2),
                "prob_buy":   round(float(confidence_buy), 4),
                "prob_sell":  round(float(confidence_sell), 4),
            }

        except Exception as e:
            log.error(f"Erro na predição: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "risk": 0.0}

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
    ) -> bool:
        """Valida se robot_id/token pertencem ao user/org informados."""
        if not self.active:
            return False

        if not organization_id or not user_profile_id or not robot_instance_id or not robot_token:
            return False

        token_hash = hashlib.sha256(robot_token.encode("utf-8")).hexdigest()

        try:
            resp = (
                self._client.table("robot_instances")
                .select("id, status, profile_id, organization_id, robot_token_hash")
                .eq("id", robot_instance_id)
                .eq("organization_id", organization_id)
                .eq("profile_id", user_profile_id)
                .limit(1)
                .maybe_single()
                .execute()
            )
            row = resp.data or None
            if not row:
                return False

            if row.get("status") != "active":
                return False

            stored_hash = str(row.get("robot_token_hash") or "")
            if not stored_hash:
                return False

            return hmac.compare_digest(stored_hash, token_hash)
        except Exception as e:
            log.error("[Supabase] Falha ao validar robot_instance: %s", e)
            return False

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

            if not self.db.validate_robot_identity(org_id, user_id, robot_id, robot_token):
                return {
                    "type": "SIGNAL",
                    "signal": "HOLD",
                    "confidence": 0.0,
                    "risk": 0.0,
                    "reason": "Robo nao autorizado para este usuario/organizacao",
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

            prediction = self.model.predict(features.iloc[-1:])

            win_rate = self.learner.get_win_rate()
            if win_rate < 0.45:
                prediction['signal'] = 'HOLD'
                prediction['reason'] = f'Win rate baixo: {win_rate:.1%}'
            elif win_rate > 0.65:
                prediction['risk'] = min(prediction['risk'] * 1.2, CONFIG['risk_max'])

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
                rationale=prediction.get('reason', f"Ensemble RF+GB | WR={win_rate:.1%}"),
            )

            response = {
                "type":        "SIGNAL",
                "signal":      prediction['signal'],
                "confidence":  prediction['confidence'],
                "risk":        prediction['risk'],
                "win_rate":    round(win_rate, 4),
                "timestamp":   datetime.now().isoformat(),
                "decision_id": decision_id,
            }

            if prediction['signal'] != 'HOLD':
                log.info(f"SINAL: {prediction['signal']} | "
                         f"Confiança: {prediction['confidence']:.1%} | "
                         f"Risco: {prediction['risk']}% | "
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

        if not self.db.validate_robot_identity(org_id, user_id, robot_id, robot_token):
            return {"type": "ACK", "status": "Robo nao autorizado", "result": result}

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

        # Retroalimentar o aprendizado local
        self.learner.history.append({
            'timestamp': datetime.now().isoformat(),
            'result':    result.upper(),
            'profit':    profit,
            'user_id':   user_id or '',
        })

        log.info(f"Resultado recebido: {result.upper()} | Profit: {profit:.2f} | "
                 f"WR: {self.learner.get_win_rate():.1%}")

        return {"type": "ACK", "status": "Resultado registrado", "result": result}

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

    de