from __future__ import annotations

import json
from typing import Any
from urllib import error, request


class BackendClient:
    def __init__(self, base_url: str, robot_token: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.robot_token = robot_token
        self.timeout = timeout

    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(
            url=f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={
                "Content-Type": "application/json",
                "X-Device-Token": self.robot_token,
                "X-Robot-Token": self.robot_token,
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                data = response.read().decode("utf-8")
                return json.loads(data)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Falha ao conectar no backend: {exc.reason}") from exc

    def request_decision(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/agent/decision", snapshot)

    def send_trade_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/agent/trade-feedback", payload)

    def send_trade_opened(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/agent/trade-opened", payload)

    def send_heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/agent/heartbeat", payload)

    def get_runtime_config(self) -> dict[str, Any]:
        return self._call("GET", "/api/agent/runtime-config")

    def send_symbol_catalog(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._call("POST", "/api/agent/symbol-catalog", payload)
