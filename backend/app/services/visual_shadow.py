from __future__ import annotations

import base64
import binascii
import hashlib
import json
import logging
import os
import struct
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

from app.core.config import get_settings

log = logging.getLogger("visual_shadow")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decode_chart_image(image_base64: str) -> bytes:
    raw = image_base64.split(",", 1)[1] if image_base64.startswith("data:") and "," in image_base64 else image_base64
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("chart_image_base64 inválido") from exc


def _chart_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _png_dimensions(image_bytes: bytes) -> tuple[int, int]:
    if len(image_bytes) < 24 or image_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("imagem não é um PNG válido")
    return struct.unpack(">II", image_bytes[16:24])


def _quality(width: int, height: int, size_bytes: int) -> dict[str, float]:
    pixels = width * height
    size_kb = size_bytes / 1024
    image_clarity = min(1.0, max(0.2, pixels / float(1600 * 900)))
    chart_visibility = min(1.0, max(0.2, size_kb / 180.0))
    overlay_density = 0.35 if size_kb > 220 else 0.22 if size_kb > 120 else 0.12
    score = min(0.98, round(image_clarity * 0.55 + chart_visibility * 0.35 + (1.0 - overlay_density) * 0.10, 4))
    return {
        "score": score,
        "image_clarity": round(image_clarity, 4),
        "chart_visibility": round(chart_visibility, 4),
        "overlay_density": round(overlay_density, 4),
    }


def _normalize_signal(value: Any) -> str:
    signal = str(value or "unknown").strip().lower()
    return signal if signal in {"buy", "sell", "hold"} else "unknown"


def _resolve_alignment(structured_signal: str, visual_signal: str, visual_confidence: float) -> str:
    structured = structured_signal.strip().lower()
    if visual_signal == "unknown":
        return "not_applicable"
    if structured == visual_signal:
        return "aligned"
    return "divergent_high" if visual_confidence >= 0.72 else "divergent_low"


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().upper()


def _is_outside_attached_chart(payload: dict[str, Any]) -> bool:
    chart_symbol = _normalized_text(payload.get("chart_symbol"))
    chart_timeframe = _normalized_text(payload.get("chart_timeframe"))
    symbol = _normalized_text(payload.get("symbol"))
    timeframe = _normalized_text(payload.get("timeframe"))

    if chart_symbol and symbol and chart_symbol != symbol:
        return True
    if chart_timeframe and timeframe and chart_timeframe != timeframe:
        return True
    return False


def _fallback_visual_context(quality: dict[str, float], warning: str) -> tuple[dict[str, Any], str, str | None, str]:
    context = {
        "schema_version": "1.0",
        "status": "processed",
        "engine": "visual_shadow_capture_v1",
        "summary": "Imagem registrada; leitura visual automatizada indisponivel.",
        "setup_guess": "unknown",
        "signal_bias": "unknown",
        "quality": quality,
        "market_read": {"trend": "unknown", "volatility": "unknown", "structure": "unknown"},
        "evidence": [{"label": "capture_verified", "confidence": quality["score"], "source": "screen"}],
        "warnings": [warning],
        "rationale": "O screenshot foi armazenado e validado, mas a etapa visual com IA nao foi executada.",
        "model_version": "capture-only-v1",
    }
    return context, "not_applicable", warning, "capture-only-v1"


def _ask_visual_model(snapshot: dict[str, Any], image_base64: str, api_key: str) -> dict[str, Any]:
    settings = get_settings()
    client = OpenAI(api_key=api_key)
    prompt = (
        "Voce esta em shadow mode do robo trader. Analise apenas a imagem do grafico e retorne JSON puro com as chaves "
        "summary, setup_guess, signal_bias, confidence, market_read, evidence, warnings e rationale. "
        f"Contexto estruturado: symbol={snapshot.get('symbol')} timeframe={snapshot.get('timeframe')} "
        f"structured_signal={snapshot.get('structured_signal')} structured_confidence={snapshot.get('structured_confidence')}. "
        "signal_bias deve ser buy, sell, hold ou unknown. confidence deve ficar entre 0 e 1. "
        "market_read deve ter trend, volatility e structure. warnings deve ser array de strings."
    )
    response = client.chat.completions.create(
        model=settings.visual_shadow_model,
        temperature=0.1,
        max_tokens=350,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Responda apenas JSON valido e nao proponha execucao direta de ordem."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}},
                ],
            },
        ],
    )
    content = response.choices[0].message.content if response.choices else "{}"
    payload = json.loads(content or "{}")
    if not isinstance(payload, dict):
        raise ValueError("Resposta visual sem objeto JSON")
    return payload


def _persist_visual_context(sb, row: dict[str, Any]) -> None:
    sb.table("trade_visual_contexts").upsert(row, on_conflict="robot_instance_id,cycle_id").execute()


def analyze_visual_shadow_capture(
    *,
    image_bytes: bytes,
    image_base64: str,
    symbol: str | None,
    timeframe: str | None,
    structured_signal: str,
    structured_confidence: float,
) -> dict[str, Any]:
    settings = get_settings()
    width, height = _png_dimensions(image_bytes)
    quality = _quality(width, height, len(image_bytes))
    context_input = {
        "symbol": symbol,
        "timeframe": timeframe,
        "structured_signal": structured_signal,
        "structured_confidence": structured_confidence,
    }
    api_key = (settings.openai_api_key or "").strip()

    try:
        if not settings.visual_shadow_model or not api_key:
            raise RuntimeError("vision_api_unconfigured")
        model_payload = _ask_visual_model(context_input, image_base64, api_key)
        visual_signal = _normalize_signal(model_payload.get("signal_bias"))
        visual_confidence = max(0.0, min(float(model_payload.get("confidence", 0.0) or 0.0), 1.0))
        alignment = _resolve_alignment(structured_signal, visual_signal, visual_confidence)
        conflict_reason = None if alignment == "aligned" else str(model_payload.get("rationale") or "visual_divergence")
        visual_context = {
            "schema_version": "1.0",
            "status": "processed",
            "engine": "visual_shadow_openai_v1",
            "summary": str(model_payload.get("summary") or "Leitura visual processada."),
            "setup_guess": str(model_payload.get("setup_guess") or "unknown"),
            "signal_bias": visual_signal,
            "quality": quality,
            "market_read": model_payload.get("market_read") or {"trend": "unknown", "volatility": "unknown", "structure": "unknown"},
            "evidence": model_payload.get("evidence") or [],
            "warnings": model_payload.get("warnings") or [],
            "rationale": str(model_payload.get("rationale") or "Leitura visual concluida."),
            "model_version": settings.visual_shadow_model,
            "visual_confidence": visual_confidence,
        }
        return {
            "visual_shadow_status": "processed",
            "visual_alignment": alignment,
            "visual_conflict_reason": conflict_reason,
            "visual_context": visual_context,
            "visual_model_version": settings.visual_shadow_model,
        }
    except Exception as exc:
        visual_context, alignment, conflict_reason, model_version = _fallback_visual_context(quality, str(exc))
        return {
            "visual_shadow_status": "processed",
            "visual_alignment": alignment,
            "visual_conflict_reason": conflict_reason,
            "visual_context": visual_context,
            "visual_model_version": model_version,
        }


def process_visual_shadow_cycle(
    *,
    sb,
    robot: dict[str, Any],
    payload: dict[str, Any],
    decision_id: str | None,
    structured_signal: str,
    structured_confidence: float,
) -> dict[str, str | None]:
    settings = get_settings()
    cycle_id = str(payload.get("cycle_id") or "").strip()
    if not cycle_id:
        return {"visual_shadow_status": None, "visual_alignment": None, "visual_conflict_reason": None}

    base_row = {
        "organization_id": robot["organization_id"],
        "robot_instance_id": robot["id"],
        "trade_decision_id": decision_id,
        "cycle_id": cycle_id,
        "chart_image_captured_at": payload.get("chart_image_captured_at") or None,
        "visual_worker_lock_owner": str(payload.get("worker_owner") or "agent-local").strip() or "agent-local",
        "visual_worker_locked_at": _now_iso(),
    }

    visual_requested = bool(payload.get("visual_shadow_requested", robot.get("visual_shadow_enabled")))
    if not robot.get("visual_shadow_enabled") or not visual_requested:
        _persist_visual_context(sb, {
            **base_row,
            "visual_shadow_status": "skipped",
            "visual_alignment": "not_applicable",
            "visual_conflict_reason": "visual_shadow_disabled",
        })
        return {"visual_shadow_status": "skipped", "visual_alignment": "not_applicable", "visual_conflict_reason": "visual_shadow_disabled"}

    if settings.visual_shadow_kill_switch:
        _persist_visual_context(sb, {
            **base_row,
            "visual_shadow_status": "skipped",
            "visual_alignment": "not_applicable",
            "visual_conflict_reason": "visual_shadow_kill_switch",
        })
        return {"visual_shadow_status": "skipped", "visual_alignment": "not_applicable", "visual_conflict_reason": "visual_shadow_kill_switch"}

    if _is_outside_attached_chart(payload):
        chart_symbol = str(payload.get("chart_symbol") or "").strip() or None
        chart_timeframe = str(payload.get("chart_timeframe") or "").strip() or None
        requested_symbol = str(payload.get("symbol") or "").strip() or None
        requested_timeframe = str(payload.get("timeframe") or "").strip() or None
        _persist_visual_context(sb, {
            **base_row,
            "visual_shadow_status": "skipped_non_chart_symbol",
            "visual_alignment": "not_applicable",
            "visual_conflict_reason": "symbol_outside_attached_chart",
            "visual_context": {
                "schema_version": "1.0",
                "status": "skipped",
                "engine": "visual_shadow_router_v1",
                "summary": "Ciclo fora do grafico anexado; o shadow visual nao comparou este simbolo.",
                "chart_symbol": chart_symbol,
                "chart_timeframe": chart_timeframe,
                "requested_symbol": requested_symbol,
                "requested_timeframe": requested_timeframe,
            },
        })
        return {
            "visual_shadow_status": "skipped_non_chart_symbol",
            "visual_alignment": "not_applicable",
            "visual_conflict_reason": "symbol_outside_attached_chart",
        }

    image_base64 = str(payload.get("chart_image_base64") or "").strip()
    if not image_base64:
        _persist_visual_context(sb, {
            **base_row,
            "visual_shadow_status": "skipped",
            "visual_alignment": "not_applicable",
            "visual_conflict_reason": "chart_image_missing",
        })
        return {"visual_shadow_status": "skipped", "visual_alignment": "not_applicable", "visual_conflict_reason": "chart_image_missing"}

    try:
        image_bytes = _decode_chart_image(image_base64)
        width, height = _png_dimensions(image_bytes)
    except Exception as exc:
        _persist_visual_context(sb, {
            **base_row,
            "visual_shadow_status": "error",
            "visual_alignment": "error",
            "visual_conflict_reason": f"chart_image_invalid: {exc}",
        })
        return {"visual_shadow_status": "error", "visual_alignment": "error", "visual_conflict_reason": f"chart_image_invalid: {exc}"}

    image_hash = str(payload.get("chart_image_sha256") or _chart_hash(image_bytes))
    captured_at = datetime.now(timezone.utc)
    storage_path = f"{robot['organization_id']}/{robot['id']}/{captured_at:%Y/%m/%d}/{cycle_id}.chart.png"
    try:
        sb.storage.from_(settings.visual_storage_bucket).upload(
            storage_path,
            image_bytes,
            {"content-type": "image/png", "upsert": "true"},
        )
    except Exception as exc:
        log.warning("Visual storage upload failed for %s: %s", cycle_id, exc)
        _persist_visual_context(sb, {
            **base_row,
            "chart_image_hash": image_hash,
            "visual_shadow_status": "error",
            "visual_alignment": "error",
            "visual_conflict_reason": f"storage_upload_failed: {exc}",
        })
        return {"visual_shadow_status": "error", "visual_alignment": "error", "visual_conflict_reason": f"storage_upload_failed: {exc}"}
    analysis = analyze_visual_shadow_capture(
        image_bytes=image_bytes,
        image_base64=image_base64,
        symbol=str(payload.get("symbol") or "").strip() or None,
        timeframe=str(payload.get("timeframe") or "").strip() or None,
        structured_signal=structured_signal,
        structured_confidence=structured_confidence,
    )

    _persist_visual_context(sb, {
        **base_row,
        "chart_image_storage_path": storage_path,
        "chart_image_hash": image_hash,
        "visual_shadow_status": analysis["visual_shadow_status"],
        "visual_context": analysis["visual_context"],
        "visual_alignment": analysis["visual_alignment"],
        "visual_conflict_reason": analysis["visual_conflict_reason"],
        "visual_model_version": analysis["visual_model_version"],
        "processed_at": _now_iso(),
    })
    return {
        "visual_shadow_status": analysis["visual_shadow_status"],
        "visual_alignment": analysis["visual_alignment"],
        "visual_conflict_reason": analysis["visual_conflict_reason"],
    }