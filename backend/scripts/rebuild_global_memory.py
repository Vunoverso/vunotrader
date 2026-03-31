"""
rebuild_global_memory.py
========================
Reconstrói a memória global agregada a partir de anonymized_trade_events.

Uso:
  python backend/scripts/rebuild_global_memory.py --days 180 --min-samples 20
  python backend/scripts/rebuild_global_memory.py --days 180 --min-samples 20 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone


def _make_client():
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias.")

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("Instale dependência: pip install supabase") from exc

    return create_client(url, key)


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _build_fingerprint(row: dict) -> str:
    conf = _to_float(row.get("confidence"), 0.0)
    risk = _to_float(row.get("risk_pct"), 0.0)
    vol = _to_float(row.get("volatility"), 0.0)

    # Buckets simples para reduzir ruído e preservar anonimização.
    payload = {
        "conf_bucket": round(conf, 1),
        "risk_bucket": round(risk * 2) / 2,
        "vol_bucket": round(vol, 4),
        "mode": str(row.get("mode") or "demo").lower(),
        "side": str(row.get("side") or "hold").lower(),
        "regime": str(row.get("regime") or "lateral").lower(),
        "symbol": str(row.get("symbol") or "UNKNOWN").upper(),
        "timeframe": str(row.get("timeframe") or "M5").upper(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fetch_events(client, days: int) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    resp = (
        client.table("anonymized_trade_events")
        .select("symbol,timeframe,regime,side,mode,confidence,risk_pct,result,pnl_points,volatility,created_at")
        .gte("created_at", since)
        .order("created_at")
        .limit(100000)
        .execute()
    )
    return list(resp.data or [])


def _aggregate(rows: list[dict], min_samples: int) -> list[dict]:
    grouped: dict[tuple, dict] = {}

    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN").upper()
        timeframe = str(row.get("timeframe") or "M5").upper()
        regime = str(row.get("regime") or "lateral").lower()
        side = str(row.get("side") or "hold").lower()
        mode = str(row.get("mode") or "demo").lower()
        result = str(row.get("result") or "").lower()
        if side not in {"buy", "sell", "hold"}:
            side = "hold"
        if mode not in {"observer", "demo", "real"}:
            mode = "demo"

        fp = _build_fingerprint(row)
        key = (symbol, timeframe, regime, side, mode, fp)

        cur = grouped.setdefault(
            key,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "regime": regime,
                "side": side,
                "mode": mode,
                "config_fingerprint": fp,
                "sample_size": 0,
                "wins": 0,
                "losses": 0,
                "breakevens": 0,
                "sum_pnl": 0.0,
                "sum_conf": 0.0,
                "sum_risk": 0.0,
                "last_event_at": None,
            },
        )

        cur["sample_size"] += 1
        if result == "win":
            cur["wins"] += 1
        elif result == "loss":
            cur["losses"] += 1
        else:
            cur["breakevens"] += 1

        cur["sum_pnl"] += _to_float(row.get("pnl_points"), 0.0)
        cur["sum_conf"] += _to_float(row.get("confidence"), 0.0)
        cur["sum_risk"] += _to_float(row.get("risk_pct"), 0.0)

        created_at = row.get("created_at")
        if created_at and (cur["last_event_at"] is None or str(created_at) > str(cur["last_event_at"])):
            cur["last_event_at"] = created_at

    output: list[dict] = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for data in grouped.values():
        n = int(data["sample_size"])
        if n < min_samples:
            continue
        wins = int(data["wins"])
        losses = int(data["losses"])
        breakevens = int(data["breakevens"])
        win_rate = wins / n if n > 0 else 0.0

        output.append(
            {
                "symbol": data["symbol"],
                "timeframe": data["timeframe"],
                "regime": data["regime"],
                "side": data["side"],
                "mode": data["mode"],
                "config_fingerprint": data["config_fingerprint"],
                "sample_size": n,
                "wins": wins,
                "losses": losses,
                "breakevens": breakevens,
                "win_rate": round(win_rate, 4),
                "avg_pnl_points": round(data["sum_pnl"] / n, 4),
                "avg_confidence": round(data["sum_conf"] / n, 4),
                "avg_risk_pct": round(data["sum_risk"] / n, 4),
                "last_event_at": data["last_event_at"],
                "computed_at": now_iso,
                "raw_stats": {
                    "win_rate": round(win_rate, 6),
                    "wins": wins,
                    "losses": losses,
                    "breakevens": breakevens,
                    "samples": n,
                },
            }
        )

    output.sort(key=lambda x: (x["sample_size"], x["win_rate"]), reverse=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild memória global agregada")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--min-samples", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        client = _make_client()
        rows = _fetch_events(client, args.days)
        if not rows:
            print("Sem eventos no período.")
            return 2

        aggregated = _aggregate(rows, args.min_samples)
        if not aggregated:
            print("Sem grupos suficientes para memória global.")
            return 2

        print(f"Eventos lidos: {len(rows)}")
        print(f"Grupos agregados: {len(aggregated)}")

        if args.dry_run:
            print("Dry run ativo. Sem escrita no banco.")
            print(json.dumps(aggregated[:5], ensure_ascii=False, indent=2))
            return 0

        # Rebuild simples: limpa e repopula.
        client.table("global_memory_signals").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        for i in range(0, len(aggregated), 500):
            batch = aggregated[i : i + 500]
            client.table("global_memory_signals").upsert(
                batch,
                on_conflict="symbol,timeframe,regime,side,mode,config_fingerprint",
            ).execute()

        print("Memória global reconstruída com sucesso.")
        return 0
    except Exception as exc:
        print(f"Erro: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
