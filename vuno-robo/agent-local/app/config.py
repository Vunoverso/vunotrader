from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AgentConfig:
    backend_url: str
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    instance_name: str
    trading_mode: str
    robot_product_type: str
    visual_shadow_enabled: bool
    bridge_name: str
    poll_interval_seconds: int
    heartbeat_interval_seconds: int
    runtime_config_interval_seconds: int
    max_snapshot_age_seconds: int
    request_timeout_seconds: int
    max_spread_points: int
    default_lot: float
    stop_loss_points: int
    take_profit_points: int
    max_positions_per_symbol: int
    reentry_cooldown_seconds: int
    max_command_age_seconds: int
    deviation_points: int
    execution_retries: int
    use_local_fallback: bool
    pause_new_orders: bool
    snapshot_dir: Path
    command_dir: Path
    feedback_dir: Path
    metadata_dir: Path
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
            robot_id=str(payload["robot_id"]),
            robot_token=str(payload.get("robot_token") or payload["device_token"]),
            user_id=str(payload["user_id"]),
            organization_id=str(payload["organization_id"]),
            instance_name=str(payload.get("instance_name", "Vuno Bridge")),
            trading_mode=str(payload.get("trading_mode", "demo")).lower(),
            robot_product_type=str(payload.get("robot_product_type", "robo_integrado")),
            visual_shadow_enabled=bool(payload.get("visual_shadow_enabled", False)),
            bridge_name=str(payload.get("bridge_name", "VunoBridge")),
            poll_interval_seconds=int(payload.get("poll_interval_seconds", 2)),
            heartbeat_interval_seconds=int(payload.get("heartbeat_interval_seconds", 15)),
            runtime_config_interval_seconds=int(payload.get("runtime_config_interval_seconds", 30)),
            max_snapshot_age_seconds=int(payload.get("max_snapshot_age_seconds", 45)),
            request_timeout_seconds=int(payload.get("request_timeout_seconds", 12)),
            max_spread_points=int(payload.get("max_spread_points", 30)),
            default_lot=float(payload.get("default_lot", 0.01)),
            stop_loss_points=int(payload.get("stop_loss_points", 180)),
            take_profit_points=int(payload.get("take_profit_points", 360)),
            max_positions_per_symbol=int(payload.get("max_positions_per_symbol", 1)),
            reentry_cooldown_seconds=int(payload.get("reentry_cooldown_seconds", 60)),
            max_command_age_seconds=int(payload.get("max_command_age_seconds", 45)),
            deviation_points=int(payload.get("deviation_points", 20)),
            execution_retries=int(payload.get("execution_retries", 3)),
            use_local_fallback=bool(payload.get("use_local_fallback", True)),
            pause_new_orders=bool(payload.get("pause_new_orders", False)),
            snapshot_dir=resolve_path(payload.get("snapshot_dir", "runtime/bridge/in")),
            command_dir=resolve_path(payload.get("command_dir", "runtime/bridge/out")),
            feedback_dir=resolve_path(payload.get("feedback_dir", "runtime/bridge/feedback")),
            metadata_dir=resolve_path(payload.get("metadata_dir", "runtime/bridge/metadata")),
            archive_dir=resolve_path(payload.get("archive_dir", "runtime/archive")),
            memory_db_path=project_dir / "runtime" / "memory.db",
        )
