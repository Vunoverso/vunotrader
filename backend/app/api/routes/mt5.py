"""
Endpoints para comunicação direta com o EA do MetaTrader 5.
Recebe heartbeat e dados de mercado sem depender do Python local.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.supabase import get_service_supabase

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class HeartbeatPayload(BaseModel):
    robot_id: str
    robot_token: str
    user_id: str
    organization_id: str
    mode: str = "demo"


class HeartbeatResponse(BaseModel):
    status: str
    timestamp: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validate_robot(robot_id: str, robot_token: str, organization_id: str) -> dict:
    """Valida se o robot_id + token pertencem à organização. Retorna o registro."""
    sb = get_service_supabase()
    result = (
        sb.table("robot_instances")
        .select("id, token, organization_id, status")
        .eq("id", robot_id)
        .eq("organization_id", organization_id)
        .single()
        .execute()
    )
    row = result.data
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Robot not found")
    if row.get("token") != robot_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid robot token")
    if row.get("status") == "revoked":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Robot revoked")
    return row


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/heartbeat", response_model=HeartbeatResponse, summary="Ping de vida do EA")
async def heartbeat(payload: HeartbeatPayload):
    """
    Recebe um ping do EA do MetaTrader 5 e atualiza last_seen_at no Supabase.
    Chamado a cada 30 segundos pelo OnTimer() do EA — sem necessidade do Python local.
    """
    _validate_robot(payload.robot_id, payload.robot_token, payload.organization_id)

    now = datetime.now(timezone.utc).isoformat()
    sb = get_service_supabase()
    sb.table("robot_instances").update({"last_seen_at": now}).eq("id", payload.robot_id).execute()

    return HeartbeatResponse(status="ok", timestamp=now)
