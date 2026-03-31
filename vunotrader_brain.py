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
import csv
import urllib.request
import urllib.error
import urllib.parse
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

from vuno_core import (
    DecisionEngine,
    DecisionRuntimeConfig,
    FeatureBuilder,
    TradingModel,
    generate_bootstrap_market_data,
    load_model_weights,
    save_model_weights,
)

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
    "enable_skill_engine": os.environ.get("ENABLE_SKILL_ENGINE", "0") == "1",
    "skill_engine_url": os.environ.get("SKILL_ENGINE_URL", "").strip(),
    "skill_engine_timeout_sec": float(os.environ.get("SKILL_ENGINE_TIMEOUT_SEC", "1.8")),
    "skill_engine_api_key": os.environ.get("SKILL_ENGINE_API_KEY", "").strip(),
    "enable_global_memory_shadow": os.environ.get("ENABLE_GLOBAL_MEMORY_SHADOW", "1") == "1",
    "global_memory_min_samples": int(os.environ.get("GLOBAL_MEMORY_MIN_SAMPLES", "20")),
    "enable_fin_news": os.environ.get("ENABLE_FIN_NEWS", "1") == "1",
    "fin_news_api_key": os.environ.get("FIN_NEWS_API_KEY", "").strip(),
    "fin_news_api_url_template": os.environ.get(
        "FIN_NEWS_API_URL_TEMPLATE",
        "https://api.apitube.io/v1/news/everything?query={query}&language={language}&limit={limit}",
    ).strip(),
    "fin_news_api_url_templates": os.environ.get("FIN_NEWS_API_URL_TEMPLATES", "").strip(),
    "fin_news_timeout_sec": float(os.environ.get("FIN_NEWS_TIMEOUT_SEC", "3.0")),
    "fin_news_cache_sec": int(os.environ.get("FIN_NEWS_CACHE_SEC", "120")),
    "fin_news_language": os.environ.get("FIN_NEWS_LANGUAGE", "pt").strip() or "pt",
    "fin_news_min_articles": int(os.environ.get("FIN_NEWS_MIN_ARTICLES", "3")),
    "fin_news_mode": os.environ.get("FIN_NEWS_MODE", "shadow").strip().lower() or "shadow",
    "fin_news_min_confidence_to_influence": float(os.environ.get("FIN_NEWS_MIN_CONFIDENCE_TO_INFLUENCE", "0.80")),
    "fin_news_conflict_risk_reduction": float(os.environ.get("FIN_NEWS_CONFLICT_RISK_REDUCTION", "0.30")),
    "fin_news_alignment_risk_boost": float(os.environ.get("FIN_NEWS_ALIGNMENT_RISK_BOOST", "0.10")),
    "fin_news_block_on_conflict": os.environ.get("FIN_NEWS_BLOCK_ON_CONFLICT", "0") == "1",
    "fin_news_block_confidence": float(os.environ.get("FIN_NEWS_BLOCK_CONFIDENCE", "0.92")),
}


class FinancialNewsAnalyzer:
    """
    Camada opcional de noticias para modular risco/sinal do motor.
    Nao substitui o modelo tecnico; apenas adiciona contexto macro em tempo real.
    """

    _POSITIVE_TERMS = {
        "alta", "bull", "bullish", "otimismo", "otimista", "subida", "valorizacao",
        "crescimento", "acordo", "aprova", "estavel", "recovery", "recuperacao",
    }
    _NEGATIVE_TERMS = {
        "queda", "bear", "bearish", "pessimismo", "pessimista", "crise", "guerra",
        "recessao", "recessão", "inflacao", "inflação", "hawkish", "aperto", "risco",
        "selloff", "desaceleracao", "desaceleração", "stress", "estresse",
    }

    def __init__(self):
        self.enabled = bool(CONFIG.get("enable_fin_news")) and bool(CONFIG.get("fin_news_api_key"))
        self.mode = str(CONFIG.get("fin_news_mode") or "shadow").strip().lower()
        self.api_key = str(CONFIG.get("fin_news_api_key") or "")
        self.url_template = str(CONFIG.get("fin_news_api_url_template") or "")
        raw_templates = str(CONFIG.get("fin_news_api_url_templates") or "")
        self.timeout_sec = float(CONFIG.get("fin_news_timeout_sec") or 3.0)
        self.cache_sec = int(CONFIG.get("fin_news_cache_sec") or 120)
        self.language = str(CONFIG.get("fin_news_language") or "pt")
        self.min_articles = int(CONFIG.get("fin_news_min_articles") or 3)
        self.min_confidence_to_influence = float(CONFIG.get("fin_news_min_confidence_to_influence") or 0.80)
        self.conflict_risk_reduction = max(0.0, min(1.0, float(CONFIG.get("fin_news_conflict_risk_reduction") or 0.30)))
        self.alignment_risk_boost = max(0.0, min(1.0, float(CONFIG.get("fin_news_alignment_risk_boost") or 0.10)))
        self.block_on_conflict = bool(CONFIG.get("fin_news_block_on_conflict", False))
        self.block_confidence = float(CONFIG.get("fin_news_block_confidence") or 0.92)
        self._cache: dict[tuple[str, str], tuple[float, dict]] = {}

        if self.mode not in {"off", "shadow", "assist"}:
            self.mode = "shadow"

        if raw_templates:
            self.url_templates = [u.strip() for u in raw_templates.split(",") if u.strip()]
        else:
            self.url_templates = [
                self.url_template,
                "https://api.apitube.io/v1/news/everything?query={query}&language={language}&limit={limit}",
                "https://api.apitube.io/v1/news/everything?q={query}&language={language}&limit={limit}",
                "https://api.apitube.io/v1/news?query={query}&language={language}&limit={limit}",
                "https://api.apitube.io/v1/news?q={query}&language={language}&limit={limit}",
            ]

        if self.enabled:
            log.info("Leitor de noticias financeiras habilitado | mode=%s", self.mode)
        else:
            log.info("Leitor de noticias financeiras desabilitado (sem chave ou flag).")

    @staticmethod
    def _normalize_text(value: str) -> str:
        return re.sub(r"\s+", " ", (value or "").strip().lower())

    def _build_url(self, template: str, symbol: str, timeframe: str, limit: int = 20) -> str:
        query = f"{symbol} forex OR economia OR juros OR inflacao OR inflação OR fed OR ecb"
        encoded_query = urllib.parse.quote(query)
        return (
            template
            .replace("{symbol}", urllib.parse.quote(symbol))
            .replace("{timeframe}", urllib.parse.quote(timeframe))
            .replace("{query}", encoded_query)
            .replace("{language}", urllib.parse.quote(self.language))
            .replace("{limit}", str(limit))
        )

    @staticmethod
    def _extract_articles(payload: dict) -> list[dict]:
        for key in ("articles", "news", "results", "items", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict):
                for sub_key in ("articles", "news", "results", "items"):
                    sub_val = value.get(sub_key)
                    if isinstance(sub_val, list):
                        return [x for x in sub_val if isinstance(x, dict)]
        return []

    def _score_article(self, article: dict) -> float:
        text = self._normalize_text(
            " ".join([
                str(article.get("title") or ""),
                str(article.get("description") or ""),
                str(article.get("summary") or ""),
            ])
        )
        if not text:
            return 0.0

        pos_hits = sum(1 for term in self._POSITIVE_TERMS if term in text)
        neg_hits = sum(1 for term in self._NEGATIVE_TERMS if term in text)
        raw = float(pos_hits - neg_hits)
        # Clampeia para reduzir impacto de manchetes extremas isoladas.
        return max(-3.0, min(3.0, raw)) / 3.0

    def _fetch(self, symbol: str, timeframe: str) -> dict:
        if not self.enabled:
            return {
                "enabled": False,
                "bias": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "reason": "news_disabled",
            }

        cache_key = (symbol.upper(), timeframe.upper())
        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and (now - cached[0]) <= self.cache_sec:
            return cached[1]

        headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "VunoTrader-Brain/2.0",
        }
        raw = ""
        last_error_reason = "fetch_error"
        for template in self.url_templates:
            req = urllib.request.Request(self._build_url(template, symbol, timeframe), headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore").strip()
                    last_error_reason = "ok"
                    break
            except urllib.error.HTTPError as e:
                # 404 pode significar rota diferente; tenta proxima alternativa.
                last_error_reason = f"http_{e.code}"
                if e.code != 404:
                    log.warning("[News] HTTP %s ao buscar noticias para %s", e.code, symbol)
            except Exception as e:
                last_error_reason = "fetch_error"
                log.debug("[News] Falha ao buscar noticias para %s: %s", symbol, e)

        if not raw:
            result = {
                "enabled": True,
                "bias": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "reason": last_error_reason,
            }
            self._cache[cache_key] = (now, result)
            return result

        try:
            payload = json.loads(raw) if raw else {}
        except Exception:
            payload = {}

        articles = self._extract_articles(payload)
        if len(articles) < self.min_articles:
            result = {
                "enabled": True,
                "bias": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "sample_size": len(articles),
                "reason": "low_sample",
            }
            self._cache[cache_key] = (now, result)
            return result

        scores = [self._score_article(a) for a in articles[:30]]
        mean_score = float(np.mean(scores)) if scores else 0.0
        score_abs = abs(mean_score)

        if mean_score >= 0.25:
            bias = "buy"
        elif mean_score <= -0.25:
            bias = "sell"
        else:
            bias = "neutral"

        confidence = min(1.0, score_abs * 1.35)
        result = {
            "enabled": True,
            "bias": bias,
            "score": round(mean_score, 4),
            "confidence": round(confidence, 4),
            "sample_size": len(scores),
            "reason": "ok",
        }
        self._cache[cache_key] = (now, result)
        return result

    def _build_candidate_prediction(self, baseline: dict, news: dict) -> tuple[dict, str, dict]:
        """
        Constrói uma decisao candidata com noticias sem alterar baseline.
        A aplicacao real depende de mode=assist e threshold de confianca.
        """
        candidate = dict(baseline)
        signal = str(candidate.get("signal") or "HOLD").upper()
        risk = float(candidate.get("risk", 0) or 0)
        bias = str(news.get("bias") or "neutral")
        strength = float(news.get("confidence", 0) or 0)

        meta = {
            "base_signal": signal,
            "base_risk": risk,
            "candidate_signal": signal,
            "candidate_risk": risk,
            "changed": False,
            "can_influence": False,
            "alignment": "neutral",
        }

        if signal not in {"BUY", "SELL"} or not news.get("enabled"):
            return candidate, "NEWS:inactive", meta

        aligns = (signal == "BUY" and bias == "buy") or (signal == "SELL" and bias == "sell")
        opposes = (signal == "BUY" and bias == "sell") or (signal == "SELL" and bias == "buy")

        if strength < self.min_confidence_to_influence or bias == "neutral":
            return candidate, f"NEWS:low_conf;bias={bias};c={strength:.2f}", meta

        meta["can_influence"] = True
        if aligns:
            new_risk = min(float(CONFIG.get("risk_max", 4.0)), risk * (1.0 + self.alignment_risk_boost))
            candidate["risk"] = round(new_risk, 3)
            meta["alignment"] = "align"
            note = f"NEWS:align;bias={bias};c={strength:.2f}"
        elif opposes:
            if self.block_on_conflict and strength >= self.block_confidence:
                candidate["signal"] = "HOLD"
                candidate["risk"] = 0.0
                note = f"NEWS:block;bias={bias};c={strength:.2f}"
            else:
                factor = max(0.0, 1.0 - self.conflict_risk_reduction)
                candidate["risk"] = round(max(0.0, risk * factor), 3)
                note = f"NEWS:oppose;bias={bias};c={strength:.2f}"
            meta["alignment"] = "oppose"
        else:
            note = f"NEWS:neutral;bias={bias};c={strength:.2f}"

        meta["candidate_signal"] = str(candidate.get("signal") or signal).upper()
        meta["candidate_risk"] = float(candidate.get("risk", risk) or 0)
        meta["changed"] = (
            meta["candidate_signal"] != meta["base_signal"]
            or abs(meta["candidate_risk"] - float(meta["base_risk"])) > 1e-9
        )
        return candidate, note, meta

    def apply_to_prediction(self, prediction: dict, symbol: str, timeframe: str) -> tuple[dict, str, dict, dict]:
        news = self._fetch(symbol, timeframe)
        baseline = dict(prediction)
        candidate, candidate_note, candidate_meta = self._build_candidate_prediction(baseline, news)

        mode = self.mode
        applied = False
        effective = dict(baseline)

        if mode == "assist" and candidate_meta.get("can_influence"):
            effective = dict(candidate)
            applied = bool(candidate_meta.get("changed"))

        note = (
            f"NEWS:mode={mode};applied={1 if applied else 0};"
            f"base={candidate_meta.get('base_signal','HOLD')}/{float(candidate_meta.get('base_risk',0.0)):.2f};"
            f"cand={candidate_meta.get('candidate_signal','HOLD')}/{float(candidate_meta.get('candidate_risk',0.0)):.2f};"
            f"reason={candidate_note}"
        )

        shadow = {
            "mode": mode,
            "execution_changed": bool(applied and candidate_meta.get("changed")),
            "baseline_signal": str(candidate_meta.get("base_signal", "HOLD")),
            "baseline_risk": float(candidate_meta.get("base_risk", 0.0) or 0.0),
            "candidate_signal": str(candidate_meta.get("candidate_signal", "HOLD")),
            "candidate_risk": float(candidate_meta.get("candidate_risk", 0.0) or 0.0),
            "candidate_changed": bool(candidate_meta.get("changed", False)),
            "can_influence": bool(candidate_meta.get("can_influence", False)),
            "alignment": str(candidate_meta.get("alignment", "neutral")),
        }

        return effective, note, news, shadow


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

        # Compatibilidade: a UI de instalação entrega auth_user_id no campo UserID,
        # mas robot_instances referencia profile_id. Resolvemos profile_id aqui.
        resolved_profile_id = user_profile_id
        try:
            prof = (
                self._client.table("user_profiles")
                .select("id")
                .eq("auth_user_id", user_profile_id)
                .limit(1)
                .maybe_single()
                .execute()
            )
            prof_row = prof.data or None
            if prof_row and prof_row.get("id"):
                resolved_profile_id = str(prof_row.get("id"))
        except Exception as e:
            log.debug("[Supabase] Falha ao resolver profile_id por auth_user_id: %s", e)

        token_hash = hashlib.sha256(robot_token.encode("utf-8")).hexdigest()

        try:
            resp = (
                self._client.table("robot_instances")
                .select("id, status, profile_id, organization_id, robot_token_hash, allowed_modes, real_trading_enabled, max_risk_real")
                .eq("id", robot_instance_id)
                .eq("organization_id", organization_id)
                .eq("profile_id", resolved_profile_id)
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

        defaults = {
            "max_consecutive_losses": 3,
            "drawdown_pause_pct": 5.0,
            "auto_reduce_risk": True,
            "capital_usd": 10000.0,
            "per_trade_stop_loss_mode": "atr",
            "per_trade_stop_loss_value": 2.0,
            "per_trade_take_profit_rr": 2.0,
        }
        if not self.active:
            return defaults
        try:
            res = self._client.table("user_parameters").select(
                "max_consecutive_losses, drawdown_pause_pct, auto_reduce_risk, capital_usd, per_trade_stop_loss_mode, per_trade_stop_loss_value, per_trade_take_profit_rr"
            ).eq("user_id", user_id).limit(1).maybe_single().execute()
            if res.data:
                merged = {**defaults, **{k: v for k, v in res.data.items() if v is not None}}
                self._risk_params_cache[user_id] = (merged, now + 300)
                return merged
        except Exception as e:
            log.debug(f"[Supabase] get_risk_params falhou: {e}")
        self._risk_params_cache[user_id] = (defaults, now + 60)
        return defaults

    def get_global_memory_best(
        self,
        symbol: str,
        timeframe: str,
        regime: str,
        mode: str,
        min_samples: int = 20,
    ) -> dict | None:
        """
        Busca a melhor recomendacao global agregada para o contexto atual.
        Usado apenas em shadow mode (nao altera execucao).
        """
        if not self.active:
            return None
        try:
            res = (
                self._client.table("global_memory_signals")
                .select("side, sample_size, win_rate, avg_pnl_points, avg_confidence, avg_risk_pct, computed_at")
                .eq("symbol", str(symbol or "").upper())
                .eq("timeframe", str(timeframe or "").upper())
                .eq("regime", str(regime or "").lower())
                .eq("mode", str(mode or "demo").lower())
                .in_("side", ["buy", "sell"])
                .gte("sample_size", int(min_samples))
                .limit(100)
                .execute()
            )
            rows = list(res.data or [])
            if not rows:
                return None

            def _score(row: dict) -> float:
                wr = float(row.get("win_rate") or 0)
                n = int(row.get("sample_size") or 0)
                # Prioriza win_rate sem ignorar robustez amostral.
                return wr * min(1.0, (n / 100.0) ** 0.5)

            best = sorted(rows, key=_score, reverse=True)[0]
            return {
                "side": str(best.get("side") or "").upper(),
                "sample_size": int(best.get("sample_size") or 0),
                "win_rate": float(best.get("win_rate") or 0),
                "avg_pnl_points": float(best.get("avg_pnl_points") or 0),
                "avg_confidence": float(best.get("avg_confidence") or 0),
                "avg_risk_pct": float(best.get("avg_risk_pct") or 0),
                "computed_at": str(best.get("computed_at") or ""),
            }
        except Exception as e:
            log.debug(f"[Supabase] get_global_memory_best falhou: {e}")
            return None


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


class SkillEngineBridge:
    """
    Camada opcional para integrar um Skill Engine externo no ciclo do brain.
    Fluxo:
    1) pre_trade: valida/governa a sugestao do ML antes de executar
    2) post_trade: recebe feedback do resultado para aprendizado cruzado
    """

    def __init__(self):
        self.enabled = bool(CONFIG.get("enable_skill_engine")) and bool(CONFIG.get("skill_engine_url"))
        self.url = str(CONFIG.get("skill_engine_url") or "")
        self.timeout = float(CONFIG.get("skill_engine_timeout_sec") or 1.8)
        self.api_key = str(CONFIG.get("skill_engine_api_key") or "")

        if self.enabled:
            log.info("Skill Engine bridge habilitada: %s", self.url)
        else:
            log.info("Skill Engine bridge desabilitada. Usando apenas governanca local.")

    def _post(self, endpoint: str, payload: dict) -> dict | None:
        if not self.enabled or not self.url:
            return None

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        base_url = self.url.rstrip("/")
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        req = urllib.request.Request(
            f"{base_url}{path}",
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="ignore").strip()
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            log.warning("[SkillEngine] HTTP %s em %s", e.code, endpoint)
            return None
        except Exception as e:
            log.debug("[SkillEngine] Falha em %s: %s", endpoint, e)
            return None

    def evaluate_pre_trade(self, payload: dict) -> dict:
        """
        Retorna decisao de governanca:
        - allow: segue com o sinal do ML
        - block: bloqueia e converte para HOLD
        - review: exige revisao humana antes de entrar
        - override: ajusta sinal/risco com base no Skill Engine
        """
        default = {"decision": "allow", "reason": "Governanca local apenas"}
        data = self._post("/pre-trade", payload)
        if not isinstance(data, dict):
            return default

        decision = str(data.get("decision", "allow") or "allow").strip().lower()
        if decision not in {"allow", "block", "review", "override"}:
            decision = "allow"

        response = {
            "decision": decision,
            "reason": str(data.get("reason") or ""),
            "override_signal": str(data.get("override_signal") or "").upper() or None,
            "override_risk_pct": data.get("override_risk_pct"),
            "requires_human": bool(data.get("requires_human", False)),
            "meta": data.get("meta") if isinstance(data.get("meta"), dict) else {},
        }
        return response

    def report_trade_result(self, payload: dict) -> None:
        """Entrega feedback de execucao ao Skill Engine (best effort)."""
        _ = self._post("/post-trade", payload)


# ─── Servidor Socket (comunicação com MT5) ───────────────────────
class MT5Bridge:
    """
    Servidor TCP que recebe dados do MT5 e envia sinais de volta
    Protocolo: JSON via socket TCP na porta 9999
    """

    def __init__(self, host: str, port: int, model: TradingModel,
                 engine: DecisionEngine, learner: LearningManager, db: SupabaseLogger,
                 skill_engine: SkillEngineBridge, news_analyzer: FinancialNewsAnalyzer):
        self.host    = host
        self.port    = port
        self.model   = model
        self.engine  = engine
        self.learner = learner
        self.db      = db
        self.skill_engine = skill_engine
        self.news_analyzer = news_analyzer
        self.server  = None
        self.running = False
        self.last_df = None
        # Mapa ticket → (decision_id, executed_trade_id) para fechar depois
        self._open_trades: dict[str, tuple[str | None, str | None]] = {}
        # Contador de perdas consecutivas por robot_id (reset ao vencer)
        self._consec_losses: dict[str, int] = {}
        # Avaliação de impacto de notícias por decision_id para fechar no TRADE_RESULT.
        self._news_shadow_by_decision: dict[str, dict] = {}

    def _append_news_shadow_log(self, row: dict) -> None:
        """Persistência leve local para comparar baseline vs news após resultado real."""
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_shadow_eval.csv")
            file_exists = os.path.exists(path)
            with open(path, "a", newline="", encoding="utf-8") as f:
                fields = [
                    "timestamp", "decision_id", "symbol", "timeframe", "mode",
                    "baseline_signal", "candidate_signal", "effective_signal",
                    "baseline_risk", "candidate_risk", "effective_risk",
                    "news_bias", "news_confidence", "news_sample_size",
                    "alignment", "can_influence", "execution_changed",
                    "outcome", "pnl_money", "pnl_points",
                ]
                writer = csv.DictWriter(f, fieldnames=fields)
                if not file_exists:
                    writer.writeheader()
                writer.writerow({k: row.get(k) for k in fields})
        except Exception as e:
            log.debug("Falha ao gravar news_shadow_eval.csv: %s", e)

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

            win_rate = self.learner.get_win_rate()
            analysis = self.engine.analyze_market(
                df,
                win_rate=win_rate,
                mode=mode,
                max_risk_real=max_risk_real,
            )
            prediction = {
                "signal": analysis["signal"],
                "confidence": analysis["confidence"],
                "risk": analysis["risk"],
                "prob_buy": analysis.get("prob_buy", 0.0),
                "prob_sell": analysis.get("prob_sell", 0.0),
                "rationale": analysis.get("rationale", ""),
            }
            regime = analysis.get("regime", "lateral")
            rationale = analysis.get("rationale", "")
            atr_pct = float(analysis.get("atr_pct", 0) or 0)
            feature_snapshot = analysis.get("feature_snapshot") or {}

            # Camada de contexto macro: noticias financeiras (best effort).
            prediction, news_note, news_context, news_shadow = self.news_analyzer.apply_to_prediction(
                prediction,
                symbol=symbol,
                timeframe=timeframe,
            )
            if news_note:
                rationale = f"{rationale} | {news_note}"

            # Integracao opcional: Skill Engine valida/ajusta a proposta do ML
            governance = self.skill_engine.evaluate_pre_trade({
                "symbol": symbol,
                "timeframe": timeframe,
                "mode": mode,
                "user_id": user_id,
                "organization_id": org_id,
                "robot_id": robot_id,
                "ml_signal": prediction.get("signal"),
                "ml_confidence": float(prediction.get("confidence", 0) or 0),
                "ml_risk_pct": float(prediction.get("risk", 0) or 0),
                "regime": regime,
                "win_rate": float(win_rate),
                "features": feature_snapshot,
                "news": news_context,
            })

            gov_decision = str(governance.get("decision", "allow") or "allow").lower()
            gov_reason = str(governance.get("reason", "") or "").strip()
            override_signal = str(governance.get("override_signal") or "").upper().strip()
            override_risk = governance.get("override_risk_pct")

            if gov_decision in {"block", "review"}:
                prediction["signal"] = "HOLD"
                prediction["risk"] = 0.0
                prediction["governance_hold"] = True
            elif gov_decision == "override":
                if override_signal in {"BUY", "SELL", "HOLD"}:
                    prediction["signal"] = override_signal
                if override_risk is not None:
                    try:
                        prediction["risk"] = max(0.0, float(override_risk))
                    except (TypeError, ValueError):
                        pass

            if gov_reason:
                rationale = f"{rationale} | GOV: {gov_reason}"

            # Shadow mode: compara decisao local com memoria global sem alterar execucao.
            shadow_data = None
            if CONFIG.get("enable_global_memory_shadow"):
                local_signal = str(prediction.get("signal") or "HOLD").upper()
                global_best = self.db.get_global_memory_best(
                    symbol=symbol,
                    timeframe=timeframe,
                    regime=regime,
                    mode=mode,
                    min_samples=int(CONFIG.get("global_memory_min_samples") or 20),
                )
                if global_best:
                    local_side = local_signal if local_signal in {"BUY", "SELL"} else None
                    global_side = str(global_best.get("side") or "").upper()
                    agreement = bool(local_side and local_side == global_side)
                    shadow_data = {
                        "enabled": True,
                        "local_signal": local_signal,
                        "global_recommendation": global_best,
                        "agreement": agreement,
                        "execution_changed": False,
                    }
                    # Marcador compacto para auditoria web sem mudar schema.
                    rationale = (
                        f"{rationale} | SHADOW:"
                        f"{('agree' if agreement else 'diverge')}"
                        f";global={global_side}"
                        f";wr={float(global_best.get('win_rate', 0))*100:.1f}%"
                        f";n={int(global_best.get('sample_size', 0))}"
                    )

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
                "action":      prediction['signal'].lower(),
                "win_rate":    round(win_rate, 4),
                "regime":      regime,
                "rationale":   rationale,
                "timestamp":   datetime.now().isoformat(),
                "decision_id": decision_id,
                "governance": {
                    "decision": gov_decision,
                    "reason": gov_reason,
                    "requires_human": bool(governance.get("requires_human", False) or gov_decision == "review"),
                },
            }

            if decision_id and news_shadow:
                self._news_shadow_by_decision[decision_id] = {
                    "timestamp": datetime.now().isoformat(),
                    "decision_id": decision_id,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "mode": mode,
                    "baseline_signal": str(news_shadow.get("baseline_signal", "HOLD")),
                    "candidate_signal": str(news_shadow.get("candidate_signal", "HOLD")),
                    "effective_signal": str(prediction.get("signal", "HOLD")),
                    "baseline_risk": float(news_shadow.get("baseline_risk", 0.0) or 0.0),
                    "candidate_risk": float(news_shadow.get("candidate_risk", 0.0) or 0.0),
                    "effective_risk": float(prediction.get("risk", 0.0) or 0.0),
                    "news_bias": str(news_context.get("bias", "neutral")) if news_context else "neutral",
                    "news_confidence": float(news_context.get("confidence", 0.0) or 0.0) if news_context else 0.0,
                    "news_sample_size": int(news_context.get("sample_size", 0) or 0) if news_context else 0,
                    "alignment": str(news_shadow.get("alignment", "neutral")),
                    "can_influence": int(bool(news_shadow.get("can_influence", False))),
                    "execution_changed": int(bool(news_shadow.get("execution_changed", False))),
                }

            if shadow_data:
                response["shadow_global"] = shadow_data

            if news_context:
                response["news_context"] = {
                    "enabled": bool(news_context.get("enabled", False)),
                    "mode": str(news_shadow.get("mode", "shadow")) if news_shadow else "shadow",
                    "bias": str(news_context.get("bias", "neutral")),
                    "score": float(news_context.get("score", 0.0) or 0.0),
                    "confidence": float(news_context.get("confidence", 0.0) or 0.0),
                    "sample_size": int(news_context.get("sample_size", 0) or 0),
                }

            if news_shadow:
                response["news_shadow"] = news_shadow

            if prediction.get("governance_hold"):
                response["paused"] = True
                response["paused_reason"] = "governance"

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

        if decision_id:
            shadow_row = self._news_shadow_by_decision.pop(decision_id, None)
            if shadow_row:
                shadow_row["outcome"] = result.lower()
                shadow_row["pnl_money"] = float(profit)
                shadow_row["pnl_points"] = float(points)
                self._append_news_shadow_log(shadow_row)

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

        # Integração cruzada: devolve outcome para o Skill Engine (best effort)
        self.skill_engine.report_trade_result({
            "decision_id": decision_id,
            "ticket": ticket,
            "user_id": user_id,
            "organization_id": org_id,
            "robot_id": robot_id,
            "mode": mode_trade,
            "symbol": symbol_trade,
            "timeframe": str(msg.get("timeframe", "") or ""),
            "result": result.lower(),
            "pnl_money": float(profit),
            "pnl_points": float(points),
            "confidence": float(msg.get("confidence", 0) or 0),
            "risk_pct": float(msg.get("risk_pct", 0) or 0),
            "regime": str(msg.get("regime", "") or ""),
            "features": _build_feature_snapshot(msg),
        })

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
        return generate_bootstrap_market_data(n)

    def run(self, interval: int):
        while True:
            log.info("Iniciando retreino do modelo...")
            df = self.generate_sample_data(CONFIG['lookback_candles'])
            if self.model.train(df):
                save_model_weights(self.model)
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
    runtime = DecisionRuntimeConfig(
        min_confidence=float(CONFIG["min_confidence"]),
        risk_base=float(CONFIG["risk_base"]),
        risk_max=float(CONFIG["risk_max"]),
        risk_min=float(CONFIG["risk_min"]),
    )
    model   = TradingModel(runtime)
    engine  = DecisionEngine(model, runtime)
    learner = LearningManager(CONFIG['history_file'])
    learner.load()
    db      = SupabaseLogger()
    skill_engine = SkillEngineBridge()
    news_analyzer = FinancialNewsAnalyzer()

    # Carregar pesos existentes; se não houver, faz bootstrap e salva
    scheduler = RetrainScheduler(model, learner)
    loaded = load_model_weights(model)
    if loaded:
        log.info("Pesos do modelo carregados de disco (brain_model_rf.pkl / brain_model_gb.pkl)")
    else:
        df_inicial = scheduler.generate_sample_data(CONFIG['lookback_candles'])
        model.train(df_inicial)
        save_model_weights(model)

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
        engine,
        learner,
        db,
        skill_engine,
        news_analyzer,
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
