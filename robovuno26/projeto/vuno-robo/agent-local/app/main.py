from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from .api_client import BackendClient
    from .bridge import BridgeFilesystem
    from .config import AgentConfig
    from .memory import MemoryStore
    from .runtime_contract import sync_runtime_settings
except ImportError:
    from api_client import BackendClient
    from bridge import BridgeFilesystem
    from config import AgentConfig
    from memory import MemoryStore
    from runtime_contract import sync_runtime_settings


AGENT_RUNTIME = "exe" if getattr(sys, "frozen", False) else "python"


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


def to_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_position_action(value: object) -> str:
    action = str(value or "NONE").upper().strip()
    return action if action in {"NONE", "PROTECT", "CLOSE"} else "NONE"


def normalize_decision(decision: dict, fallback_reason: str) -> dict:
    signal = str(decision.get("signal", "HOLD")).upper().strip()
    if signal not in {"BUY", "SELL", "HOLD"}:
        signal = "HOLD"

    confidence = max(0.0, min(to_float(decision.get("confidence", 0.0), 0.0), 1.0))
    risk = max(0.0, min(to_float(decision.get("risk", 0.0), 0.0), 1.0))
    stop_loss = max(0, to_int(decision.get("stop_loss_points", 0), 0))
    take_profit = max(0, to_int(decision.get("take_profit_points", 0), 0))
    reason = str(decision.get("reason") or decision.get("rationale") or fallback_reason).strip()
    position_action = normalize_position_action(decision.get("position_action", "NONE"))

    if signal == "HOLD":
        risk = 0.0
        stop_loss = 0
        take_profit = 0

    normalized = {
        "signal": signal,
        "confidence": confidence,
        "risk": risk,
        "stop_loss_points": stop_loss,
        "take_profit_points": take_profit,
        "position_action": position_action,
        "reason": reason or fallback_reason,
    }

    if decision.get("position_ticket") is not None:
        normalized["position_ticket"] = to_int(decision.get("position_ticket"), 0)
    if decision.get("position_stop_loss") is not None:
        normalized["position_stop_loss"] = to_float(decision.get("position_stop_loss"), 0.0)
    if decision.get("position_take_profit") is not None:
        normalized["position_take_profit"] = to_float(decision.get("position_take_profit"), 0.0)

    return normalized


def should_skip_snapshot(path: Path, max_age_seconds: int) -> bool:
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return True
    return age > max_age_seconds


def send_heartbeat(bridge: BridgeFilesystem, client: BackendClient) -> None:
    payload = {
        "status": "ACTIVE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "details": {
            "agent_runtime": AGENT_RUNTIME,
            "pending_snapshots": len(bridge.pending_snapshots()),
            "pending_feedback": len(bridge.pending_feedback()),
        },
    }
    client.send_heartbeat(payload)


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


def process_snapshots(
    bridge: BridgeFilesystem,
    client: BackendClient,
    memory: MemoryStore,
    config: AgentConfig,
) -> None:
    for snapshot_path in bridge.pending_snapshots():
        if should_skip_snapshot(snapshot_path, config.max_snapshot_age_seconds):
            print(f"[STALE] Snapshot expirado: {snapshot_path.name}")
            archive_safely(bridge, snapshot_path, "Snapshot")
            continue

        try:
            snapshot = bridge.load_json(snapshot_path)
        except PermissionError:
            print(f"[RETRY] Snapshot ainda em escrita: {snapshot_path.name}")
            continue
        except Exception as exc:
            print(f"[SKIP] Snapshot invalido: {snapshot_path.name} -> {exc}")
            archive_safely(bridge, snapshot_path, "Snapshot")
            continue

        symbol = str(snapshot.get("symbol", "")).strip()
        if not symbol:
            print(f"[SKIP] Snapshot sem symbol: {snapshot_path.name}")
            archive_safely(bridge, snapshot_path, "Snapshot")
            continue

        snapshot["symbol"] = symbol
        snapshot["local_memory"] = memory.get_symbol_context(symbol)

        try:
            response = client.request_decision(snapshot)
            remote_decision = response.get("decision", {})
            decision = normalize_decision(remote_decision, "remote_sem_payload_valido")
            print(f"[REMOTE] {symbol} -> {decision['signal']} ({decision['reason']})")
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
            archive_safely(bridge, snapshot_path, "Snapshot")


def process_feedback(
    bridge: BridgeFilesystem,
    client: BackendClient,
    memory: MemoryStore,
) -> None:
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

        missing_keys = [
            key
            for key in ("symbol", "outcome", "pnl", "closed_at", "ticket", "volume")
            if key not in payload
        ]
        if missing_keys:
            print(f"[SKIP] Feedback incompleto: {feedback_path.name} -> faltando {', '.join(missing_keys)}")
            archive_safely(bridge, feedback_path, "Feedback")
            continue

        try:
            payload["pnl"] = float(payload["pnl"])
            payload["volume"] = float(payload["volume"])
            payload["ticket"] = int(payload["ticket"])
        except (TypeError, ValueError) as exc:
            print(f"[SKIP] Feedback com tipos invalidos: {feedback_path.name} -> {exc}")
            archive_safely(bridge, feedback_path, "Feedback")
            continue

        try:
            client.send_trade_feedback(payload)
        except Exception as exc:
            print(f"[RETRY] Feedback pendente: {feedback_path.name} -> {exc}")
            continue

        try:
            memory.record_feedback(payload)
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
    print(f"Snapshots: {config.snapshot_dir}")
    print(f"Comandos: {config.command_dir}")

    while True:
        try:
            if time.time() - last_runtime_sync_at >= config.runtime_config_interval_seconds:
                try:
                    settings = sync_runtime_settings(bridge, client)
                    last_runtime_sync_at = time.time()
                    print(f"[RUNTIME] sincronizado modo={settings['trading_mode']}")
                except Exception as exc:
                    print(f"[RUNTIME] falha -> {exc}")

            process_snapshots(bridge, client, memory, config)
            process_feedback(bridge, client, memory)

            if time.time() - last_heartbeat_at >= config.heartbeat_interval_seconds:
                try:
                    send_heartbeat(bridge, client)
                    last_heartbeat_at = time.time()
                    print("[HEARTBEAT] ativo")
                except Exception as exc:
                    print(f"[HEARTBEAT] falha -> {exc}")
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
