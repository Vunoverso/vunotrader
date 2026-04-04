from __future__ import annotations

try:
    from .api_client import BackendClient
    from .bridge import BridgeFilesystem
except ImportError:
    from api_client import BackendClient
    from bridge import BridgeFilesystem


def build_mt5_runtime_settings(payload: dict) -> dict:
    params = payload["parameters"]
    return {
        "version": 1,
        "robot_instance_id": payload["robot_instance_id"],
        "robot_name": payload["robot_name"],
        "trading_mode": payload["robot_mode"],
        "risk_per_trade": params["risk_per_trade"],
        "max_spread_points": params["max_spread_points"],
        "default_lot": params["default_lot"],
        "stop_loss_points": params["stop_loss_points"],
        "take_profit_points": params["take_profit_points"],
        "max_positions_per_symbol": params["max_positions_per_symbol"],
        "reentry_cooldown_seconds": params["reentry_cooldown_seconds"],
        "max_command_age_seconds": params["max_command_age_seconds"],
        "deviation_points": params["deviation_points"],
        "execution_retries": params["execution_retries"],
        "pause_new_orders": 1 if params["pause_new_orders"] else 0,
        "use_local_fallback": 1 if params["use_local_fallback"] else 0,
    }


def sync_runtime_settings(bridge: BridgeFilesystem, client: BackendClient) -> dict:
    payload = client.get_runtime_config()
    settings = build_mt5_runtime_settings(payload)
    bridge.write_runtime_settings(settings)
    return settings