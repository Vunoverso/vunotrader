from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AgentConfig:
    backend_url: str
    robot_token: str
    poll_interval_seconds: int
    heartbeat_interval_seconds: int
    runtime_config_interval_seconds: int
    max_snapshot_age_seconds: int
    request_timeout_seconds: int
    snapshot_dir: Path
    command_dir: Path
    feedback_dir: Path
    archive_dir: Path
    memory_db_path: Path

    @classmethod
    def load(cls, path: Path) -> "AgentConfig":
        config_path = path.resolve()
        project_dir = config_path.parents[1]
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))

        def resolve_path(value: str) -> Path:
            candidate = Path(os.path.expandvars(value)).expanduser()
            if candidate.is_absolute():
                return candidate
            return project_dir / candidate

        return cls(
            backend_url=str(payload["backend_url"]).rstrip("/"),
            robot_token=str(payload.get("robot_token") or payload["device_token"]),
            poll_interval_seconds=int(payload.get("poll_interval_seconds", 2)),
            heartbeat_interval_seconds=int(payload.get("heartbeat_interval_seconds", 15)),
            runtime_config_interval_seconds=int(payload.get("runtime_config_interval_seconds", 30)),
            max_snapshot_age_seconds=int(payload.get("max_snapshot_age_seconds", 45)),
            request_timeout_seconds=int(payload.get("request_timeout_seconds", 12)),
            snapshot_dir=resolve_path(payload.get("snapshot_dir", "runtime/bridge/in")),
            command_dir=resolve_path(payload.get("command_dir", "runtime/bridge/out")),
            feedback_dir=resolve_path(payload.get("feedback_dir", "runtime/bridge/feedback")),
            archive_dir=resolve_path(payload.get("archive_dir", "runtime/archive")),
            memory_db_path=project_dir / "runtime" / "memory.db",
        )
