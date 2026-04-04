from __future__ import annotations

import json
import os
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

    @staticmethod
    def read_bytes(path: Path) -> bytes:
        return path.read_bytes()

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        temp_path = path.with_name(f"{path.name}.{int(time.time() * 1000)}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temp_path.replace(path)

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
        if decision.get("comment"):
            payload["comment"] = decision["comment"]
        if decision.get("stop_loss_price") is not None:
            payload["stop_loss_price"] = decision["stop_loss_price"]
        if decision.get("take_profit_price") is not None:
            payload["take_profit_price"] = decision["take_profit_price"]
        if decision.get("position_ticket") is not None:
            payload["position_ticket"] = decision["position_ticket"]
        if decision.get("position_stop_loss") is not None:
            payload["position_stop_loss"] = decision["position_stop_loss"]
        if decision.get("position_take_profit") is not None:
            payload["position_take_profit"] = decision["position_take_profit"]
        command_path = self.command_dir / f"{symbol}.command.json"
        self._write_json(command_path, payload)

    def write_runtime_settings(self, payload: dict[str, Any]) -> None:
        self._write_json(self.runtime_settings_path(), payload)

    @staticmethod
    def _terminal_files_roots() -> list[Path]:
        appdata = os.getenv("APPDATA")
        if not appdata:
            return []

        terminal_root = Path(appdata) / "MetaQuotes" / "Terminal"
        if not terminal_root.exists():
            return []

        roots: list[Path] = []
        for terminal_dir in terminal_root.iterdir():
            files_root = terminal_dir / "MQL5" / "Files"
            if files_root.exists():
                roots.append(files_root)
        return roots

    def find_chart_image(self, snapshot_path: Path, snapshot: dict[str, Any]) -> Path | None:
        declared = str(snapshot.get("chart_image_file") or "").strip()
        candidates: list[Path] = []
        if declared:
            declared_path = Path(declared)
            candidates.append(declared_path if declared_path.is_absolute() else snapshot_path.parent / declared_path)

            if not declared_path.is_absolute():
                for files_root in self._terminal_files_roots():
                    candidates.append(files_root / declared_path)

        cycle_id = str(snapshot.get("cycle_id") or "").strip()
        bridge_name = str(snapshot.get("bridge_name") or "").strip()
        if cycle_id:
            file_name = f"{cycle_id}.chart.png"
            candidates.append(snapshot_path.parent / file_name)
            for files_root in self._terminal_files_roots():
                if bridge_name:
                    candidates.append(files_root / bridge_name / "in" / file_name)
                candidates.append(files_root / file_name)

        snapshot_name = snapshot_path.name
        if snapshot_name.endswith(".snapshot.json"):
            file_name = f"{snapshot_name[:-14]}.chart.png"
            candidates.append(snapshot_path.parent / file_name)
            for files_root in self._terminal_files_roots():
                if bridge_name:
                    candidates.append(files_root / bridge_name / "in" / file_name)
                candidates.append(files_root / file_name)

        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def archive(self, path: Path) -> None:
        target = self.archive_dir / path.name
        if target.exists():
            target = self.archive_dir / f"{path.stem}_{int(time.time())}{path.suffix}"
        shutil.move(str(path), str(target))
