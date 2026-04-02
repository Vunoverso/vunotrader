"""
retrain_pipeline.py
===================
Pipeline de retreino supervisionado do Vuno Brain.

Fluxo:
  1. Lê `anonymized_trade_events` do Supabase (últimos N dias)
  2. Filtra eventos com resultado known (win/loss)
  3. Reconstrói features a partir das colunas disponíveis
  4. Treina RF + GB sobre os dados históricos
  5. Avalia acurácia e salva métricas em `model_metrics` (se a tabela existir)
  6. Persiste modelo em disco (brain_model_rf.pkl / brain_model_gb.pkl)
  7. Pode ser executado standalone ou importado por RetrainScheduler

Uso:
    python retrain_pipeline.py [--days 30] [--min-samples 100] [--dry-run]

Variáveis de ambiente:
    SUPABASE_URL             Obrigatório
    SUPABASE_SERVICE_ROLE_KEY  Obrigatório
"""

import argparse
import hashlib
import json
import logging
import os
import pickle
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("retrain_pipeline")

# ────────────────────────────────────────────────────────────────
# Caminhos dos modelos (alinhados com vunotrader_brain.py)
# ────────────────────────────────────────────────────────────────
_BASE_DIR  = Path(__file__).parent
MODEL_RF   = _BASE_DIR / "brain_model_rf.pkl"
MODEL_GB   = _BASE_DIR / "brain_model_gb.pkl"
MODEL_SCALER = _BASE_DIR / "brain_model_scaler.pkl"
LOCAL_CYCLE_LOG_CSV = _BASE_DIR / "scanner_cycle_logs.csv"

# ────────────────────────────────────────────────────────────────
# Constantes
# ────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "rsi", "macd", "macd_signal", "macd_hist",
    "bb_width", "bb_pos", "atr_pct",
    "momentum_5", "momentum_10", "momentum_20",
    "volume_ratio",
    "cross_9_21", "cross_21_50", "cross_50_200",
    "dist_ema9", "dist_ema21", "dist_ema50",
]

# Colunas presentes em anonymized_trade_events / scanner_cycle_logs que mapeiam para features parciais
EVENT_NUMERIC_COLS = [
    "confidence", "risk_pct", "pnl_points", "volatility",
    "score", "atr_pct", "volume_ratio", "rsi", "momentum_20",
]

LABEL_MAP = {"win": 1, "loss": 0, "breakeven": 0}


# ────────────────────────────────────────────────────────────────
# Supabase — cliente mínimo via REST
# ────────────────────────────────────────────────────────────────
def _make_supabase_client():
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log.warning("Supabase não configurado. Pipeline seguirá apenas com fontes locais, se existirem.")
        return None

    try:
        from supabase import create_client  # type: ignore
        return create_client(url, key)
    except ImportError:
        log.warning("Pacote supabase não instalado. Pipeline seguirá apenas com fontes locais.")
        return None


# ────────────────────────────────────────────────────────────────
# 1. Extração de dados
# ────────────────────────────────────────────────────────────────
def fetch_events(client, days: int = 30) -> pd.DataFrame:
    """
    Busca anonymized_trade_events dos últimos `days` dias.
    Retorna DataFrame com todos os campos disponíveis.
    """
    if client is None:
        return pd.DataFrame()

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    log.info(f"Buscando eventos desde {since[:10]} (últimos {days} dias)…")
    try:
        resp = (
            client.table("anonymized_trade_events")
            .select(
                "id, mode, symbol, timeframe, side, confidence, "
                "risk_pct, result, pnl_points, regime, volatility, created_at"
            )
            .gte("created_at", since)
            .order("created_at")
            .limit(50_000)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        log.error(f"Falha ao buscar eventos: {exc}")
        return pd.DataFrame()

    if not rows:
        log.warning("Nenhum evento encontrado no período.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    log.info(f"  → {len(df)} eventos carregados. Colunas: {list(df.columns)}")
    return df


def fetch_cycle_logs(client, days: int = 30) -> pd.DataFrame:
    """
    Busca scanner_cycle_logs fechados dos últimos `days` dias.
    Usa apenas ciclos executados e encerrados com outcome conhecido.
    """
    if client is None:
        return pd.DataFrame()

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    log.info(f"Buscando ciclos fechados desde {since[:10]} (últimos {days} dias)...")
    try:
        resp = (
            client.table("scanner_cycle_logs")
            .select(
                "id, mode, symbol, timeframe, signal, confidence, risk_pct, result, "
                "pnl_points, regime, score, atr_pct, volume_ratio, rsi, momentum_20, cycle_ts"
            )
            .gte("cycle_ts", since)
            .eq("decision_status", "closed")
            .eq("executed", True)
            .order("cycle_ts")
            .limit(50_000)
            .execute()
        )
        rows = resp.data or []
    except Exception as exc:
        log.warning(f"scanner_cycle_logs indisponível ou não acessível: {exc}")
        return pd.DataFrame()

    if not rows:
        log.info("Nenhum ciclo fechado encontrado no período.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.rename(columns={"signal": "side", "cycle_ts": "created_at"})
    log.info(f"  → {len(df)} ciclos fechados carregados. Colunas: {list(df.columns)}")
    return df


def fetch_local_cycle_logs(days: int = 30) -> pd.DataFrame:
    """
    Busca ciclos fechados no CSV local gerado pelo CycleCollector.
    Útil para aprendizagem shadow antes da persistência remota.
    """
    if not LOCAL_CYCLE_LOG_CSV.exists():
        log.info("CSV local de ciclos não encontrado.")
        return pd.DataFrame()

    try:
        df = pd.read_csv(LOCAL_CYCLE_LOG_CSV)
    except Exception as exc:
        log.warning(f"Falha ao ler CSV local de ciclos: {exc}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    if "cycle_ts" not in df.columns:
        log.warning("CSV local de ciclos sem coluna cycle_ts.")
        return pd.DataFrame()

    df["cycle_ts"] = pd.to_datetime(df["cycle_ts"], utc=True, errors="coerce")
    since = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    df = df[df["cycle_ts"] >= since].copy()
    if df.empty:
        return pd.DataFrame()

    if "decision_status" not in df.columns or "executed" not in df.columns:
        log.warning("CSV local de ciclos sem colunas decision_status/executed.")
        return pd.DataFrame()

    df = df[(df["decision_status"] == "closed") & (df["executed"] == True)].copy()
    if df.empty:
        return pd.DataFrame()

    df = df.rename(columns={"signal": "side", "cycle_ts": "created_at", "risk": "risk_pct"})
    log.info(f"  → {len(df)} ciclos fechados carregados do CSV local.")
    return df


# ────────────────────────────────────────────────────────────────
# 2. Preparação de features
# ────────────────────────────────────────────────────────────────
def _encode_categorical(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encoda colunas categóricas presentes no dataset."""
    df = df.copy()

    for col, categories in [
        ("side",      ["buy", "sell"]),
        ("regime",    ["tendencia", "lateral", "volatil"]),
        ("timeframe", ["M1", "M5", "M15", "M30", "H1", "H4"]),
        ("mode",      ["observer", "demo", "real"]),
    ]:
        if col in df.columns:
            for cat in categories:
                df[f"{col}_{cat}"] = (df[col] == cat).astype(float)
            df.drop(columns=[col], inplace=True, errors="ignore")

    return df


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Constrói X (features) e y (labels) do DataFrame de eventos.

    Como anonymized_trade_events não armazena as features técnicas brutas,
    usamos as colunas disponíveis (confidence, risk_pct, pnl_points,
    volatility) + encodings de side/regime/timeframe/mode como proxy.

    Quando o brain for atualizado para persistir feature_snapshot em
    anonymized_trade_events, basta adicionar as colunas aqui.
    """
    df = df.copy()

    # Remove linhas sem resultado
    df = df[df["result"].isin(LABEL_MAP.keys())].copy()
    if df.empty:
        return pd.DataFrame(), pd.Series(dtype=int)

    y = df["result"].map(LABEL_MAP).astype(int)
    df.drop(columns=["result", "id", "created_at",
                     "source_trade_decision_id", "source_trade_outcome_id",
                     "anonymous_user_hash", "anonymous_org_hash"],
            errors="ignore", inplace=True)

    df = _encode_categorical(df)

    # Garante que colunas numéricas sejam float
    for col in EVENT_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Descarta colunas de string restantes
    df = df.select_dtypes(include=[np.number])

    log.info(f"  Features finais: {list(df.columns)} ({len(df)} amostras)")
    return df, y


# ────────────────────────────────────────────────────────────────
# 3. Retreino
# ────────────────────────────────────────────────────────────────
def retrain(X: pd.DataFrame, y: pd.Series) -> dict[str, Any]:
    """
    Treina RF + GB com validação cruzada simples (80/20 split).
    Retorna dict com métricas e os modelos treinados.
    """
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    log.info(f"Treinando com {len(X)} amostras ({y.sum()} wins / {(y == 0).sum()} losses)…")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=6, min_samples_leaf=4,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    gb = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42
    )

    scaler = StandardScaler()
    X_tr_scaled = scaler.fit_transform(X_tr)
    X_te_scaled = scaler.transform(X_te)

    rf.fit(X_tr_scaled, y_tr)
    gb.fit(X_tr_scaled, y_tr)

    rf_preds = rf.predict(X_te_scaled)
    gb_preds = gb.predict(X_te_scaled)

    # Ensemble simples: média das probabilidades
    rf_proba = rf.predict_proba(X_te_scaled)[:, 1]
    gb_proba = gb.predict_proba(X_te_scaled)[:, 1]
    ens_preds = ((rf_proba + gb_proba) / 2 >= 0.5).astype(int)

    metrics = {
        "n_samples":        len(X),
        "n_train":          len(X_tr),
        "n_test":           len(X_te),
        "win_rate_train":   float(y_tr.mean()),
        "win_rate_test":    float(y_te.mean()),
        "rf_accuracy":      float(accuracy_score(y_te, rf_preds)),
        "gb_accuracy":      float(accuracy_score(y_te, gb_preds)),
        "ensemble_accuracy": float(accuracy_score(y_te, ens_preds)),
        "features":         list(X.columns),
        "trained_at":       datetime.now(timezone.utc).isoformat(),
    }

    log.info("  RF  accuracy: %.3f", metrics["rf_accuracy"])
    log.info("  GB  accuracy: %.3f", metrics["gb_accuracy"])
    log.info("  Ens accuracy: %.3f", metrics["ensemble_accuracy"])

    print(classification_report(y_te, ens_preds, target_names=["loss", "win"], zero_division=0))

    return {"rf": rf, "gb": gb, "scaler": scaler, "metrics": metrics}


# ────────────────────────────────────────────────────────────────
# 4. Persistência
# ────────────────────────────────────────────────────────────────
def save_models(result: dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        log.info("[dry-run] Modelos NÃO foram salvos em disco.")
        return

    with open(MODEL_RF, "wb") as f:
        pickle.dump(result["rf"], f)
    with open(MODEL_GB, "wb") as f:
        pickle.dump(result["gb"], f)
    with open(MODEL_SCALER, "wb") as f:
        pickle.dump(result["scaler"], f)

    log.info(f"Modelos salvos: {MODEL_RF} | {MODEL_GB} | {MODEL_SCALER}")


def save_metrics_to_supabase(
    client, metrics: dict[str, Any], dry_run: bool = False
) -> None:
    """Persiste métricas em model_metrics (ignora se tabela não existir)."""
    if dry_run:
        log.info("[dry-run] Métricas NÃO foram enviadas ao Supabase.")
        log.info("  %s", json.dumps({k: v for k, v in metrics.items() if k != "features"}, indent=2))
        return

    if client is None:
        log.info("Métricas não enviadas: Supabase indisponível nesta execução.")
        return

    try:
        client.table("model_metrics").insert({
            "accuracy_rf":        metrics["rf_accuracy"],
            "accuracy_gb":        metrics["gb_accuracy"],
            "accuracy_ensemble":  metrics["ensemble_accuracy"],
            "n_samples":          metrics["n_samples"],
            "win_rate":           metrics["win_rate_test"],
            "features":           json.dumps(metrics["features"]),
            "trained_at":         metrics["trained_at"],
        }).execute()
        log.info("Métricas salvas em model_metrics.")
    except Exception as exc:
        log.debug(f"Falha ao salvar métricas (tabela pode não existir): {exc}")


# ────────────────────────────────────────────────────────────────
# 5. Entrypoint
# ────────────────────────────────────────────────────────────────
def run_pipeline(days: int = 30, min_samples: int = 100, dry_run: bool = False) -> dict[str, Any] | None:
    """
    Executa o pipeline completo.
    Pode ser chamado por RetrainScheduler ou externamente.
    Retorna o dict de métricas, ou None se dados insuficientes.
    """
    client = _make_supabase_client()

    df_events = fetch_events(client, days=days)
    df_cycles = fetch_cycle_logs(client, days=days)
    df_local_cycles = fetch_local_cycle_logs(days=days)
    frames = [df for df in [df_events, df_cycles, df_local_cycles] if not df.empty]
    if not frames:
        log.warning("Pipeline abortado: nenhum evento disponível.")
        return None

    df = pd.concat(frames, ignore_index=True)
    dedupe_cols = [col for col in ["created_at", "symbol", "timeframe", "side", "result"] if col in df.columns]
    if dedupe_cols:
        df = df.drop_duplicates(subset=dedupe_cols, keep="last")
    log.info(f"Dataset consolidado para treino: {len(df)} linhas.")

    X, y = build_features(df)
    if X.empty:
        log.warning("Pipeline abortado: sem features válidas.")
        return None

    if len(X) < min_samples:
        log.warning(
            f"Pipeline abortado: apenas {len(X)} amostras (mínimo: {min_samples}). "
            "Aguarde mais dados de trade para retreinar."
        )
        return None

    result = retrain(X, y)
    save_models(result, dry_run=dry_run)
    save_metrics_to_supabase(client, result["metrics"], dry_run=dry_run)

    log.info("Pipeline de retreino concluído com sucesso.")
    return result["metrics"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Vuno Brain — Retrain Pipeline")
    parser.add_argument("--days",        type=int,  default=30,  help="Dias de histórico a usar (default: 30)")
    parser.add_argument("--min-samples", type=int,  default=100, help="Mínimo de amostras para treinar (default: 100)")
    parser.add_argument("--dry-run",     action="store_true",    help="Não salva modelos nem grava no Supabase")
    args = parser.parse_args()

    metrics = run_pipeline(days=args.days, min_samples=args.min_samples, dry_run=args.dry_run)
    if metrics is None:
        sys.exit(2)

    print("\nMétricas finais:")
    print(json.dumps({k: v for k, v in metrics.items() if k != "features"}, indent=2))


if __name__ == "__main__":
    main()
