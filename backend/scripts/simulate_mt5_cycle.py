import json
import random
import socket
import time

USER_ID = "96fd6e0d-ae81-4eeb-b6fd-37279373a7db"
ORG_ID = "24affdc3-dc7b-4672-b20d-65033949bb76"


def send_payload(payload: dict) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(15)
    s.connect(("127.0.0.1", 9999))
    s.sendall(json.dumps(payload).encode("utf-8"))
    raw = s.recv(65536).decode("utf-8")
    s.close()
    return json.loads(raw)


def build_candles(n: int = 120) -> list[list[float]]:
    now = int(time.time())
    price = 130000.0
    candles: list[list[float]] = []
    for i in range(n):
        t = now - (n - i) * 60
        o = price + random.uniform(-25, 25)
        c = o + random.uniform(-30, 30)
        h = max(o, c) + random.uniform(0, 15)
        l = min(o, c) - random.uniform(0, 15)
        v = random.uniform(100, 1000)
        candles.append([t, o, h, l, c, v])
        price = c
    return candles


def main() -> None:
    market_data = {
        "type": "MARKET_DATA",
        "symbol": "WINM26",
        "timeframe": "M5",
        "mode": "demo",
        "user_id": USER_ID,
        "organization_id": ORG_ID,
        "candles": build_candles(),
    }

    resp = send_payload(market_data)
    print("MARKET_DATA_RESPONSE", resp)

    decision_id = resp.get("decision_id")
    if not decision_id:
        raise RuntimeError("Sem decision_id na resposta do brain")

    trade_result = {
        "type": "TRADE_RESULT",
        "ticket": "900001",
        "decision_id": decision_id,
        "mode": "demo",
        "user_id": USER_ID,
        "organization_id": ORG_ID,
        "entry_price": 130000.0,
        "stop_loss": 129500.0,
        "take_profit": 130800.0,
        "lot": 1.0,
        "profit": 250.0,
        "points": 50,
        "symbol": "WINM26",
    }

    resp2 = send_payload(trade_result)
    print("TRADE_RESULT_RESPONSE", resp2)
    print("DECISION_ID", decision_id)


if __name__ == "__main__":
    main()
