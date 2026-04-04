from __future__ import annotations

import json
import re
from typing import Any


INSTRUMENT_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "FOREX_GLOBAL",
        "label": "Forex internacional",
        "description": "Pares maiores e metais comuns em corretoras globais de MT5.",
        "suggested_symbols": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "XAUUSD"],
        "note": "Algumas corretoras usam sufixos no simbolo, como EURUSD.a ou XAUUSDm.",
    },
    {
        "profile_id": "B3_FUTURES",
        "label": "Futuros Brasil (B3)",
        "description": "Mini indice e mini dolar dependem do vencimento configurado pela corretora.",
        "suggested_symbols": ["WINJ26", "WDOJ26"],
        "note": "Confirme o vencimento e o nome exato no Market Watch do MT5 antes de salvar.",
    },
    {
        "profile_id": "INDICES_E_CFD",
        "label": "Indices e CFD",
        "description": "Indices globais e contratos sinteticos oferecidos por algumas corretoras.",
        "suggested_symbols": ["US30", "NAS100", "GER40"],
        "note": "Os nomes podem variar entre US30, DJ30, NAS100.cash e formatos parecidos.",
    },
    {
        "profile_id": "CUSTOM",
        "label": "Personalizado",
        "description": "Use os simbolos exatos exibidos no Market Watch da sua corretora.",
        "suggested_symbols": [],
        "note": "Ideal quando a corretora usa sufixos, prefixos ou nomes proprietarios.",
    },
)

VALID_PROFILE_IDS = {str(profile["profile_id"]) for profile in INSTRUMENT_PROFILES}
SYMBOL_SPLIT_PATTERN = re.compile(r"[\r\n,;]+")
MAX_SELECTED_SYMBOLS = 12
MAX_DISCOVERED_SYMBOLS = 2500


def normalize_symbol_token(value: Any) -> str:
    symbol = str(value or "").strip()
    if not symbol:
        return ""
    if len(symbol) > 40:
        raise ValueError("cada simbolo deve ter ate 40 caracteres")
    return symbol


def normalize_symbol_list(value: Any, *, max_items: int) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        raw_items = SYMBOL_SPLIT_PATTERN.split(value)
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raise ValueError("lista de simbolos invalida")

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_items:
        symbol = normalize_symbol_token(raw_item)
        if not symbol:
            continue
        dedupe_key = symbol.upper()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized.append(symbol)

    if len(normalized) > max_items:
        raise ValueError(f"lista de simbolos aceita no maximo {max_items} itens")

    return normalized


def list_instrument_profiles() -> list[dict[str, Any]]:
    return [dict(profile) for profile in INSTRUMENT_PROFILES]


def normalize_broker_profile(value: str | None) -> str:
    normalized = (value or "CUSTOM").strip().upper()
    if normalized not in VALID_PROFILE_IDS:
        raise ValueError("broker_profile invalido")
    return normalized


def get_profile_label(profile_id: str | None) -> str:
    normalized = normalize_broker_profile(profile_id)
    for profile in INSTRUMENT_PROFILES:
        if profile["profile_id"] == normalized:
            return str(profile["label"])
    return "Personalizado"


def normalize_selected_symbols(value: Any) -> list[str]:
    try:
        return normalize_symbol_list(value, max_items=MAX_SELECTED_SYMBOLS)
    except ValueError as exc:
        raise ValueError("selected_symbols deve ser lista de strings ou texto separado por virgula") from exc


def normalize_catalog_symbols(value: Any) -> list[str]:
    return normalize_symbol_list(value, max_items=MAX_DISCOVERED_SYMBOLS)


def normalize_primary_symbol(value: Any) -> str:
    return normalize_symbol_token(value)


def merge_primary_symbol(primary_symbol: Any, selected_symbols: Any) -> tuple[str, list[str]]:
    primary = normalize_primary_symbol(primary_symbol)
    selected = normalize_selected_symbols(selected_symbols)

    if not primary and selected:
        primary = selected[0]

    if not primary:
        return "", selected

    merged = [primary]
    primary_key = primary.upper()
    for symbol in selected:
        if symbol.upper() == primary_key:
            continue
        merged.append(symbol)

    if len(merged) > MAX_SELECTED_SYMBOLS:
        raise ValueError(f"selected_symbols aceita no maximo {MAX_SELECTED_SYMBOLS} ativos por instancia")

    return primary, merged


def serialize_selected_symbols(symbols: Any) -> str:
    normalized = normalize_selected_symbols(symbols)
    return json.dumps(normalized, ensure_ascii=True)


def serialize_catalog_symbols(symbols: Any) -> str:
    normalized = normalize_catalog_symbols(symbols)
    return json.dumps(normalized, ensure_ascii=True)


def parse_selected_symbols(raw_payload: object) -> list[str]:
    if not raw_payload:
        return []

    try:
        payload = json.loads(str(raw_payload))
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    return normalize_selected_symbols(payload)


def parse_discovered_symbols(raw_payload: object) -> list[str]:
    if not raw_payload:
        return []

    try:
        payload = json.loads(str(raw_payload))
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    return normalize_catalog_symbols(payload)


def build_bridge_name(robot_instance_id: int) -> str:
    safe_id = max(int(robot_instance_id), 1)
    return f"VunoBridge-{safe_id}"