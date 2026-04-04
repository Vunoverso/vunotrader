from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_audit_event(
    connection,
    tenant_id: int,
    event_type: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    robot_instance_id: int | None = None,
) -> None:
    connection.execute(
        """
        INSERT INTO audit_events (
            tenant_id, user_id, robot_instance_id, event_type, payload, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            tenant_id,
            user_id,
            robot_instance_id,
            event_type,
            json.dumps(payload, ensure_ascii=True),
            now_utc_iso(),
        ),
    )
