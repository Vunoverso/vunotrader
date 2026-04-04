from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any


class BridgeFilesystem:
    def __init__(
        self,
        snapshot_dir: Path,
        command_dir: Path,
        feedback_dir: Path,
        metadata_dir: Path,
        archive_dir: Path,
    ) -> None:
        self.snapshot_dir = snapshot_dir
        self.command_dir = command_dir
        self.feedback_dir = feedback_dir
        self.metadata_dir = metadata_dir
        self.archive_dir = archive_dir
        self.ensure_directories()

    def ensure_directories(self) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.command_dir.mkdir(parents=True, exist_ok=True)
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def pending_snapshots(self) -> list[Path]:
        return sorted(self.snapshot_dir.glob("*.json"))

    def pending_feedback(self) -> list[Path]:
        return sorted(self.feedback_dir.glob("*.json"))

    def pending_metadata(self) -> list[Path]:
        return sorted(self.metadata_dir.glob("*.json"))

    def runtime_settings_path(self) -> Path:
        return self.command_dir / "runtime.settings.json"

    @staticmethod
    def load_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_command(self, symbol: str, decision: dict[str, Any]) -> None:
        payload = {
            "symbol": symbol,
            "signal": decision["signal"],
            "confidence": decision["confidence"],
            "risk": decision["risk"],
            "stop_loss_points": decision["stop_loss_points"],
            "take_profit_points": decision["take_profit_points"],
            "position_action": decision.get("position_action", "NONE"),
            "reason": decision.get("reason") or decision.get("rationale", ""),
            "generated_at_unix": int(time.time()),
        }
        if decision.get("position_ticket") is not None:
            payload["position_ticket"] = decision["position_ticket"]
        if decision.get("position_stop_loss") is not None:
            payload["position_stop_loss"] = decision["position_stop_loss"]
        if decision.get("position_take_profit") is not None:
            payload["position_take_profit"] = decision["position_take_profit"]
        command_path = self.command_dir / f"{symbol}.command.json"
        command_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def write_runtime_settings(self, payload: dict[str, Any]) -> None:
        self.runtime_settings_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def archive(self, path: Path) -> None:
        target = self.archive_dir / path.name
        if target.exists():
            target = self.archive_dir / f"{path.stem}_{int(time.time())}{path.suffix}"
        shutil.move(str(path), str(target))
