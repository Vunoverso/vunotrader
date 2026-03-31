from __future__ import annotations

import os
import time
import json
from pathlib import Path

from supabase import create_client

from scripts.mt5_cmd_bot import (
    ConnectionConfig,
    MT5Controller,
    VunoAuditLogger,
    build_vuno_engine,
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        k = key.strip()
        v = value.strip().strip('"')
        if not os.getenv(k):
            os.environ[k] = v


def ensure_identity_from_db() -> None:
    if os.getenv("BRAIN_USER_ID") and os.getenv("BRAIN_ORG_ID"):
        return

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        return

    client = create_client(url, key)
    latest = (
        client.table("trade_decisions")
        .select("user_id,organization_id,robot_instance_id")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    row = (latest.data or [{}])[0]
    if row.get("user_id"):
        os.environ.setdefault("BRAIN_USER_ID", str(row["user_id"]))
    if row.get("organization_id"):
        os.environ.setdefault("BRAIN_ORG_ID", str(row["organization_id"]))
    if row.get("robot_instance_id"):
        os.environ.setdefault("MT5_ROBOT_INSTANCE_ID", str(row["robot_instance_id"]))


def main() -> int:
    report: dict[str, object] = {"status": "starting"}
    load_dotenv(Path("brain.env"))
    load_dotenv(Path("backend/.env"))
    os.environ["VUNO_AUDIT_ENABLED"] = "1"
    os.environ.setdefault("VUNO_AUDIT_MODE", "demo")
    ensure_identity_from_db()

    controller = MT5Controller(
        ConnectionConfig(
            login=None,
            password="",
            server="",
            path="",
            timeout_ms=60000,
            portable=False,
        )
    )

    engine = build_vuno_engine()
    audit = VunoAuditLogger()
    if not audit.active:
        report.update({"status": "fail", "reason": "audit_logger_inactive"})
        Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
        print("PHASE1_FAIL: audit logger inativo")
        return 2

    symbol = "EURUSD"
    timeframe = "M1"
    volume = 0.01

    controller.connect()
    try:
        # Limpa posições residuais no símbolo antes do ciclo.
        for pos in controller.get_positions(symbol):
            controller.close_position(pos.ticket, deviation=20, magic=20260331, comment="phase1-preclose")

        frame = controller.get_rates(symbol, timeframe, 400)
        analysis = engine.analyze_market(frame, win_rate=0.56, mode="demo")
        signal = str(analysis.get("signal", "HOLD") or "HOLD").upper()
        confidence = float(analysis.get("confidence", 0.0) or 0.0)
        risk = float(analysis.get("risk", 0.0) or 0.0)
        rationale = str(analysis.get("rationale", "") or "")

        if signal not in {"BUY", "SELL"}:
            signal = "BUY"
            rationale = (rationale + " | override=phase1-smoke-force-buy").strip(" |")

        report.update(
            {
                "status": "running",
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal,
                "confidence": confidence,
                "risk": risk,
            }
        )

        decision_id = audit.log_decision(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal,
            confidence=confidence,
            risk_pct=risk,
            rationale=rationale,
        )
        if not decision_id:
            report.update({"status": "fail", "reason": "decision_not_logged"})
            Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
            print("PHASE1_FAIL: decision not logged")
            return 3

        open_result = controller.send_market_order(
            symbol=symbol,
            side=signal.lower(),
            volume=volume,
            deviation=20,
            magic=20260331,
            comment="phase1-open",
            sl_points=120,
            tp_points=120,
        )
        broker_ticket = int(getattr(open_result, "order", 0) or 0) or int(getattr(open_result, "deal", 0) or 0)
        if int(getattr(open_result, "retcode", 0) or 0) != 10009 or broker_ticket <= 0:
            report.update(
                {
                    "status": "fail",
                    "reason": "open_failed",
                    "open_retcode": int(getattr(open_result, "retcode", 0) or 0),
                    "broker_ticket": broker_ticket,
                }
            )
            Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
            print(f"PHASE1_FAIL: open failed retcode={getattr(open_result, 'retcode', None)}")
            return 4

        executed_trade_id = audit.log_trade_open(
            decision_id=decision_id,
            broker_ticket=str(broker_ticket),
            entry_price=float(getattr(open_result, "price", 0.0) or 0.0),
            stop_loss=120.0,
            take_profit=120.0,
            lot=volume,
        )
        if not executed_trade_id:
            report.update({"status": "fail", "reason": "open_not_logged", "decision_id": decision_id})
            Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
            print("PHASE1_FAIL: open not logged")
            return 5

        time.sleep(3)
        close_result = controller.close_position(broker_ticket, deviation=20, magic=20260331, comment="phase1-close")
        if int(getattr(close_result, "retcode", 0) or 0) != 10009:
            report.update(
                {
                    "status": "fail",
                    "reason": "close_failed",
                    "decision_id": decision_id,
                    "executed_trade_id": executed_trade_id,
                    "close_retcode": int(getattr(close_result, "retcode", 0) or 0),
                }
            )
            Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
            print(f"PHASE1_FAIL: close failed retcode={getattr(close_result, 'retcode', None)}")
            return 6

        time.sleep(2)
        close_info = controller.get_closed_position_result(broker_ticket) or {
            "pnl_money": 0.0,
            "pnl_points": 0.0,
            "result": "breakeven",
            "reason": f"Fechamento detectado no MT5 para ticket {broker_ticket}",
        }
        audit.log_trade_close(
            executed_trade_id=executed_trade_id,
            pnl_money=float(close_info["pnl_money"]),
            pnl_points=float(close_info["pnl_points"]),
            result=str(close_info["result"]),
            reason=str(close_info["reason"]),
        )

        report.update(
            {
                "status": "ok",
                "decision_id": decision_id,
                "executed_trade_id": executed_trade_id,
                "ticket": broker_ticket,
                "close_result": str(close_info.get("result", "breakeven")),
                "pnl_money": float(close_info.get("pnl_money", 0.0) or 0.0),
            }
        )
        Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
        print(f"PHASE1_OK decision_id={decision_id} executed_trade_id={executed_trade_id} ticket={broker_ticket}")
        return 0
    except Exception as exc:
        report.update({"status": "fail", "reason": "exception", "error": str(exc)})
        Path("phase1_cycle_result.json").write_text(json.dumps(report, ensure_ascii=True), encoding="utf-8")
        raise
    finally:
        controller.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
