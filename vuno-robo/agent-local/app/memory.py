from __future__ import annotations

import json
import sqlite3
from pathlib import Path


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

                CREATE TABLE IF NOT EXISTS symbol_state (
                    symbol TEXT PRIMARY KEY,
                    pending_decision_id TEXT,
                    active_decision_id TEXT,
                    last_open_ticket INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
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

    def remember_pending_decision(self, symbol: str, decision_id: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO symbol_state (symbol, pending_decision_id, active_decision_id, last_open_ticket, updated_at)
                VALUES (?, ?, NULL, 0, datetime('now'))
                ON CONFLICT(symbol) DO UPDATE SET
                    pending_decision_id = excluded.pending_decision_id,
                    updated_at = excluded.updated_at
                """,
                (symbol, decision_id),
            )

    def get_pending_decision(self, symbol: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT pending_decision_id FROM symbol_state WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        return str(row["pending_decision_id"]) if row and row["pending_decision_id"] else None

    def get_active_decision_id(self, symbol: str) -> str | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT active_decision_id FROM symbol_state WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        return str(row["active_decision_id"]) if row and row["active_decision_id"] else None

    def get_open_ticket(self, symbol: str) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT last_open_ticket FROM symbol_state WHERE symbol = ?",
                (symbol,),
            ).fetchone()
        return int(row["last_open_ticket"]) if row else 0

    def set_open_ticket(self, symbol: str, ticket: int) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO symbol_state (symbol, pending_decision_id, active_decision_id, last_open_ticket, updated_at)
                VALUES (?, NULL, NULL, ?, datetime('now'))
                ON CONFLICT(symbol) DO UPDATE SET
                    last_open_ticket = excluded.last_open_ticket,
                    updated_at = excluded.updated_at
                """,
                (symbol, ticket),
            )

    def mark_open_trade(self, symbol: str, decision_id: str, ticket: int) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO symbol_state (symbol, pending_decision_id, active_decision_id, last_open_ticket, updated_at)
                VALUES (?, NULL, ?, ?, datetime('now'))
                ON CONFLICT(symbol) DO UPDATE SET
                    pending_decision_id = NULL,
                    active_decision_id = excluded.active_decision_id,
                    last_open_ticket = excluded.last_open_ticket,
                    updated_at = excluded.updated_at
                """,
                (symbol, decision_id, ticket),
            )

    def clear_open_ticket(self, symbol: str) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE symbol_state SET last_open_ticket = 0, updated_at = datetime('now') WHERE symbol = ?",
                (symbol,),
            )

    def clear_active_trade(self, symbol: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE symbol_state
                SET pending_decision_id = NULL,
                    active_decision_id = NULL,
                    last_open_ticket = 0,
                    updated_at = datetime('now')
                WHERE symbol = ?
                """,
                (symbol,),
            )

    def get_symbol_context(self, symbol: str, lookback: int = 20) -> dict[str, float]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT outcome, pnl FROM feedback WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                (symbol, lookback),
            ).fetchall()

        total = len(rows)
        if total == 0:
            return {
                "recent_trades": 0,
                "recent_win_rate": 0.5,
                "recent_pnl": 0.0,
            }

        wins = sum(1 for row in rows if str(row["outcome"]).upper() == "WIN")
        pnl = sum(float(row["pnl"]) for row in rows)

        return {
            "recent_trades": float(total),
            "recent_win_rate": round(wins / total, 2),
            "recent_pnl": round(pnl, 2),
        }
