from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.supabase import get_service_supabase
from app.services.visual_shadow import analyze_visual_shadow_capture, _chart_hash


def _load_rows(sb, cycle_id: str | None, limit: int) -> list[dict]:
    query = sb.table("trade_visual_contexts").select(
        "id, trade_decision_id, cycle_id, chart_image_storage_path, chart_image_hash, visual_shadow_status, visual_model_version, created_at"
    ).order("created_at", desc=False)
    if cycle_id:
        query = query.eq("cycle_id", cycle_id)
    rows = query.limit(limit).execute().data or []
    return [row for row in rows if row.get("chart_image_storage_path")]


def _download_bytes(sb, bucket: str, storage_path: str) -> bytes:
    data = sb.storage.from_(bucket).download(storage_path)
    if isinstance(data, bytes):
        return data
    if hasattr(data, "read"):
        return data.read()
    raise RuntimeError(f"Download invalido para {storage_path}")


def _load_decision(sb, decision_id: str | None) -> dict:
    if not decision_id:
        return {}
    rows = sb.table("trade_decisions").select("symbol, timeframe, side, confidence").eq("id", decision_id).limit(1).execute().data or []
    return rows[0] if rows else {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Reprocessa ciclos visuais persistidos com a IA configurada")
    parser.add_argument("--cycle-id", help="Reprocessa apenas um cycle_id especifico")
    parser.add_argument("--limit", type=int, default=50, help="Numero maximo de ciclos para reprocessar")
    parser.add_argument("--capture-only", action="store_true", help="Filtra apenas ciclos em capture-only-v1")
    args = parser.parse_args()

    settings = get_settings()
    if not (settings.openai_api_key or "").strip():
        raise RuntimeError("OPENAI_API_KEY nao configurada no backend")

    sb = get_service_supabase()
    rows = _load_rows(sb, args.cycle_id, args.limit)
    updated = 0

    for row in rows:
        if args.capture_only and row.get("visual_model_version") != "capture-only-v1":
            continue

        storage_path = str(row["chart_image_storage_path"])
        image_bytes = _download_bytes(sb, settings.visual_storage_bucket, storage_path)
        decision = _load_decision(sb, row.get("trade_decision_id"))
        analysis = analyze_visual_shadow_capture(
            image_bytes=image_bytes,
            image_base64=base64.b64encode(image_bytes).decode("ascii"),
            symbol=str(decision.get("symbol") or "").strip() or None,
            timeframe=str(decision.get("timeframe") or "").strip() or None,
            structured_signal=str(decision.get("side") or "hold"),
            structured_confidence=float(decision.get("confidence") or 0.0),
        )
        sb.table("trade_visual_contexts").update(
            {
                "chart_image_hash": row.get("chart_image_hash") or _chart_hash(image_bytes),
                "visual_shadow_status": analysis["visual_shadow_status"],
                "visual_alignment": analysis["visual_alignment"],
                "visual_conflict_reason": analysis["visual_conflict_reason"],
                "visual_context": analysis["visual_context"],
                "visual_model_version": analysis["visual_model_version"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", row["id"]).execute()
        updated += 1
        print(f"UPDATED {row['cycle_id']} -> {analysis['visual_alignment']} / {analysis['visual_model_version']}")

    print(f"TOTAL_UPDATED {updated}")


if __name__ == "__main__":
    main()