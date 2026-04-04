from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def _safe_json_load(value: object) -> dict:
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_token(value: object, fallback: str = "na") -> str:
    token = str(value or "").strip().lower().replace(" ", "_")
    return token or fallback


def _extract_setup_and_context(snapshot_payload: dict, decision_payload: dict) -> tuple[str, str]:
    analysis = decision_payload.get("analysis") or {}
    signal = str(decision_payload.get("signal") or "HOLD").upper()
    setup_key = _normalize_token(analysis.get("setup") or analysis.get("engine"), "setup")
    timeframe = str(analysis.get("observed_timeframe") or snapshot_payload.get("timeframe") or "NA").upper()
    zone = _normalize_token(analysis.get("zone_type"), "neutral")
    structure = _normalize_token(analysis.get("structure_state") or analysis.get("state"), "neutral")
    fib_state = "fib" if analysis.get("fib_in_retracement_zone") or analysis.get("fib_near_retracement_zone") else "nofib"
    context_key = f"{timeframe}|{setup_key}|{zone}|{structure}|{signal}|{fib_state}"
    return setup_key, context_key


def _empty_context_payload() -> dict[str, object]:
    return {
        "recent_trades": 0.0,
        "recent_win_rate": 0.5,
        "recent_pnl": 0.0,
        "setup_stats": {},
        "context_stats": {},
    }


def _stats_bucket() -> dict[str, float]:
    return {
        "recent_trades": 0.0,
        "wins": 0.0,
        "recent_pnl": 0.0,
    }


def _update_stats_bucket(bucket: dict[str, float], outcome: object, pnl: object) -> None:
    bucket["recent_trades"] += 1.0
    if str(outcome or "").upper() == "WIN":
        bucket["wins"] += 1.0
    try:
        bucket["recent_pnl"] += float(pnl or 0.0)
    except (TypeError, ValueError):
        bucket["recent_pnl"] += 0.0


def _finalize_bucket(bucket: dict[str, float]) -> dict[str, float]:
    trades = float(bucket.get("recent_trades", 0.0))
    wins = float(bucket.get("wins", 0.0))
    pnl = float(bucket.get("recent_pnl", 0.0))
    return {
        "recent_trades": round(trades, 2),
        "recent_win_rate": round((wins / trades) if trades else 0.5, 2),
        "recent_pnl": round(pnl, 2),
    }


class MemoryStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk REAL NOT NULL,
                    snapshot_payload TEXT NOT NULL,
                    decision_payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    pnl REAL NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def record_decision(self, snapshot: dict, decision: dict) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO decisions (
                    symbol, signal, confidence, risk, snapshot_payload, decision_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot["symbol"],
                    decision["signal"],
                    float(decision["confidence"]),
                    float(decision["risk"]),
                    json.dumps(snapshot, ensure_ascii=True),
                    json.dumps(decision, ensure_ascii=True),
                    snapshot.get("captured_at", ""),
                ),
            )

    def record_feedback(self, payload: dict) -> None:
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO feedback (symbol, outcome, pnl, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    payload["symbol"],
                    payload["outcome"],
                    float(payload["pnl"]),
                    json.dumps(payload, ensure_ascii=True),
                    payload.get("closed_at", ""),
                ),
            )

    def get_symbol_context(self, symbol: str, lookback: int = 20) -> dict[str, object]:
        with self._connection() as connection:
            feedback_rows = connection.execute(
                "SELECT outcome, pnl FROM feedback WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol, lookback),
            ).fetchall()
            decision_rows = connection.execute(
                """
                SELECT snapshot_payload, decision_payload
                FROM decisions
                WHERE symbol = ? AND signal IN ('BUY', 'SELL')
                ORDER BY id DESC
                LIMIT ?
                """,
                (symbol, lookback * 3),
            ).fetchall()

        if not feedback_rows:
            return _empty_context_payload()

        decision_contexts: list[tuple[str, str]] = []
        for row in decision_rows:
            snapshot_payload = _safe_json_load(row["snapshot_payload"])
            decision_payload = _safe_json_load(row["decision_payload"])
            decision_contexts.append(_extract_setup_and_context(snapshot_payload, decision_payload))

        overall_bucket = _stats_bucket()
        setup_buckets: dict[str, dict[str, float]] = {}
        context_buckets: dict[str, dict[str, float]] = {}

        for index, row in enumerate(feedback_rows):
            outcome = row["outcome"]
            pnl = row["pnl"]
            _update_stats_bucket(overall_bucket, outcome, pnl)

            if index >= len(decision_contexts):
                continue

            setup_key, context_key = decision_contexts[index]
            setup_bucket = setup_buckets.setdefault(setup_key, _stats_bucket())
            context_bucket = context_buckets.setdefault(context_key, _stats_bucket())
            _update_stats_bucket(setup_bucket, outcome, pnl)
            _update_stats_bucket(context_bucket, outcome, pnl)

        return {
            **_finalize_bucket(overall_bucket),
            "setup_stats": {
                key: _finalize_bucket(bucket)
                for key, bucket in setup_buckets.items()
            },
            "context_stats": {
                key: _finalize_bucket(bucket)
                for key, bucket in context_buckets.items()
            },
        }
