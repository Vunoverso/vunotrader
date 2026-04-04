from __future__ import annotations

import argparse
import base64
import hashlib
import os
import socket
import sys
import time
from pathlib import Path

try:
    from .api_client import BackendClient
    from .bridge import BridgeFilesystem
    from .config import AgentConfig
    from .legacy_mt5_api import (
        build_command_payload,
        build_heartbeat_payload,
        build_runtime_settings,
        build_signal_payload,
        build_trade_feedback_payload,
        build_trade_opened_payload,
    )
    from .memory import MemoryStore
    from .runtime_contract import sync_runtime_settings as sync_remote_runtime_settings
except ImportError:
    from api_client import BackendClient
    from bridge import BridgeFilesystem
    from config import AgentConfig
    from legacy_mt5_api import (
        build_command_payload,
        build_heartbeat_payload,
        build_runtime_settings,
        build_signal_payload,
        build_trade_feedback_payload,
        build_trade_opened_payload,
    )
    from memory import MemoryStore
    from runtime_contract import sync_runtime_settings as sync_remote_runtime_settings


AGENT_RUNTIME = "exe" if getattr(sys, "frozen", False) else "python"
WORKER_OWNER = f"{socket.gethostname().lower()}-{os.getpid()}"


def local_fallback(snapshot: dict) -> dict:
    ema_fast = float(snapshot.get("ema_fast", 0.0))
    ema_slow = float(snapshot.get("ema_slow", 0.0))

    signal = "HOLD"
    if ema_fast > ema_slow:
        signal = "BUY"
    elif ema_fast < ema_slow:
        signal = "SELL"

    return {
        "signal": signal,
        "confidence": 0.3,
        "risk": 0.2 if signal != "HOLD" else 0.0,
        "stop_loss_points": 180 if signal != "HOLD" else 0,
        "take_profit_points": 360 if signal != "HOLD" else 0,
        "reason": "fallback_local_agent",
    }


def to_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_decision(decision: dict, fallback_reason: str) -> dict:
    signal = str(decision.get("signal", "HOLD")).upper().strip()
    if signal not in {"BUY", "SELL", "HOLD"}:
        signal = "HOLD"

    confidence = max(0.0, min(float(decision.get("confidence", 0.0) or 0.0), 1.0))
    risk = max(0.0, min(float(decision.get("risk", 0.0) or 0.0), 1.0))
    stop_loss = max(0, to_int(decision.get("stop_loss_points", 0), 0))
    take_profit = max(0, to_int(decision.get("take_profit_points", 0), 0))
    reason = str(decision.get("reason") or decision.get("rationale") or fallback_reason).strip()

    if signal == "HOLD":
        risk = 0.0
        stop_loss = 0
        take_profit = 0

    return {
        "signal": signal,
        "confidence": confidence,
        "risk": risk,
        "stop_loss_points": stop_loss,
        "take_profit_points": take_profit,
        "reason": reason or fallback_reason,
    }


def should_skip_snapshot(path: Path, max_age_seconds: int) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return True
    return age > max_age_seconds


def archive_safely(bridge: BridgeFilesystem, path: Path, kind: str) -> bool:
    try:
        bridge.archive(path)
        return True
    except PermissionError:
        print(f"[RETRY] {kind} ainda bloqueado: {path.name}")
        return False
    except FileNotFoundError:
        return False
    except OSError as exc:
        print(f"[WARN] Falha ao arquivar {kind.lower()} {path.name}: {exc}")
        return False


def archive_related_assets(bridge: BridgeFilesystem, snapshot_path: Path, image_path: Path | None) -> None:
    archive_safely(bridge, snapshot_path, "Snapshot")
    if image_path is not None:
        archive_safely(bridge, image_path, "Imagem")


def sync_runtime_settings(bridge: BridgeFilesystem, client: BackendClient, config: AgentConfig) -> str:
    try:
        settings = sync_remote_runtime_settings(bridge, client)
        return f"remoto sincronizado modo={settings.get('trading_mode', config.trading_mode)}"
    except Exception as exc:
        bridge.write_runtime_settings(build_runtime_settings(config))
        return f"fallback local ({exc})"


def sync_open_trade(snapshot: dict, client: BackendClient, memory: MemoryStore, config: AgentConfig) -> None:
    symbol = str(snapshot.get("symbol", "")).strip()
    current_ticket = to_int(snapshot.get("open_position_ticket"), 0)
    last_ticket = memory.get_open_ticket(symbol)

    if current_ticket <= 0:
        if last_ticket > 0:
            memory.clear_open_ticket(symbol)
        return

    if current_ticket == last_ticket:
        return

    decision_id = memory.get_pending_decision(symbol) or memory.get_active_decision_id(symbol)
    if not decision_id:
        memory.set_open_ticket(symbol, current_ticket)
        print(f"[OPEN] {symbol} ticket {current_ticket} sem decision_id para vincular")
        return

    try:
        client.send_trade_opened(build_trade_opened_payload(snapshot, config, decision_id))
        memory.mark_open_trade(symbol, decision_id, current_ticket)
        print(f"[OPEN] {symbol} -> {decision_id}")
    except Exception as exc:
        print(f"[RETRY] abertura pendente para {symbol}: {exc}")


def process_metadata(bridge: BridgeFilesystem, client: BackendClient) -> None:
    for metadata_path in bridge.pending_metadata():
        try:
            payload = bridge.load_json(metadata_path)
        except PermissionError:
            print(f"[RETRY] Metadata ainda em escrita: {metadata_path.name}")
            continue
        except Exception as exc:
            print(f"[SKIP] Metadata invalida: {metadata_path.name} -> {exc}")
            archive_safely(bridge, metadata_path, "Metadata")
            continue

        try:
            client.send_symbol_catalog(payload)
        except Exception as exc:
            print(f"[RETRY] Metadata pendente: {metadata_path.name} -> {exc}")
            continue

        if archive_safely(bridge, metadata_path, "Metadata"):
            print(f"[METADATA] enviado: {metadata_path.name}")


def process_snapshots(
    bridge: BridgeFilesystem,
    client: BackendClient,
    memory: MemoryStore,
    config: AgentConfig,
) -> None:
    for snapshot_path in bridge.pending_snapshots():
        image_path: Path | None = None
        if should_skip_snapshot(snapshot_path, config.max_snapshot_age_seconds):
            print(f"[STALE] Snapshot expirado: {snapshot_path.name}")
            archive_related_assets(bridge, snapshot_path, image_path)
            continue

        try:
            snapshot = bridge.load_json(snapshot_path)
        except PermissionError:
            print(f"[RETRY] Snapshot ainda em escrita: {snapshot_path.name}")
            continue
        except Exception as exc:
            print(f"[SKIP] Snapshot invalido: {snapshot_path.name} -> {exc}")
            archive_related_assets(bridge, snapshot_path, image_path)
            continue

        symbol = str(snapshot.get("symbol", "")).strip()
        candles = snapshot.get("candles") or []
        if not symbol or not isinstance(candles, list):
            print(f"[SKIP] Snapshot sem estrutura valida: {snapshot_path.name}")
            archive_related_assets(bridge, snapshot_path, image_path)
            continue

        snapshot["symbol"] = symbol
        snapshot["local_memory"] = memory.get_symbol_context(symbol)
        snapshot["visual_shadow_requested"] = config.visual_shadow_enabled
        snapshot["worker_owner"] = WORKER_OWNER

        image_path = bridge.find_chart_image(snapshot_path, snapshot)
        if image_path is not None:
            try:
                image_bytes = bridge.read_bytes(image_path)
                snapshot["chart_image_base64"] = base64.b64encode(image_bytes).decode("ascii")
                snapshot["chart_image_sha256"] = hashlib.sha256(image_bytes).hexdigest()
            except PermissionError:
                print(f"[RETRY] Imagem ainda em escrita: {image_path.name}")
                continue
            except Exception as exc:
                print(f"[WARN] Imagem do ciclo invalida {image_path.name}: {exc}")

        sync_open_trade(snapshot, client, memory, config)

        try:
            response = client.request_decision(build_signal_payload(snapshot, config))
            decision = build_command_payload(response, snapshot)
            if decision.get("signal") in {"BUY", "SELL"} and decision.get("decision_id"):
                memory.remember_pending_decision(symbol, str(decision["decision_id"]))
            action = decision.get("position_action") or decision.get("signal")
            print(f"[REMOTE] {symbol} -> {action} ({decision.get('reason', '-')})")
            if response.get("visual_shadow_status"):
                print(
                    f"[SHADOW] {symbol} -> {response.get('visual_shadow_status')} / "
                    f"{response.get('visual_alignment') or 'not_applicable'}"
                )
        except Exception as exc:
            print(f"[FALLBACK] {symbol} -> {exc}")
            try:
                decision = normalize_decision(local_fallback(snapshot), "fallback_local_agent")
            except Exception as fallback_exc:
                print(f"[HOLD] fallback invalido para {symbol}: {fallback_exc}")
                decision = normalize_decision({}, "fallback_indisponivel")

        try:
            bridge.write_command(symbol, decision)
            memory.record_decision(snapshot, decision)
        except Exception as exc:
            print(f"[ERROR] Falha ao processar snapshot {snapshot_path.name}: {exc}")
        finally:
            archive_related_assets(bridge, snapshot_path, image_path)


def process_feedback(bridge: BridgeFilesystem, client: BackendClient, memory: MemoryStore, config: AgentConfig) -> None:
    for feedback_path in bridge.pending_feedback():
        try:
            payload = bridge.load_json(feedback_path)
        except PermissionError:
            print(f"[RETRY] Feedback ainda em escrita: {feedback_path.name}")
            continue
        except Exception as exc:
            print(f"[SKIP] Feedback invalido: {feedback_path.name} -> {exc}")
            archive_safely(bridge, feedback_path, "Feedback")
            continue

        symbol = str(payload.get("symbol", "")).strip()
        missing_keys = [
            key
            for key in ("symbol", "outcome", "pnl", "closed_at", "ticket", "volume")
            if key not in payload
        ]
        if not symbol or missing_keys:
            print(f"[SKIP] Feedback incompleto: {feedback_path.name}")
            archive_safely(bridge, feedback_path, "Feedback")
            continue

        decision_id = memory.get_active_decision_id(symbol) or memory.get_pending_decision(symbol)

        try:
            backend_payload = build_trade_feedback_payload(payload, config, decision_id)
            client.send_trade_feedback(backend_payload)
        except Exception as exc:
            print(f"[RETRY] Feedback pendente: {feedback_path.name} -> {exc}")
            continue

        try:
            memory.record_feedback(payload)
            memory.clear_active_trade(symbol)
        except Exception as exc:
            print(f"[WARN] Falha ao gravar memoria de feedback {feedback_path.name}: {exc}")

        archive_safely(bridge, feedback_path, "Feedback")
        print(f"[FEEDBACK] {payload.get('symbol')} -> {payload.get('outcome')} {payload.get('pnl')}")


def run(config_path: Path) -> None:
    config = AgentConfig.load(config_path)
    bridge = BridgeFilesystem(
        snapshot_dir=config.snapshot_dir,
        command_dir=config.command_dir,
        feedback_dir=config.feedback_dir,
        metadata_dir=config.metadata_dir,
        archive_dir=config.archive_dir,
    )
    client = BackendClient(
        base_url=config.backend_url,
        robot_token=config.robot_token,
        timeout=config.request_timeout_seconds,
    )
    memory = MemoryStore(config.memory_db_path)
    last_heartbeat_at = 0.0
    last_runtime_sync_at = 0.0

    print("Agente local iniciado.")
    print(f"Backend: {config.backend_url}")
    print(f"Runtime: {AGENT_RUNTIME}")
    print(f"Snapshots: {config.snapshot_dir}")
    print(f"Comandos: {config.command_dir}")

    while True:
        try:
            if time.time() - last_runtime_sync_at >= config.runtime_config_interval_seconds:
                runtime_status = sync_runtime_settings(bridge, client, config)
                last_runtime_sync_at = time.time()
                print(f"[RUNTIME] {runtime_status}")

            process_metadata(bridge, client)
            process_snapshots(bridge, client, memory, config)
            process_feedback(bridge, client, memory, config)

            if time.time() - last_heartbeat_at >= config.heartbeat_interval_seconds:
                client.send_heartbeat(build_heartbeat_payload(config, 0.0))
                last_heartbeat_at = time.time()
                print("[HEARTBEAT] ativo")
        except Exception as exc:
            print(f"[LOOP] erro inesperado no ciclo principal: {exc}")

        time.sleep(config.poll_interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente local do Vuno Trader")
    parser.add_argument("--config", required=True, help="Caminho para o arquivo de configuracao JSON")
    args = parser.parse_args()
    run(Path(args.config))


if __name__ == "__main__":
    main()
