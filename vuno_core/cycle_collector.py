from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or default).strip()


class CycleCollector:
    """Coleta ciclos do scanner para CSV local e, opcionalmente, Supabase."""

    def __init__(self, csv_path: Path | None = None):
        self.csv_path = csv_path or (Path(__file__).resolve().parents[1] / "scanner_cycle_logs.csv")
        self.enabled = _env("VUNO_CYCLE_LOG_ENABLED", "1") == "1"

        self.user_id = _env("BRAIN_USER_ID", "")
        self.organization_id = _env("BRAIN_ORG_ID", "")
        self.robot_instance_id = _env("MT5_ROBOT_INSTANCE_ID", "")

        self._supabase_enabled = _env("VUNO_CYCLE_SUPABASE_ENABLED", "0") == "1"
        self._client = None
        self._supabase_ready = False

        if self.enabled:
            self._ensure_csv_header()
        if self.enabled and self._supabase_enabled:
            self._init_supabase()

    def _init_supabase(self) -> None:
        url = _env("SUPABASE_URL", "")
        key = _env("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return

        try:
            from supabase import create_client  # type: ignore

            self._client = create_client(url, key)
            self._supabase_ready = True
        except Exception:
            self._supabase_ready = False

    def _ensure_csv_header(self) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if self.csv_path.exists():
            return

        with self.csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames())
            writer.writeheader()

    @staticmethod
    def _fieldnames() -> list[str]:
        return [
            "cycle_id",
            "cycle_ts",
            "mode",
            "symbol",
            "timeframe",
            "signal",
            "decision_status",
            "decision_reason",
            "block_reason",
            "confidence",
            "risk",
            "regime",
            "score",
            "spread_points",
            "atr_pct",
            "volume_ratio",
            "rsi",
            "momentum_20",
            "decision_id",
            "executed",
            "broker_ticket",
            "result",
            "pnl_money",
            "pnl_points",
            "user_id",
            "organization_id",
            "robot_instance_id",
            "feature_hash",
            "created_at",
        ]

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def make_cycle_id(symbol: str, timeframe: str, cycle_ts: str) -> str:
        seed = f"{symbol.upper()}|{timeframe.upper()}|{cycle_ts}"
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _make_feature_hash(payload: dict[str, Any]) -> str:
        raw = "|".join(
            [
                str(payload.get("symbol", "")),
                str(payload.get("timeframe", "")),
                f"{float(payload.get('confidence', 0.0) or 0.0):.6f}",
                f"{float(payload.get('score', 0.0) or 0.0):.6f}",
                f"{float(payload.get('atr_pct', 0.0) or 0.0):.6f}",
                f"{float(payload.get('volume_ratio', 0.0) or 0.0):.6f}",
                f"{float(payload.get('rsi', 0.0) or 0.0):.6f}",
                f"{float(payload.get('momentum_20', 0.0) or 0.0):.6f}",
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def log_cycle(self, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        cycle_ts = str(payload.get("cycle_ts") or self._now_iso())
        symbol = str(payload.get("symbol", "")).upper()
        timeframe = str(payload.get("timeframe", "")).upper()

        row = {
            "cycle_id": str(payload.get("cycle_id") or self.make_cycle_id(symbol, timeframe, cycle_ts)),
            "cycle_ts": cycle_ts,
            "mode": str(payload.get("mode", "demo")),
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": str(payload.get("signal", "HOLD")).upper(),
            "decision_status": str(payload.get("decision_status", "analyzed")),
            "decision_reason": str(payload.get("decision_reason", "")),
            "block_reason": str(payload.get("block_reason", "")),
            "confidence": float(payload.get("confidence", 0.0) or 0.0),
            "risk": float(payload.get("risk", 0.0) or 0.0),
            "regime": str(payload.get("regime", "lateral")),
            "score": float(payload.get("score", 0.0) or 0.0),
            "spread_points": float(payload.get("spread_points", 0.0) or 0.0),
            "atr_pct": float(payload.get("atr_pct", 0.0) or 0.0),
            "volume_ratio": float(payload.get("volume_ratio", 0.0) or 0.0),
            "rsi": float(payload.get("rsi", 0.0) or 0.0),
            "momentum_20": float(payload.get("momentum_20", 0.0) or 0.0),
            "decision_id": str(payload.get("decision_id", "")),
            "executed": bool(payload.get("executed", False)),
            "broker_ticket": str(payload.get("broker_ticket", "")),
            "result": str(payload.get("result", "")),
            "pnl_money": float(payload.get("pnl_money", 0.0) or 0.0),
            "pnl_points": float(payload.get("pnl_points", 0.0) or 0.0),
            "user_id": str(payload.get("user_id") or self.user_id),
            "organization_id": str(payload.get("organization_id") or self.organization_id),
            "robot_instance_id": str(payload.get("robot_instance_id") or self.robot_instance_id),
            "feature_hash": self._make_feature_hash(payload),
            "created_at": self._now_iso(),
        }

        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._fieldnames())
            writer.writerow(row)

        if self._supabase_ready:
            self._log_supabase(row)

    def _log_supabase(self, row: dict[str, Any]) -> None:
        try:
            self._client.table("scanner_cycle_logs").insert(
                {
                    "cycle_id": row["cycle_id"],
                    "cycle_ts": row["cycle_ts"],
                    "mode": row["mode"],
                    "symbol": row["symbol"],
                    "timeframe": row["timeframe"],
                    "signal": row["signal"],
                    "decision_status": row["decision_status"],
                    "decision_reason": row["decision_reason"],
                    "block_reason": row["block_reason"],
                    "confidence": row["confidence"],
                    "risk_pct": row["risk"],
                    "regime": row["regime"],
                    "score": row["score"],
                    "spread_points": row["spread_points"],
                    "atr_pct": row["atr_pct"],
                    "volume_ratio": row["volume_ratio"],
                    "rsi": row["rsi"],
                    "momentum_20": row["momentum_20"],
                    "decision_id": row["decision_id"] or None,
                    "executed": row["executed"],
                    "broker_ticket": row["broker_ticket"] or None,
                    "result": row["result"] or None,
                    "pnl_money": row["pnl_money"],
                    "pnl_points": row["pnl_points"],
                    "user_id": row["user_id"] or None,
                    "organization_id": row["organization_id"] or None,
                    "robot_instance_id": row["robot_instance_id"] or None,
                    "feature_hash": row["feature_hash"],
                }
            ).execute()
        except Exception:
            return
