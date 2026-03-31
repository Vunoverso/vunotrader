from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from supabase import create_client


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        k = key.strip()
        v = value.strip().strip('"')
        current = os.environ.get(k, "")
        if not current:
            os.environ[k] = v


load_dotenv(Path("brain.env"))
load_dotenv(Path("backend/.env"))

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
if not url or not key:
    raise SystemExit("missing SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY")

user_id = os.getenv("BRAIN_USER_ID", "")
org_id = os.getenv("BRAIN_ORG_ID", "")
robot_id = os.getenv("MT5_ROBOT_INSTANCE_ID", "")

client = create_client(url, key)

if not user_id or not org_id:
    latest = (
        client.table("trade_decisions")
        .select("user_id,organization_id,robot_instance_id")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    row = (latest.data or [{}])[0]
    user_id = user_id or str(row.get("user_id") or "")
    org_id = org_id or str(row.get("organization_id") or "")
    robot_id = robot_id or str(row.get("robot_instance_id") or "")

window = datetime.now(timezone.utc) - timedelta(minutes=20)
window_iso = window.isoformat()

result = {
    "user_id": user_id,
    "organization_id": org_id,
    "robot_instance_id": robot_id,
}

if user_id and org_id:
    decisions = (
        client.table("trade_decisions")
        .select("id,trade_id,symbol,side,mode,created_at", count="exact")
        .eq("user_id", user_id)
        .eq("organization_id", org_id)
        .gte("created_at", window_iso)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    result["decisions_count"] = decisions.count or 0
    result["decisions"] = decisions.data or []

    executed = (
        client.table("executed_trades")
        .select("id,trade_decision_id,broker_ticket,status,opened_at,closed_at", count="exact")
        .eq("organization_id", org_id)
        .gte("opened_at", window_iso)
        .order("opened_at", desc=True)
        .limit(5)
        .execute()
    )
    result["executed_count"] = executed.count or 0
    result["executed"] = executed.data or []

    outcomes = (
        client.table("trade_outcomes")
        .select("id,executed_trade_id,result,pnl_money,created_at", count="exact")
        .eq("organization_id", org_id)
        .gte("created_at", window_iso)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    result["outcomes_count"] = outcomes.count or 0
    result["outcomes"] = outcomes.data or []

print(json.dumps(result, ensure_ascii=True))
