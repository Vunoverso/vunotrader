#!/usr/bin/env python3
"""
CLI para controlar um terminal MetaTrader 5 direto pelo Python.

Este script e um caminho paralelo ao fluxo principal do projeto.
Ele conecta no terminal MT5 local via pacote MetaTrader5 e permite:
- consultar status da conta e terminal
- ler cotacoes e posicoes
- enviar ordens de compra e venda
- fechar posicoes
- executar uma estrategia simples por loop no CMD

Importante:
- nao substitui o fluxo EA + brain + Supabase
- nao persiste decisao no backend Vuno
- deve ser usado com cautela, preferencialmente em conta demo
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import json
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from vuno_core.cycle_collector import CycleCollector


TIMEFRAME_MAP = {
    "M1": "TIMEFRAME_M1",
    "M2": "TIMEFRAME_M2",
    "M3": "TIMEFRAME_M3",
    "M4": "TIMEFRAME_M4",
    "M5": "TIMEFRAME_M5",
    "M6": "TIMEFRAME_M6",
    "M10": "TIMEFRAME_M10",
    "M12": "TIMEFRAME_M12",
    "M15": "TIMEFRAME_M15",
    "M20": "TIMEFRAME_M20",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H2": "TIMEFRAME_H2",
    "H3": "TIMEFRAME_H3",
    "H4": "TIMEFRAME_H4",
    "H6": "TIMEFRAME_H6",
    "H8": "TIMEFRAME_H8",
    "H12": "TIMEFRAME_H12",
    "D1": "TIMEFRAME_D1",
    "W1": "TIMEFRAME_W1",
    "MN1": "TIMEFRAME_MN1",
}


def load_environment(env_file: str | None) -> None:
    if load_dotenv is None:
        return

    project_root = Path(__file__).resolve().parents[1]
    default_env = project_root / "brain.env"

    if env_file:
        load_dotenv(env_file)
        return

    if default_env.exists():
        load_dotenv(default_env)


def env_str(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or default).strip()


def env_int(name: str, default: int) -> int:
    value = str(os.getenv(name, "")).strip()
    if not value:
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = str(os.getenv(name, "")).strip()
    if not value:
        return default
    return float(value)


class SymbolAutonomyMemory:
    """Memoria local simples por simbolo/timeframe para ajustar prioridade de entrada."""

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or (PROJECT_ROOT / "autonomy_symbol_memory.json")
        self.data: dict[str, dict[str, float]] = {}
        self._load()

    def _load(self) -> None:
        if not self.file_path.exists():
            self.data = {}
            return
        try:
            self.data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception:
            self.data = {}

    def _save(self) -> None:
        try:
            self.file_path.write_text(json.dumps(self.data, ensure_ascii=True, indent=2), encoding="utf-8")
        except Exception:
            return

    @staticmethod
    def _key(symbol: str, timeframe: str) -> str:
        return f"{symbol.upper()}::{timeframe.upper()}"

    def get_stats(self, symbol: str, timeframe: str) -> dict[str, float]:
        key = self._key(symbol, timeframe)
        row = self.data.get(key, {})
        trades = float(row.get("trades", 0.0) or 0.0)
        wins = float(row.get("wins", 0.0) or 0.0)
        losses = float(row.get("losses", 0.0) or 0.0)
        pnl = float(row.get("pnl", 0.0) or 0.0)
        win_rate = (wins / trades) if trades > 0 else 0.5
        return {
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "pnl": pnl,
            "win_rate": win_rate,
        }

    def record_outcome(self, symbol: str, timeframe: str, result: str, pnl_money: float) -> None:
        key = self._key(symbol, timeframe)
        row = self.data.get(key, {"trades": 0.0, "wins": 0.0, "losses": 0.0, "pnl": 0.0})
        row["trades"] = float(row.get("trades", 0.0) or 0.0) + 1.0
        if result.lower() == "win":
            row["wins"] = float(row.get("wins", 0.0) or 0.0) + 1.0
        elif result.lower() == "loss":
            row["losses"] = float(row.get("losses", 0.0) or 0.0) + 1.0
        row["pnl"] = float(row.get("pnl", 0.0) or 0.0) + float(pnl_money or 0.0)
        self.data[key] = row
        self._save()

    def get_priority_multiplier(self, symbol: str, timeframe: str) -> float:
        stats = self.get_stats(symbol, timeframe)
        trades = int(stats["trades"])
        if trades < 5:
            return 1.0
        wr = float(stats["win_rate"])
        # Ajuste leve para evitar overfitting local: max +/-20%
        return max(0.8, min(1.2, 1.0 + ((wr - 0.5) * 0.8)))


def build_vuno_engine():
    from vuno_core import (
        DecisionEngine,
        DecisionRuntimeConfig,
        TradingModel,
        generate_bootstrap_market_data,
        load_model_weights,
        save_model_weights,
    )

    runtime = DecisionRuntimeConfig(
        min_confidence=env_float("VUNO_MIN_CONFIDENCE", 0.62),
        risk_base=env_float("VUNO_RISK_BASE", 2.0),
        risk_max=env_float("VUNO_RISK_MAX", 4.0),
        risk_min=env_float("VUNO_RISK_MIN", 0.5),
    )
    model = TradingModel(runtime)
    loaded = load_model_weights(model)
    if not loaded:
        bootstrap_bars = env_int("VUNO_BOOTSTRAP_BARS", 500)
        model.train(generate_bootstrap_market_data(bootstrap_bars))
        save_model_weights(model)
    return DecisionEngine(model, runtime)


class VunoAuditLogger:
    def __init__(self):
        self.active = False
        self._client = None
        self.user_id = env_str("BRAIN_USER_ID", "")
        self.organization_id = env_str("BRAIN_ORG_ID", "")
        self.robot_instance_id = env_str("MT5_ROBOT_INSTANCE_ID", "")
        self.mode = env_str("VUNO_AUDIT_MODE", "demo")

        if env_str("VUNO_AUDIT_ENABLED", "0") != "1":
            return

        if not self.user_id or not self.organization_id:
            print("[audit] Desativado: faltam BRAIN_USER_ID/BRAIN_ORG_ID no ambiente.")
            return

        try:
            from supabase import create_client
        except ImportError:
            print("[audit] Desativado: pacote supabase não instalado.")
            return

        url = env_str("SUPABASE_URL", "")
        key = env_str("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            print("[audit] Desativado: faltam SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY.")
            return

        try:
            self._client = create_client(url, key)
            self.active = True
            print("[audit] Logger Supabase ativo para run-engine.")
        except Exception as exc:
            print(f"[audit] Desativado: falha ao conectar Supabase ({exc}).")

    def log_decision(self, symbol: str, timeframe: str, signal: str, confidence: float, risk_pct: float, rationale: str) -> str | None:
        if not self.active:
            return None
        try:
            trade_id = f"{symbol}-{int(time.time() * 1000)}"
            resp = (
                self._client.table("trade_decisions")
                .insert(
                    {
                        "trade_id": trade_id,
                        "user_id": self.user_id,
                        "organization_id": self.organization_id,
                        "robot_instance_id": self.robot_instance_id or None,
                        "mode": self.mode,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "side": signal.lower(),
                        "confidence": float(confidence),
                        "risk_pct": float(risk_pct),
                        "rationale": rationale,
                    }
                )
                .execute()
            )
            return (resp.data or [{}])[0].get("id")
        except Exception:
            return None

    def log_trade_open(self, decision_id: str | None, broker_ticket: str, entry_price: float, stop_loss: float, take_profit: float, lot: float) -> str | None:
        if not self.active or not decision_id:
            return None
        try:
            resp = (
                self._client.table("executed_trades")
                .insert(
                    {
                        "trade_decision_id": decision_id,
                        "organization_id": self.organization_id,
                        "robot_instance_id": self.robot_instance_id or None,
                        "broker_ticket": broker_ticket,
                        "entry_price": float(entry_price),
                        "stop_loss": float(stop_loss),
                        "take_profit": float(take_profit),
                        "lot": float(lot),
                        "status": "open",
                        "opened_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )
            return (resp.data or [{}])[0].get("id")
        except Exception:
            return None

    def log_trade_close(self, executed_trade_id: str, pnl_money: float, pnl_points: float, result: str, reason: str) -> None:
        if not self.active or not executed_trade_id:
            return
        try:
            self._client.table("executed_trades").update(
                {"status": "closed", "closed_at": datetime.utcnow().isoformat()}
            ).eq("id", executed_trade_id).execute()

            self._client.table("trade_outcomes").insert(
                {
                    "executed_trade_id": executed_trade_id,
                    "organization_id": self.organization_id,
                    "robot_instance_id": self.robot_instance_id or None,
                    "result": result,
                    "pnl_money": float(pnl_money),
                    "pnl_points": float(pnl_points),
                    "win_loss_reason": reason,
                }
            ).execute()
        except Exception:
            return


def require_mt5() -> None:
    if mt5 is not None:
        return
    print("ERRO: pacote MetaTrader5 nao instalado.")
    print("Instale com: pip install MetaTrader5")
    sys.exit(1)


@dataclass
class ConnectionConfig:
    login: int | None
    password: str
    server: str
    path: str
    timeout_ms: int
    portable: bool


class MT5Controller:
    def __init__(self, config: ConnectionConfig):
        self.config = config

    def connect(self) -> None:
        kwargs: dict[str, object] = {
            "timeout": self.config.timeout_ms,
            "portable": self.config.portable,
        }
        if self.config.path:
            kwargs["path"] = self.config.path
        if self.config.login is not None:
            kwargs["login"] = self.config.login
        if self.config.password:
            kwargs["password"] = self.config.password
        if self.config.server:
            kwargs["server"] = self.config.server

        ok = mt5.initialize(**kwargs)
        if not ok:
            raise RuntimeError(f"Falha ao inicializar MT5: {mt5.last_error()}")

    def disconnect(self) -> None:
        mt5.shutdown()

    def ensure_symbol(self, symbol: str):
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbolo nao encontrado: {symbol}")
        if not info.visible and not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Nao foi possivel habilitar o simbolo: {symbol}")
        return info

    def account_snapshot(self) -> dict[str, object]:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        if terminal is None or account is None:
            raise RuntimeError(f"Nao foi possivel ler status do terminal: {mt5.last_error()}")

        return {
            "terminal_name": terminal.name,
            "terminal_company": terminal.company,
            "connected": terminal.connected,
            "trade_allowed": terminal.trade_allowed,
            "login": account.login,
            "server": account.server,
            "balance": account.balance,
            "equity": account.equity,
            "margin_free": account.margin_free,
            "leverage": account.leverage,
            "currency": account.currency,
        }

    def get_quote(self, symbol: str) -> dict[str, object]:
        self.ensure_symbol(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Nao foi possivel obter tick de {symbol}: {mt5.last_error()}")

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "time_msc": tick.time_msc,
        }

    def get_positions(self, symbol: str | None = None):
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        return list(positions or [])

    def is_position_open(self, ticket: int) -> bool:
        positions = mt5.positions_get(ticket=ticket)
        return bool(positions)

    def get_closed_position_result(self, ticket: int, lookback_hours: int = 24) -> dict[str, float | str] | None:
        to_dt = datetime.now()
        from_dt = to_dt - timedelta(hours=lookback_hours)
        deals = mt5.history_deals_get(from_dt, to_dt)
        if not deals:
            return None

        candidate = None
        for deal in deals:
            pos_id = int(getattr(deal, "position_id", 0) or 0)
            ord_id = int(getattr(deal, "order", 0) or 0)
            if pos_id == ticket or ord_id == ticket:
                candidate = deal

        if candidate is None:
            return None

        pnl = float(getattr(candidate, "profit", 0.0) or 0.0)
        return {
            "pnl_money": pnl,
            "pnl_points": 0.0,
            "result": "win" if pnl > 0 else ("loss" if pnl < 0 else "breakeven"),
            "reason": f"Fechamento detectado no MT5 para ticket {ticket}",
        }

    def get_rates(self, symbol: str, timeframe: str, bars: int) -> pd.DataFrame:
        self.ensure_symbol(symbol)
        tf_attr = TIMEFRAME_MAP.get(timeframe.upper())
        if not tf_attr or not hasattr(mt5, tf_attr):
            raise RuntimeError(f"Timeframe nao suportado: {timeframe}")

        raw = mt5.copy_rates_from_pos(symbol, getattr(mt5, tf_attr), 0, bars)
        if raw is None or len(raw) == 0:
            raise RuntimeError(f"Nao foi possivel obter candles de {symbol}: {mt5.last_error()}")

        frame = pd.DataFrame(raw)
        frame["time"] = pd.to_datetime(frame["time"], unit="s")
        return frame

    def send_market_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        deviation: int,
        magic: int,
        comment: str,
        sl_points: float | None,
        tp_points: float | None,
    ):
        symbol_info = self.ensure_symbol(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Nao foi possivel obter cotacao de {symbol}: {mt5.last_error()}")

        side_norm = side.lower()
        if side_norm not in {"buy", "sell"}:
            raise RuntimeError("Lado invalido. Use buy ou sell.")

        order_type = mt5.ORDER_TYPE_BUY if side_norm == "buy" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side_norm == "buy" else tick.bid
        point = symbol_info.point

        sl = None
        tp = None
        if sl_points and sl_points > 0:
            sl = price - (sl_points * point) if side_norm == "buy" else price + (sl_points * point)
        if tp_points and tp_points > 0:
            tp = price + (tp_points * point) if side_norm == "buy" else price - (tp_points * point)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": price,
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }
        if sl is not None:
            request["sl"] = round(sl, symbol_info.digits)
        if tp is not None:
            request["tp"] = round(tp, symbol_info.digits)

        filling_candidates = []
        if hasattr(symbol_info, "filling_mode") and symbol_info.filling_mode in {
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_RETURN,
        }:
            filling_candidates.append(symbol_info.filling_mode)

        for mode in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]:
            if mode not in filling_candidates:
                filling_candidates.append(mode)

        last_result = None
        for filling_mode in filling_candidates:
            req = dict(request)
            req["type_filling"] = filling_mode
            result = mt5.order_send(req)
            if result is None:
                last_result = None
                continue
            last_result = result
            if int(getattr(result, "retcode", 0)) != 10030:
                return result

        if last_result is None:
            raise RuntimeError(f"order_send retornou vazio: {mt5.last_error()}")
        return last_result

    def close_position(self, ticket: int, deviation: int, magic: int, comment: str):
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            raise RuntimeError(f"Posicao nao encontrada para o ticket {ticket}")

        position = positions[0]
        symbol_info = self.ensure_symbol(position.symbol)
        tick = mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise RuntimeError(f"Nao foi possivel obter cotacao de {position.symbol}: {mt5.last_error()}")

        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": position.ticket,
            "price": price,
            "deviation": int(deviation),
            "magic": int(magic),
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        filling_candidates = []
        if hasattr(symbol_info, "filling_mode") and symbol_info.filling_mode in {
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_RETURN,
        }:
            filling_candidates.append(symbol_info.filling_mode)

        for mode in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]:
            if mode not in filling_candidates:
                filling_candidates.append(mode)

        result = None
        for filling_mode in filling_candidates:
            req = dict(request)
            req["type_filling"] = filling_mode
            result = mt5.order_send(req)
            if result is not None and int(getattr(result, "retcode", 0)) != 10030:
                break

        if result is None:
            raise RuntimeError(f"Falha ao fechar ticket {ticket}: {mt5.last_error()}")

        _ = symbol_info
        return result


def build_connection_config(args: argparse.Namespace) -> ConnectionConfig:
    login_value = args.login if args.login is not None else env_str("MT5_LOGIN", "")
    login = int(login_value) if str(login_value).strip() else None
    return ConnectionConfig(
        login=login,
        password=args.password if args.password is not None else env_str("MT5_PASSWORD", ""),
        server=args.server if args.server is not None else env_str("MT5_SERVER", ""),
        path=args.path if args.path is not None else env_str("MT5_PATH", ""),
        timeout_ms=args.timeout_ms if args.timeout_ms is not None else env_int("MT5_TIMEOUT_MS", 60000),
        portable=bool(args.portable),
    )


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--env-file", help="Arquivo .env opcional para carregar credenciais")
    parser.add_argument("--login", type=int, help="Login da conta MT5")
    parser.add_argument("--password", help="Senha da conta MT5")
    parser.add_argument("--server", help="Servidor da conta MT5")
    parser.add_argument("--path", help="Caminho do terminal terminal64.exe")
    parser.add_argument("--timeout-ms", type=int, help="Timeout da conexao com MT5")
    parser.add_argument("--portable", action="store_true", help="Inicializa o terminal em modo portable")


def add_trade_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--symbol", required=True, help="Simbolo do ativo, ex: EURUSD")
    parser.add_argument("--volume", type=float, required=True, help="Volume/lote da ordem")
    parser.add_argument("--sl-points", type=float, default=0.0, help="Stop loss em pontos")
    parser.add_argument("--tp-points", type=float, default=0.0, help="Take profit em pontos")
    parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    parser.add_argument("--comment", default="python-mt5-bot", help="Comentario da ordem")


def print_status(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        print(f"{key}: {value}")


def print_positions(positions) -> None:
    if not positions:
        print("Nenhuma posicao aberta.")
        return

    for pos in positions:
        side = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
        print(
            f"ticket={pos.ticket} symbol={pos.symbol} side={side} volume={pos.volume} "
            f"price_open={pos.price_open} sl={pos.sl} tp={pos.tp} profit={pos.profit}"
        )


def print_order_result(result) -> None:
    print(f"retcode: {result.retcode}")
    print(f"order: {getattr(result, 'order', None)}")
    print(f"deal: {getattr(result, 'deal', None)}")
    print(f"volume: {getattr(result, 'volume', None)}")
    print(f"price: {getattr(result, 'price', None)}")
    print(f"comment: {getattr(result, 'comment', None)}")


def build_signal(frame: pd.DataFrame, fast_period: int, slow_period: int, rsi_period: int) -> tuple[str, pd.Series]:
    data = frame.copy()
    data["ema_fast"] = data["close"].ewm(span=fast_period, adjust=False).mean()
    data["ema_slow"] = data["close"].ewm(span=slow_period, adjust=False).mean()

    delta = data["close"].diff()
    gains = delta.clip(lower=0).rolling(rsi_period).mean()
    losses = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gains / losses.replace(0, pd.NA)
    data["rsi"] = 100 - (100 / (1 + rs))
    data = data.dropna().reset_index(drop=True)

    if len(data) < 3:
        return "HOLD", pd.Series(dtype="float64")

    prev_bar = data.iloc[-2]
    last_bar = data.iloc[-1]

    crossed_up = prev_bar["ema_fast"] <= prev_bar["ema_slow"] and last_bar["ema_fast"] > last_bar["ema_slow"]
    crossed_down = prev_bar["ema_fast"] >= prev_bar["ema_slow"] and last_bar["ema_fast"] < last_bar["ema_slow"]

    if crossed_up and float(last_bar["rsi"]) < 70:
        return "BUY", last_bar
    if crossed_down and float(last_bar["rsi"]) > 30:
        return "SELL", last_bar
    return "HOLD", last_bar


def run_strategy(controller: MT5Controller, args: argparse.Namespace) -> None:
    print(
        f"Iniciando estrategia em loop | symbol={args.symbol} timeframe={args.timeframe} "
        f"interval={args.interval_sec}s dry_run={args.dry_run}"
    )
    last_bar_time = None

    while True:
        frame = controller.get_rates(args.symbol, args.timeframe, args.bars)
        signal, features = build_signal(frame, args.fast_ema, args.slow_ema, args.rsi_period)
        if features.empty:
            print("Aguardando candles suficientes...")
            time.sleep(args.interval_sec)
            continue

        bar_time = features["time"]
        if last_bar_time is not None and bar_time == last_bar_time:
            time.sleep(args.interval_sec)
            continue
        last_bar_time = bar_time

        positions = controller.get_positions(args.symbol)
        position_sides = {
            "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
            for pos in positions
        }

        print(
            f"{bar_time} signal={signal} close={float(features['close']):.5f} "
            f"ema_fast={float(features['ema_fast']):.5f} ema_slow={float(features['ema_slow']):.5f} "
            f"rsi={float(features['rsi']):.2f} positions={len(positions)}"
        )

        if signal == "HOLD":
            time.sleep(args.interval_sec)
            continue

        if not args.allow_multiple and positions:
            print("Sinal ignorado: ja existe posicao aberta no simbolo.")
            time.sleep(args.interval_sec)
            continue

        if signal in position_sides:
            print("Sinal ignorado: ja existe posicao na mesma direcao.")
            time.sleep(args.interval_sec)
            continue

        if args.close_opposite and positions:
            for pos in positions:
                same_side = (signal == "BUY" and pos.type == mt5.POSITION_TYPE_BUY) or (
                    signal == "SELL" and pos.type == mt5.POSITION_TYPE_SELL
                )
                if not same_side:
                    result = controller.close_position(pos.ticket, args.deviation, args.magic, args.comment)
                    print(f"Posicao oposta fechada | ticket={pos.ticket} retcode={result.retcode}")

        if args.dry_run:
            print(f"[dry-run] Ordem {signal} seria enviada agora.")
        else:
            result = controller.send_market_order(
                symbol=args.symbol,
                side=signal.lower(),
                volume=args.volume,
                deviation=args.deviation,
                magic=args.magic,
                comment=args.comment,
                sl_points=args.sl_points,
                tp_points=args.tp_points,
            )
            print_order_result(result)

        time.sleep(args.interval_sec)


def run_vuno_engine(controller: MT5Controller, args: argparse.Namespace) -> None:
    engine = build_vuno_engine()
    audit = VunoAuditLogger()
    open_audit_trades: dict[int, str] = {}
    print(
        f"Iniciando motor principal Vuno | symbol={args.symbol} timeframe={args.timeframe} "
        f"interval={args.interval_sec}s dry_run={args.dry_run}"
    )
    last_bar_time = None

    while True:
        frame = controller.get_rates(args.symbol, args.timeframe, args.bars)
        analysis = engine.analyze_market(frame, win_rate=args.win_rate, mode=args.mode)
        last_row = analysis.get("last_row")
        if last_row is None or len(last_row) == 0:
            print("Aguardando candles suficientes para o motor principal...")
            time.sleep(args.interval_sec)
            continue

        features = last_row.iloc[0]
        bar_time = features["time"] if "time" in features else frame.iloc[-1]["time"]
        if last_bar_time is not None and bar_time == last_bar_time:
            time.sleep(args.interval_sec)
            continue
        last_bar_time = bar_time

        positions = controller.get_positions(args.symbol)
        position_sides = {
            "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
            for pos in positions
        }

        signal = str(analysis.get("signal", "HOLD") or "HOLD").upper()
        confidence = float(analysis.get("confidence", 0) or 0)
        risk = float(analysis.get("risk", 0) or 0)
        regime = str(analysis.get("regime", "lateral") or "lateral")
        rationale = str(analysis.get("rationale", "") or "")

        print(
            f"{bar_time} signal={signal} conf={confidence:.2%} risk={risk:.2f}% "
            f"regime={regime} positions={len(positions)}\n  rationale={rationale}"
        )

        decision_id = audit.log_decision(
            symbol=args.symbol,
            timeframe=args.timeframe,
            signal=signal,
            confidence=confidence,
            risk_pct=risk,
            rationale=rationale,
        )

        closed_tickets = [t for t in list(open_audit_trades.keys()) if not controller.is_position_open(t)]
        for ticket in closed_tickets:
            close_info = controller.get_closed_position_result(ticket)
            if close_info:
                audit.log_trade_close(
                    executed_trade_id=open_audit_trades[ticket],
                    pnl_money=float(close_info["pnl_money"]),
                    pnl_points=float(close_info["pnl_points"]),
                    result=str(close_info["result"]),
                    reason=str(close_info["reason"]),
                )
            del open_audit_trades[ticket]

        if signal == "HOLD":
            time.sleep(args.interval_sec)
            continue

        if not args.allow_multiple and positions:
            print("Sinal ignorado: ja existe posicao aberta no simbolo.")
            time.sleep(args.interval_sec)
            continue

        if signal in position_sides:
            print("Sinal ignorado: ja existe posicao na mesma direcao.")
            time.sleep(args.interval_sec)
            continue

        if args.close_opposite and positions:
            for pos in positions:
                same_side = (signal == "BUY" and pos.type == mt5.POSITION_TYPE_BUY) or (
                    signal == "SELL" and pos.type == mt5.POSITION_TYPE_SELL
                )
                if not same_side:
                    result = controller.close_position(pos.ticket, args.deviation, args.magic, args.comment)
                    print(f"Posicao oposta fechada | ticket={pos.ticket} retcode={result.retcode}")

        if args.dry_run:
            print(f"[dry-run] Motor Vuno enviaria ordem {signal} agora.")
        else:
            result = controller.send_market_order(
                symbol=args.symbol,
                side=signal.lower(),
                volume=args.volume,
                deviation=args.deviation,
                magic=args.magic,
                comment=args.comment,
                sl_points=args.sl_points,
                tp_points=args.tp_points,
            )
            print_order_result(result)

            broker_ticket = int(getattr(result, "order", 0) or 0) or int(getattr(result, "deal", 0) or 0)
            if broker_ticket > 0:
                executed_trade_id = audit.log_trade_open(
                    decision_id=decision_id,
                    broker_ticket=str(broker_ticket),
                    entry_price=float(getattr(result, "price", 0.0) or 0.0),
                    stop_loss=float(args.sl_points or 0.0),
                    take_profit=float(args.tp_points or 0.0),
                    lot=float(args.volume),
                )
                if executed_trade_id:
                    open_audit_trades[broker_ticket] = executed_trade_id

        time.sleep(args.interval_sec)


def symbol_fx_components(symbol: str) -> tuple[str, str]:
    letters = "".join(ch for ch in symbol.upper() if ch.isalpha())
    if len(letters) < 6:
        return "", ""
    return letters[:3], letters[3:6]


def correlated_positions_count(positions, symbol: str) -> int:
    base, quote = symbol_fx_components(symbol)
    if not base or not quote:
        return 0

    count = 0
    for pos in positions:
        pos_base, pos_quote = symbol_fx_components(getattr(pos, "symbol", ""))
        if not pos_base or not pos_quote:
            continue
        if base in {pos_base, pos_quote} or quote in {pos_base, pos_quote}:
            count += 1
    return count


def compute_atr_pct(frame: pd.DataFrame, period: int = 14) -> float:
    if frame is None or len(frame) < period + 2:
        return 0.0

    data = frame.copy()
    prev_close = data["close"].shift(1)
    tr = pd.concat(
        [
            (data["high"] - data["low"]).abs(),
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean().iloc[-1]
    last_close = float(data["close"].iloc[-1] or 0.0)
    if not last_close:
        return 0.0
    return float(atr / last_close)


def run_vuno_engine_dynamic(controller: MT5Controller, args: argparse.Namespace) -> None:
    engine = build_vuno_engine()
    audit = VunoAuditLogger()
    collector = CycleCollector()
    open_audit_trades: dict[int, str] = {}
    cycle_meta_by_ticket: dict[int, dict[str, object]] = {}
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        raise RuntimeError("Informe ao menos um simbolo em --symbols")

    print(
        f"Iniciando motor dinamico Vuno | symbols={symbols} timeframe={args.timeframe} "
        f"interval={args.interval_sec}s dry_run={args.dry_run}"
    )
    last_bar_by_symbol: dict[str, object] = {}

    while True:
        all_positions = controller.get_positions()
        closed_tickets = [t for t in list(open_audit_trades.keys()) if not controller.is_position_open(t)]
        for ticket in closed_tickets:
            close_info = controller.get_closed_position_result(ticket)
            if close_info:
                audit.log_trade_close(
                    executed_trade_id=open_audit_trades[ticket],
                    pnl_money=float(close_info["pnl_money"]),
                    pnl_points=float(close_info["pnl_points"]),
                    result=str(close_info["result"]),
                    reason=str(close_info["reason"]),
                )
                ticket_meta = cycle_meta_by_ticket.get(ticket, {})
                collector.log_cycle(
                    {
                        "cycle_ts": datetime.utcnow().isoformat(),
                        "mode": args.mode,
                        "symbol": str(ticket_meta.get("symbol", "")),
                        "timeframe": args.timeframe,
                        "signal": str(ticket_meta.get("signal", "HOLD")),
                        "decision_status": "closed",
                        "decision_reason": str(ticket_meta.get("rationale", "")),
                        "confidence": float(ticket_meta.get("confidence", 0.0) or 0.0),
                        "risk": float(ticket_meta.get("risk", 0.0) or 0.0),
                        "regime": str(ticket_meta.get("regime", "lateral")),
                        "score": float(ticket_meta.get("score", 0.0) or 0.0),
                        "spread_points": float(ticket_meta.get("spread_points", 0.0) or 0.0),
                        "atr_pct": float(ticket_meta.get("atr_pct", 0.0) or 0.0),
                        "volume_ratio": float(ticket_meta.get("volume_ratio", 0.0) or 0.0),
                        "rsi": float(ticket_meta.get("rsi", 0.0) or 0.0),
                        "momentum_20": float(ticket_meta.get("momentum_20", 0.0) or 0.0),
                        "decision_id": str(ticket_meta.get("decision_id", "")),
                        "executed": True,
                        "broker_ticket": str(ticket),
                        "result": str(close_info["result"]),
                        "pnl_money": float(close_info["pnl_money"]),
                        "pnl_points": float(close_info["pnl_points"]),
                    }
                )
            del open_audit_trades[ticket]
            if ticket in cycle_meta_by_ticket:
                del cycle_meta_by_ticket[ticket]

        candidates: list[dict[str, object]] = []
        for symbol in symbols:
            try:
                frame = controller.get_rates(symbol, args.timeframe, args.bars)
                analysis = engine.analyze_market(frame, win_rate=args.win_rate, mode=args.mode)
                last_row = analysis.get("last_row")
                if last_row is None or len(last_row) == 0:
                    continue

                features = last_row.iloc[0]
                bar_time = features["time"] if "time" in features else frame.iloc[-1]["time"]
                if last_bar_by_symbol.get(symbol) == bar_time:
                    continue
                last_bar_by_symbol[symbol] = bar_time

                signal = str(analysis.get("signal", "HOLD") or "HOLD").upper()
                confidence = float(analysis.get("confidence", 0.0) or 0.0)
                risk = float(analysis.get("risk", 0.0) or 0.0)
                rationale = str(analysis.get("rationale", "") or "")
                regime = str(analysis.get("regime", "lateral") or "lateral")

                symbol_info = controller.ensure_symbol(symbol)
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    continue
                spread_points = float((tick.ask - tick.bid) / symbol_info.point) if symbol_info.point else 0.0
                atr_pct = compute_atr_pct(frame)

                if spread_points > args.max_spread_points:
                    collector.log_cycle(
                        {
                            "cycle_ts": datetime.utcnow().isoformat(),
                            "mode": args.mode,
                            "symbol": symbol,
                            "timeframe": args.timeframe,
                            "signal": signal,
                            "decision_status": "blocked",
                            "decision_reason": rationale,
                            "block_reason": "spread_high",
                            "confidence": confidence,
                            "risk": risk,
                            "regime": regime,
                            "score": 0.0,
                            "spread_points": spread_points,
                            "atr_pct": atr_pct,
                            "volume_ratio": float(features.get("volume_ratio", 1.0) or 1.0),
                            "rsi": float(features.get("rsi", 50.0) or 50.0),
                            "momentum_20": float(features.get("momentum_20", 0.0) or 0.0),
                            "executed": False,
                        }
                    )
                    continue
                if atr_pct < args.min_atr_pct:
                    collector.log_cycle(
                        {
                            "cycle_ts": datetime.utcnow().isoformat(),
                            "mode": args.mode,
                            "symbol": symbol,
                            "timeframe": args.timeframe,
                            "signal": signal,
                            "decision_status": "blocked",
                            "decision_reason": rationale,
                            "block_reason": "atr_low",
                            "confidence": confidence,
                            "risk": risk,
                            "regime": regime,
                            "score": 0.0,
                            "spread_points": spread_points,
                            "atr_pct": atr_pct,
                            "volume_ratio": float(features.get("volume_ratio", 1.0) or 1.0),
                            "rsi": float(features.get("rsi", 50.0) or 50.0),
                            "momentum_20": float(features.get("momentum_20", 0.0) or 0.0),
                            "executed": False,
                        }
                    )
                    continue
                if signal == "HOLD":
                    collector.log_cycle(
                        {
                            "cycle_ts": datetime.utcnow().isoformat(),
                            "mode": args.mode,
                            "symbol": symbol,
                            "timeframe": args.timeframe,
                            "signal": signal,
                            "decision_status": "analyzed",
                            "decision_reason": rationale,
                            "block_reason": "hold_signal",
                            "confidence": confidence,
                            "risk": risk,
                            "regime": regime,
                            "score": 0.0,
                            "spread_points": spread_points,
                            "atr_pct": atr_pct,
                            "volume_ratio": float(features.get("volume_ratio", 1.0) or 1.0),
                            "rsi": float(features.get("rsi", 50.0) or 50.0),
                            "momentum_20": float(features.get("momentum_20", 0.0) or 0.0),
                            "executed": False,
                        }
                    )
                    continue

                opportunity_score = (confidence * 100.0) + (atr_pct * 10000.0) - (spread_points * 0.35)
                candidates.append(
                    {
                        "symbol": symbol,
                        "signal": signal,
                        "confidence": confidence,
                        "risk": risk,
                        "rationale": rationale,
                        "regime": regime,
                        "spread_points": spread_points,
                        "atr_pct": atr_pct,
                        "volume_ratio": float(features.get("volume_ratio", 1.0) or 1.0),
                        "rsi": float(features.get("rsi", 50.0) or 50.0),
                        "momentum_20": float(features.get("momentum_20", 0.0) or 0.0),
                        "score": opportunity_score,
                    }
                )
            except Exception as exc:
                print(f"[scan] {symbol} ignorado por erro: {exc}")

        if not candidates:
            print("[scan] Nenhuma oportunidade valida no ciclo atual.")
            time.sleep(args.interval_sec)
            continue

        candidates.sort(key=lambda item: float(item["score"]), reverse=True)
        best = candidates[0]
        best_symbol = str(best["symbol"])
        best_signal = str(best["signal"])
        best_confidence = float(best["confidence"])
        best_risk = float(best["risk"])
        best_rationale = str(best["rationale"])

        symbol_positions = [p for p in all_positions if p.symbol == best_symbol]
        symbol_sides = {
            "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
            for p in symbol_positions
        }

        if len(all_positions) >= args.max_global_positions:
            print(f"[risk] Limite global atingido ({len(all_positions)}/{args.max_global_positions}).")
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "blocked",
                    "decision_reason": best_rationale,
                    "block_reason": "max_global_positions",
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        if len(symbol_positions) >= args.max_positions_per_symbol:
            print(
                f"[risk] Limite por simbolo atingido em {best_symbol} "
                f"({len(symbol_positions)}/{args.max_positions_per_symbol})."
            )
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "blocked",
                    "decision_reason": best_rationale,
                    "block_reason": "max_positions_per_symbol",
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        correlated = correlated_positions_count(all_positions, best_symbol)
        if correlated >= args.max_correlated_positions:
            print(
                f"[risk] Limite de correlacao atingido para {best_symbol} "
                f"({correlated}/{args.max_correlated_positions})."
            )
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "blocked",
                    "decision_reason": best_rationale,
                    "block_reason": "max_correlated_positions",
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        if not args.allow_multiple and symbol_positions:
            print(f"[exec] Sinal ignorado para {best_symbol}: ja existe posicao aberta no simbolo.")
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "blocked",
                    "decision_reason": best_rationale,
                    "block_reason": "position_exists",
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        if best_signal in symbol_sides:
            print(f"[exec] Sinal ignorado para {best_symbol}: ja existe posicao na mesma direcao.")
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "blocked",
                    "decision_reason": best_rationale,
                    "block_reason": "same_side_exists",
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        print(
            f"[pick] {best_symbol} signal={best_signal} score={float(best['score']):.2f} "
            f"conf={best_confidence:.2%} spread={float(best['spread_points']):.1f}pts "
            f"atr={float(best['atr_pct']):.3%} regime={best['regime']}"
        )
        print(f"  rationale={best_rationale}")

        decision_id = audit.log_decision(
            symbol=best_symbol,
            timeframe=args.timeframe,
            signal=best_signal,
            confidence=best_confidence,
            risk_pct=best_risk,
            rationale=best_rationale,
        )

        if args.close_opposite and symbol_positions:
            for pos in symbol_positions:
                same_side = (best_signal == "BUY" and pos.type == mt5.POSITION_TYPE_BUY) or (
                    best_signal == "SELL" and pos.type == mt5.POSITION_TYPE_SELL
                )
                if not same_side:
                    result = controller.close_position(pos.ticket, args.deviation, args.magic, args.comment)
                    print(f"Posicao oposta fechada | ticket={pos.ticket} retcode={result.retcode}")

        if args.dry_run:
            print(f"[dry-run] Motor dinamico enviaria ordem {best_signal} em {best_symbol}.")
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "picked",
                    "decision_reason": best_rationale,
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "executed": False,
                }
            )
            time.sleep(args.interval_sec)
            continue

        result = controller.send_market_order(
            symbol=best_symbol,
            side=best_signal.lower(),
            volume=args.volume,
            deviation=args.deviation,
            magic=args.magic,
            comment=args.comment,
            sl_points=args.sl_points,
            tp_points=args.tp_points,
        )
        print_order_result(result)

        broker_ticket = int(getattr(result, "order", 0) or 0) or int(getattr(result, "deal", 0) or 0)
        if broker_ticket > 0:
            executed_trade_id = audit.log_trade_open(
                decision_id=decision_id,
                broker_ticket=str(broker_ticket),
                entry_price=float(getattr(result, "price", 0.0) or 0.0),
                stop_loss=float(args.sl_points or 0.0),
                take_profit=float(args.tp_points or 0.0),
                lot=float(args.volume),
            )
            if executed_trade_id:
                open_audit_trades[broker_ticket] = executed_trade_id
            cycle_meta_by_ticket[broker_ticket] = {
                "symbol": best_symbol,
                "signal": best_signal,
                "rationale": best_rationale,
                "confidence": best_confidence,
                "risk": best_risk,
                "regime": str(best.get("regime", "lateral")),
                "score": float(best.get("score", 0.0) or 0.0),
                "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                "rsi": float(best.get("rsi", 0.0) or 0.0),
                "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                "decision_id": decision_id or "",
            }
            collector.log_cycle(
                {
                    "cycle_ts": datetime.utcnow().isoformat(),
                    "mode": args.mode,
                    "symbol": best_symbol,
                    "timeframe": args.timeframe,
                    "signal": best_signal,
                    "decision_status": "executed",
                    "decision_reason": best_rationale,
                    "confidence": best_confidence,
                    "risk": best_risk,
                    "regime": str(best.get("regime", "lateral")),
                    "score": float(best.get("score", 0.0) or 0.0),
                    "spread_points": float(best.get("spread_points", 0.0) or 0.0),
                    "atr_pct": float(best.get("atr_pct", 0.0) or 0.0),
                    "volume_ratio": float(best.get("volume_ratio", 0.0) or 0.0),
                    "rsi": float(best.get("rsi", 0.0) or 0.0),
                    "momentum_20": float(best.get("momentum_20", 0.0) or 0.0),
                    "decision_id": decision_id or "",
                    "executed": True,
                    "broker_ticket": str(broker_ticket),
                }
            )

        time.sleep(args.interval_sec)


def parse_symbols_list(raw: str) -> list[str]:
    return [s.strip().upper() for s in (raw or "").split(",") if s.strip()]


def analyze_symbol_with_engine(
    controller: MT5Controller,
    engine,
    memory: SymbolAutonomyMemory,
    symbol: str,
    timeframe: str,
    bars: int,
    mode: str,
    win_rate: float,
    min_volume_ratio: float,
) -> dict | None:
    try:
        frame = controller.get_rates(symbol, timeframe, bars)
        analysis = engine.analyze_market(frame, win_rate=win_rate, mode=mode)
        last_row = analysis.get("last_row")
        if last_row is None or len(last_row) == 0:
            return None

        features = last_row.iloc[0]
        signal = str(analysis.get("signal", "HOLD") or "HOLD").upper()
        confidence = float(analysis.get("confidence", 0) or 0)
        risk = float(analysis.get("risk", 0) or 0)
        regime = str(analysis.get("regime", "lateral") or "lateral")
        rationale = str(analysis.get("rationale", "") or "")
        atr_pct = float(analysis.get("atr_pct", 0) or 0)
        volume_ratio = float(features.get("volume_ratio", 1.0) or 1.0)
        rsi = float(features.get("rsi", 50) or 50)
        momentum_20 = float(features.get("momentum_20", 0) or 0)

        # Score base de oportunidade por ativo.
        score = confidence * 100.0
        if regime == "tendencia":
            score += 8.0
        elif regime == "lateral":
            score -= 6.0
        elif regime == "volatil":
            score -= 2.0

        if volume_ratio < min_volume_ratio:
            score -= 10.0
        else:
            score += min(8.0, (volume_ratio - min_volume_ratio) * 6.0)

        # Evita priorizar mercado sem range suficiente.
        if atr_pct < 0.0025:
            score -= 6.0

        # Ajuste por memoria local de resultado por simbolo/timeframe.
        mem_mult = memory.get_priority_multiplier(symbol, timeframe)
        score *= mem_mult

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal,
            "confidence": confidence,
            "risk": risk,
            "regime": regime,
            "volume_ratio": volume_ratio,
            "atr_pct": atr_pct,
            "rsi": rsi,
            "momentum_20": momentum_20,
            "score": round(score, 3),
            "rationale": rationale,
            "memory_multiplier": round(mem_mult, 3),
            "memory": memory.get_stats(symbol, timeframe),
        }
    except Exception as exc:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": "HOLD",
            "confidence": 0.0,
            "risk": 0.0,
            "regime": "erro",
            "volume_ratio": 0.0,
            "atr_pct": 0.0,
            "rsi": 0.0,
            "momentum_20": 0.0,
            "score": -999.0,
            "rationale": f"erro_analise: {exc}",
            "memory_multiplier": 1.0,
            "memory": memory.get_stats(symbol, timeframe),
        }


def run_scan_markets(controller: MT5Controller, args: argparse.Namespace) -> None:
    symbols = parse_symbols_list(args.symbols)
    if not symbols:
        raise RuntimeError("Lista de simbolos vazia. Use --symbols EURUSD,GBPUSD,...")

    engine = build_vuno_engine()
    memory = SymbolAutonomyMemory()
    rows = []
    for symbol in symbols:
        row = analyze_symbol_with_engine(
            controller=controller,
            engine=engine,
            memory=memory,
            symbol=symbol,
            timeframe=args.timeframe,
            bars=args.bars,
            mode=args.mode,
            win_rate=args.win_rate,
            min_volume_ratio=args.min_volume_ratio,
        )
        if row:
            rows.append(row)

    if not rows:
        print("Nenhum ativo analisado.")
        return

    filtered = [
        r for r in rows
        if r["signal"] in {"BUY", "SELL"}
        and r["confidence"] >= args.min_confidence
        and (args.allow_lateral or r["regime"] != "lateral")
        and r["volume_ratio"] >= args.min_volume_ratio
    ]
    ranked = sorted(filtered, key=lambda x: x["score"], reverse=True)

    if args.output_json:
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "candidates": ranked[: args.top],
            "all": rows,
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return

    print(
        f"Scanner concluido | timeframe={args.timeframe} ativos={len(rows)} "
        f"candidatos={len(ranked)}"
    )
    for row in ranked[: args.top]:
        print(
            f"{row['symbol']} sig={row['signal']} conf={row['confidence']:.1%} "
            f"score={row['score']:.2f} regime={row['regime']} vol_ratio={row['volume_ratio']:.2f} "
            f"atr={row['atr_pct']*100:.2f}% memx={row['memory_multiplier']:.2f}"
        )
        print(f"  indicador: rsi={row['rsi']:.1f} mom20={row['momentum_20']*100:.2f}%")
        print(f"  rationale: {row['rationale']}")


def run_autonomy(controller: MT5Controller, args: argparse.Namespace) -> None:
    symbols = parse_symbols_list(args.symbols)
    if not symbols:
        raise RuntimeError("Lista de simbolos vazia. Use --symbols EURUSD,GBPUSD,...")

    engine = build_vuno_engine()
    memory = SymbolAutonomyMemory()
    open_auto_tickets: dict[int, tuple[str, str]] = {}

    print(
        f"Autonomia iniciada | ativos={len(symbols)} timeframe={args.timeframe} "
        f"interval={args.interval_sec}s dry_run={args.dry_run}"
    )

    while True:
        # Atualiza outcomes para aprender com resultado real por simbolo.
        closed = [t for t in list(open_auto_tickets.keys()) if not controller.is_position_open(t)]
        for ticket in closed:
            symbol, tf = open_auto_tickets[ticket]
            close_info = controller.get_closed_position_result(ticket)
            if close_info:
                memory.record_outcome(
                    symbol=symbol,
                    timeframe=tf,
                    result=str(close_info["result"]),
                    pnl_money=float(close_info["pnl_money"]),
                )
            del open_auto_tickets[ticket]

        rows = []
        for symbol in symbols:
            row = analyze_symbol_with_engine(
                controller=controller,
                engine=engine,
                memory=memory,
                symbol=symbol,
                timeframe=args.timeframe,
                bars=args.bars,
                mode=args.mode,
                win_rate=args.win_rate,
                min_volume_ratio=args.min_volume_ratio,
            )
            if row:
                rows.append(row)

        candidates = [
            r for r in rows
            if r["signal"] in {"BUY", "SELL"}
            and r["confidence"] >= args.min_confidence
            and (args.allow_lateral or r["regime"] != "lateral")
            and r["volume_ratio"] >= args.min_volume_ratio
        ]
        ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)

        if not ranked:
            print(f"{datetime.now().isoformat()} sem candidato valido no ciclo.")
            time.sleep(args.interval_sec)
            continue

        best = ranked[0]
        positions_all = controller.get_positions()
        if not args.allow_multiple and positions_all:
            print(
                f"{datetime.now().isoformat()} melhor ativo={best['symbol']} "
                f"mas ja existe posicao aberta ({len(positions_all)})."
            )
            time.sleep(args.interval_sec)
            continue

        print(
            f"{datetime.now().isoformat()} melhor={best['symbol']} sig={best['signal']} "
            f"conf={best['confidence']:.1%} score={best['score']:.2f} "
            f"regime={best['regime']} vol={best['volume_ratio']:.2f}"
        )

        if args.dry_run:
            print(f"[dry-run] Entraria em {best['symbol']} ({best['signal']}).")
            time.sleep(args.interval_sec)
            continue

        result = controller.send_market_order(
            symbol=best["symbol"],
            side=str(best["signal"]).lower(),
            volume=args.volume,
            deviation=args.deviation,
            magic=args.magic,
            comment=args.comment,
            sl_points=args.sl_points,
            tp_points=args.tp_points,
        )
        print_order_result(result)

        broker_ticket = int(getattr(result, "order", 0) or 0) or int(getattr(result, "deal", 0) or 0)
        if broker_ticket > 0:
            open_auto_tickets[broker_ticket] = (best["symbol"], args.timeframe)

        time.sleep(args.interval_sec)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot Python para controlar MetaTrader 5 pelo CMD")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Mostra status do terminal e da conta")
    add_connection_args(status_parser)

    quote_parser = subparsers.add_parser("quote", help="Mostra a cotacao atual de um simbolo")
    add_connection_args(quote_parser)
    quote_parser.add_argument("--symbol", required=True, help="Simbolo do ativo")

    positions_parser = subparsers.add_parser("positions", help="Lista posicoes abertas")
    add_connection_args(positions_parser)
    positions_parser.add_argument("--symbol", help="Filtra por simbolo")

    buy_parser = subparsers.add_parser("buy", help="Envia ordem de compra a mercado")
    add_connection_args(buy_parser)
    add_trade_args(buy_parser)

    sell_parser = subparsers.add_parser("sell", help="Envia ordem de venda a mercado")
    add_connection_args(sell_parser)
    add_trade_args(sell_parser)

    close_parser = subparsers.add_parser("close", help="Fecha uma posicao por ticket")
    add_connection_args(close_parser)
    close_parser.add_argument("--ticket", type=int, required=True, help="Ticket da posicao")
    close_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    close_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    close_parser.add_argument("--comment", default="python-mt5-close", help="Comentario da ordem")

    close_all_parser = subparsers.add_parser("close-all", help="Fecha todas as posicoes, opcionalmente por simbolo")
    add_connection_args(close_all_parser)
    close_all_parser.add_argument("--symbol", help="Fecha apenas o simbolo informado")
    close_all_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    close_all_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    close_all_parser.add_argument("--comment", default="python-mt5-close-all", help="Comentario da ordem")

    strategy_parser = subparsers.add_parser("run-strategy", help="Executa uma estrategia simples por loop")
    add_connection_args(strategy_parser)
    strategy_parser.add_argument("--symbol", required=True, help="Simbolo do ativo")
    strategy_parser.add_argument("--timeframe", default=env_str("MT5_TIMEFRAME", "M5"), help="Timeframe, ex: M5")
    strategy_parser.add_argument("--bars", type=int, default=300, help="Quantidade de candles para analise")
    strategy_parser.add_argument("--interval-sec", type=int, default=10, help="Intervalo entre ciclos")
    strategy_parser.add_argument("--fast-ema", type=int, default=9, help="Periodo da EMA rapida")
    strategy_parser.add_argument("--slow-ema", type=int, default=21, help="Periodo da EMA lenta")
    strategy_parser.add_argument("--rsi-period", type=int, default=14, help="Periodo do RSI")
    strategy_parser.add_argument("--volume", type=float, required=True, help="Volume/lote da ordem")
    strategy_parser.add_argument("--sl-points", type=float, default=0.0, help="Stop loss em pontos")
    strategy_parser.add_argument("--tp-points", type=float, default=0.0, help="Take profit em pontos")
    strategy_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    strategy_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    strategy_parser.add_argument("--comment", default="python-mt5-strategy", help="Comentario da ordem")
    strategy_parser.add_argument("--dry-run", action="store_true", help="Nao envia ordens; apenas mostra sinais")
    strategy_parser.add_argument("--close-opposite", action="store_true", help="Fecha posicoes opostas antes de inverter")
    strategy_parser.add_argument("--allow-multiple", action="store_true", help="Permite multiplas posicoes no simbolo")

    vuno_engine_parser = subparsers.add_parser("run-engine", help="Executa o motor principal compartilhado do Vuno em loop")
    add_connection_args(vuno_engine_parser)
    vuno_engine_parser.add_argument("--symbol", required=True, help="Simbolo do ativo")
    vuno_engine_parser.add_argument("--timeframe", default=env_str("MT5_TIMEFRAME", "M5"), help="Timeframe, ex: M5")
    vuno_engine_parser.add_argument("--bars", type=int, default=300, help="Quantidade de candles para analise")
    vuno_engine_parser.add_argument("--interval-sec", type=int, default=10, help="Intervalo entre ciclos")
    vuno_engine_parser.add_argument("--volume", type=float, required=True, help="Volume/lote da ordem")
    vuno_engine_parser.add_argument("--sl-points", type=float, default=0.0, help="Stop loss em pontos")
    vuno_engine_parser.add_argument("--tp-points", type=float, default=0.0, help="Take profit em pontos")
    vuno_engine_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    vuno_engine_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    vuno_engine_parser.add_argument("--comment", default="python-vuno-engine", help="Comentario da ordem")
    vuno_engine_parser.add_argument("--dry-run", action="store_true", help="Nao envia ordens; apenas mostra sinais")
    vuno_engine_parser.add_argument("--close-opposite", action="store_true", help="Fecha posicoes opostas antes de inverter")
    vuno_engine_parser.add_argument("--allow-multiple", action="store_true", help="Permite multiplas posicoes no simbolo")
    vuno_engine_parser.add_argument("--mode", default="demo", choices=["observer", "demo", "real"], help="Modo logico do motor")
    vuno_engine_parser.add_argument("--win-rate", type=float, default=0.5, help="Win rate informado ao motor para governanca local")

    vuno_dynamic_parser = subparsers.add_parser(
        "run-engine-dynamic",
        help="Executa o motor Vuno com scanner dinamico multiativos e selecao da melhor oportunidade",
    )
    add_connection_args(vuno_dynamic_parser)
    vuno_dynamic_parser.add_argument("--symbols", required=True, help="Lista de simbolos separados por virgula")
    vuno_dynamic_parser.add_argument("--timeframe", default=env_str("MT5_TIMEFRAME", "M5"), help="Timeframe, ex: M5")
    vuno_dynamic_parser.add_argument("--bars", type=int, default=300, help="Quantidade de candles por simbolo")
    vuno_dynamic_parser.add_argument("--interval-sec", type=int, default=10, help="Intervalo entre ciclos")
    vuno_dynamic_parser.add_argument("--volume", type=float, required=True, help="Volume/lote da ordem")
    vuno_dynamic_parser.add_argument("--sl-points", type=float, default=0.0, help="Stop loss em pontos")
    vuno_dynamic_parser.add_argument("--tp-points", type=float, default=0.0, help="Take profit em pontos")
    vuno_dynamic_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    vuno_dynamic_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    vuno_dynamic_parser.add_argument("--comment", default="python-vuno-dynamic", help="Comentario da ordem")
    vuno_dynamic_parser.add_argument("--dry-run", action="store_true", help="Nao envia ordens; apenas mostra selecao")
    vuno_dynamic_parser.add_argument("--close-opposite", action="store_true", help="Fecha posicoes opostas antes de inverter")
    vuno_dynamic_parser.add_argument("--allow-multiple", action="store_true", help="Permite multiplas posicoes no simbolo")
    vuno_dynamic_parser.add_argument("--mode", default="demo", choices=["observer", "demo", "real"], help="Modo logico do motor")
    vuno_dynamic_parser.add_argument("--win-rate", type=float, default=0.5, help="Win rate informado ao motor")
    vuno_dynamic_parser.add_argument("--max-spread-points", type=float, default=35.0, help="Spread maximo permitido")
    vuno_dynamic_parser.add_argument("--min-atr-pct", type=float, default=0.00035, help="ATR percentual minimo")
    vuno_dynamic_parser.add_argument("--max-global-positions", type=int, default=3, help="Limite global de posicoes")
    vuno_dynamic_parser.add_argument("--max-positions-per-symbol", type=int, default=1, help="Limite por simbolo")
    vuno_dynamic_parser.add_argument("--max-correlated-positions", type=int, default=2, help="Limite de posicoes correlacionadas")

    scan_parser = subparsers.add_parser("scan-markets", help="Escaneia multiplos ativos e ranqueia melhor oportunidade")
    add_connection_args(scan_parser)
    scan_parser.add_argument("--symbols", required=True, help="Lista CSV de simbolos, ex: EURUSD,GBPUSD,XAUUSD")
    scan_parser.add_argument("--timeframe", default=env_str("MT5_TIMEFRAME", "M5"), help="Timeframe, ex: M5")
    scan_parser.add_argument("--bars", type=int, default=300, help="Candles por ativo para analise")
    scan_parser.add_argument("--mode", default="demo", choices=["observer", "demo", "real"], help="Modo logico da analise")
    scan_parser.add_argument("--win-rate", type=float, default=0.5, help="Win rate base informado ao motor")
    scan_parser.add_argument("--min-confidence", type=float, default=0.62, help="Confianca minima para candidato")
    scan_parser.add_argument("--min-volume-ratio", type=float, default=0.8, help="Filtro minimo de volume relativo")
    scan_parser.add_argument("--allow-lateral", action="store_true", help="Permite entradas em regime lateral")
    scan_parser.add_argument("--top", type=int, default=5, help="Quantidade de candidatos para mostrar")
    scan_parser.add_argument("--json", dest="output_json", action="store_true", help="Retorna resultado em JSON")

    autonomy_parser = subparsers.add_parser("run-autonomy", help="Modo autonomo: escolhe melhor ativo por ciclo e opera")
    add_connection_args(autonomy_parser)
    autonomy_parser.add_argument("--symbols", required=True, help="Lista CSV de simbolos, ex: EURUSD,GBPUSD,XAUUSD")
    autonomy_parser.add_argument("--timeframe", default=env_str("MT5_TIMEFRAME", "M5"), help="Timeframe, ex: M5")
    autonomy_parser.add_argument("--bars", type=int, default=300, help="Candles por ativo para analise")
    autonomy_parser.add_argument("--interval-sec", type=int, default=15, help="Intervalo de varredura")
    autonomy_parser.add_argument("--volume", type=float, required=True, help="Volume/lote da ordem")
    autonomy_parser.add_argument("--sl-points", type=float, default=0.0, help="Stop loss em pontos")
    autonomy_parser.add_argument("--tp-points", type=float, default=0.0, help="Take profit em pontos")
    autonomy_parser.add_argument("--deviation", type=int, default=env_int("MT5_DEVIATION", 20), help="Desvio maximo")
    autonomy_parser.add_argument("--magic", type=int, default=env_int("MT5_MAGIC", 20260331), help="Magic number")
    autonomy_parser.add_argument("--comment", default="python-mt5-autonomy", help="Comentario da ordem")
    autonomy_parser.add_argument("--dry-run", action="store_true", help="Nao envia ordens; apenas escolhe ativo")
    autonomy_parser.add_argument("--allow-multiple", action="store_true", help="Permite multiplas posicoes simultaneas")
    autonomy_parser.add_argument("--mode", default="demo", choices=["observer", "demo", "real"], help="Modo logico da analise")
    autonomy_parser.add_argument("--win-rate", type=float, default=0.5, help="Win rate base informado ao motor")
    autonomy_parser.add_argument("--min-confidence", type=float, default=0.62, help="Confianca minima para entrar")
    autonomy_parser.add_argument("--min-volume-ratio", type=float, default=0.8, help="Filtro minimo de volume relativo")
    autonomy_parser.add_argument("--allow-lateral", action="store_true", help="Permite entradas em regime lateral")

    return parser


def main() -> None:
    require_mt5()
    # Preload do .env default para que defaults do argparse reflitam o ambiente local.
    load_environment(None)
    parser = build_parser()
    args = parser.parse_args()
    load_environment(getattr(args, "env_file", None))

    config = build_connection_config(args)
    controller = MT5Controller(config)

    try:
        controller.connect()

        if args.command == "status":
            print_status(controller.account_snapshot())
            return

        if args.command == "quote":
            quote = controller.get_quote(args.symbol)
            print_status(quote)
            return

        if args.command == "positions":
            print_positions(controller.get_positions(args.symbol))
            return

        if args.command in {"buy", "sell"}:
            result = controller.send_market_order(
                symbol=args.symbol,
                side=args.command,
                volume=args.volume,
                deviation=args.deviation,
                magic=args.magic,
                comment=args.comment,
                sl_points=args.sl_points,
                tp_points=args.tp_points,
            )
            print_order_result(result)
            return

        if args.command == "close":
            result = controller.close_position(args.ticket, args.deviation, args.magic, args.comment)
            print_order_result(result)
            return

        if args.command == "close-all":
            positions = controller.get_positions(args.symbol)
            if not positions:
                print("Nenhuma posicao para fechar.")
                return
            for pos in positions:
                result = controller.close_position(pos.ticket, args.deviation, args.magic, args.comment)
                print(f"ticket={pos.ticket}")
                print_order_result(result)
            return

        if args.command == "run-strategy":
            run_strategy(controller, args)
            return

        if args.command == "run-engine":
            run_vuno_engine(controller, args)
            return

        if args.command == "run-engine-dynamic":
            run_vuno_engine_dynamic(controller, args)
            return

        if args.command == "scan-markets":
            run_scan_markets(controller, args)
            return

        if args.command == "run-autonomy":
            run_autonomy(controller, args)
            return

        raise RuntimeError(f"Comando nao suportado: {args.command}")
    except KeyboardInterrupt:
        print("Execucao interrompida pelo usuario.")
    except Exception as exc:
        print(f"ERRO: {exc}")
        sys.exit(1)
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()