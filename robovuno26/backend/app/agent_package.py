from __future__ import annotations

import io
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .instrument_catalog import get_profile_label


REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / "agent-local"
MT5_DIR = REPO_ROOT / "mt5"
PACKAGE_ROOT = "vuno-robo"
AGENT_EXCLUDED_PARTS = {"__pycache__", ".venv", "dist", "runtime"}
MT5_EXCLUDED_PARTS = {"__pycache__"}
AGENT_BINARY_PATH = AGENT_DIR / "dist" / "vuno-agent.exe"


def build_runtime_config(
    backend_url: str,
    robot_token: str,
    bridge_name: str,
    broker_profile: str,
    primary_symbol: str,
    chart_timeframe: str,
    selected_symbols: list[str],
) -> dict[str, object]:
    return {
        "backend_url": backend_url,
        "robot_token": robot_token,
        "bridge_name": bridge_name,
        "broker_profile": broker_profile,
        "primary_symbol": primary_symbol,
        "chart_timeframe": chart_timeframe,
        "selected_symbols": selected_symbols,
        "poll_interval_seconds": 2,
        "heartbeat_interval_seconds": 10,
        "runtime_config_interval_seconds": 20,
        "max_snapshot_age_seconds": 45,
        "request_timeout_seconds": 12,
        "snapshot_dir": "runtime/bridge/in",
        "command_dir": "runtime/bridge/out",
        "feedback_dir": "runtime/bridge/feedback",
        "metadata_dir": "runtime/bridge/metadata",
        "archive_dir": "runtime/archive",
    }


def ensure_package_sources() -> None:
    missing = [str(path) for path in (AGENT_DIR, MT5_DIR) if not path.exists()]
    if missing:
        raise FileNotFoundError("Arquivos do pacote do robo nao estao disponiveis no servidor.")


def iter_tree_files(base_dir: Path, archive_root: str, excluded_parts: set[str]):
    for path in sorted(base_dir.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(base_dir)
        if any(part in excluded_parts for part in relative_path.parts):
            continue

        yield path, f"{PACKAGE_ROOT}/{archive_root}/{relative_path.as_posix()}"


def has_agent_binary() -> bool:
    return AGENT_BINARY_PATH.exists() and AGENT_BINARY_PATH.is_file()


def get_package_delivery_mode() -> str:
    return "exe" if has_agent_binary() else "python"


def build_quick_start(
    instance_name: str,
    mode: str,
    binary_available: bool,
    bridge_name: str,
    broker_profile: str,
    primary_symbol: str,
    chart_timeframe: str,
    selected_symbols: list[str],
) -> str:
    profile_label = get_profile_label(broker_profile)
    setup_symbol = primary_symbol or (selected_symbols[0] if selected_symbols else "")
    additional_symbols = [symbol for symbol in selected_symbols if symbol != setup_symbol]
    lines = [
        "Vuno Trader - pacote pronto do robo",
        "",
        f"Instancia: {instance_name}",
        f"Modo: {mode}",
        f"Bridge MT5: {bridge_name}",
        f"Perfil de mercado: {profile_label}",
        f"Timeframe do grafico: {chart_timeframe}",
        "",
        "Passo a passo rapido:",
        "1. Extraia este zip em qualquer pasta sua.",
        "2. Abra agent-local/iniciar-vuno-robo.cmd com duplo clique.",
        "3. No MT5, copie mt5/VunoRemoteBridge.mq5 e a pasta mt5/vuno-bridge para MQL5/Experts.",
        f"4. Compile o EA, anexe no grafico e use InpBridgeRoot={bridge_name}.",
        "5. Durante homologacao, mantenha InpAllowRealTrading=false.",
        "6. Assim que o agente ligar, o painel recebe automaticamente os simbolos e o timeframe detectados pelo MT5.",
        "7. Volte ao painel e confirme ACTIVE + ONLINE.",
        "",
        "Observacao: runtime/config.json ja sai preenchido com a chave desta instancia.",
    ]

    if setup_symbol:
        additional_symbols_label = ", ".join(additional_symbols)
        lines.extend(
            [
                "",
                "Ativos configurados para esta instancia:",
                ", ".join(selected_symbols),
                f"No MT5, abra o EA em um grafico de {setup_symbol} no timeframe {chart_timeframe}.",
                (
                    f"Se quiser rodar varios ativos com esta mesma instancia, preencha InpAdditionalSymbols com: {additional_symbols_label}."
                    if additional_symbols_label
                    else "Como esta instancia tem um unico ativo principal, InpAdditionalSymbols pode ficar vazio."
                ),
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Nenhum ativo foi fixado nesta instancia.",
                "Voce pode escolher o ativo principal no grafico do MT5 e usar InpAdditionalSymbols depois, se quiser varios simbolos.",
            ]
        )

    if binary_available:
        lines.extend(
            [
                "",
                "Este pacote inclui agent-local/dist/vuno-agent.exe.",
                "O atalho iniciar-vuno-robo.cmd vai usar o executavel automaticamente, sem depender de Python na maquina do usuario.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Neste build o executavel ainda nao foi anexado.",
                "O atalho vai preparar o ambiente Python automaticamente antes de iniciar o agente.",
            ]
        )

    return "\n".join(lines)


def build_agent_package(
    robot_name: str,
    robot_token: str,
    backend_url: str,
    mode: str,
    bridge_name: str,
    broker_profile: str,
    primary_symbol: str,
    chart_timeframe: str,
    selected_symbols: list[str],
) -> bytes:
    ensure_package_sources()
    package_buffer = io.BytesIO()
    binary_available = get_package_delivery_mode() == "exe"

    with ZipFile(package_buffer, "w", compression=ZIP_DEFLATED) as archive:
        for source_path, archive_path in iter_tree_files(AGENT_DIR, "agent-local", AGENT_EXCLUDED_PARTS):
            archive.write(source_path, archive_path)

        if binary_available:
            archive.write(AGENT_BINARY_PATH, f"{PACKAGE_ROOT}/agent-local/dist/vuno-agent.exe")

        for source_path, archive_path in iter_tree_files(MT5_DIR, "mt5", MT5_EXCLUDED_PARTS):
            archive.write(source_path, archive_path)

        runtime_config = json.dumps(
            build_runtime_config(
                backend_url=backend_url,
                robot_token=robot_token,
                bridge_name=bridge_name,
                broker_profile=broker_profile,
                primary_symbol=primary_symbol,
                chart_timeframe=chart_timeframe,
                selected_symbols=selected_symbols,
            ),
            indent=2,
            ensure_ascii=True,
        )
        archive.writestr(f"{PACKAGE_ROOT}/agent-local/runtime/config.json", f"{runtime_config}\n")
        archive.writestr(
            f"{PACKAGE_ROOT}/LEIA-PRIMEIRO.txt",
            build_quick_start(
                robot_name,
                mode,
                binary_available=binary_available,
                bridge_name=bridge_name,
                broker_profile=broker_profile,
                primary_symbol=primary_symbol,
                chart_timeframe=chart_timeframe,
                selected_symbols=selected_symbols,
            ),
        )

    return package_buffer.getvalue()


def slugify_instance_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "instancia"


def build_agent_package_filename(robot_name: str, mode: str) -> str:
    safe_mode = re.sub(r"[^a-z0-9]+", "-", mode.lower()).strip("-") or "demo"
    return f"vuno-robo-{safe_mode}-{slugify_instance_name(robot_name)}.zip"