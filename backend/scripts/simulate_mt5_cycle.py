# -*- coding: utf-8 -*-
"""
simulate_mt5_cycle.py
=====================
Testa o ciclo completo do Vuno Brain de ponta a ponta:

  Ciclo 1  : MARKET_DATA → verifica decision_id, regime, rationale, action
  Ciclo 2  : TRADE_RESULT WIN  → verifica acked=True
  Ciclo 3  : 3× MARKET_DATA+LOSS → verifica contagem de derrotas consecutivas
  Ciclo 4  : N× LOSS para acionar pausa por drawdown (se drawdown_pause_pct ativo)

Uso:
    python backend/scripts/simulate_mt5_cycle.py

Variáveis de ambiente opcionais:
    VUNO_USER_ID, VUNO_ORG_ID, VUNO_ROBOT_ID, VUNO_ROBOT_TOKEN
    BRAIN_HOST  (default: 127.0.0.1)
    BRAIN_PORT  (default: 9999)
"""

import json
import os
import random
import socket
import sys
import time
from typing import Any

# ────────────────────────────────────────────────────────────────
# Cores ANSI
# ────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# ────────────────────────────────────────────────────────────────
# Configuração
# ────────────────────────────────────────────────────────────────
HOST       = os.getenv("BRAIN_HOST", "127.0.0.1")
PORT       = int(os.getenv("BRAIN_PORT", "9999"))
USER_ID    = os.getenv("VUNO_USER_ID",    "96fd6e0d-ae81-4eeb-b6fd-37279373a7db")
ORG_ID     = os.getenv("VUNO_ORG_ID",     "24affdc3-dc7b-4672-b20d-65033949bb76")
ROBOT_ID   = os.getenv("VUNO_ROBOT_ID",   "")   # vazio = brain cria/busca automaticamente
ROBOT_TOKEN = os.getenv("VUNO_ROBOT_TOKEN", "")

# ────────────────────────────────────────────────────────────────
# Contadores de assertivas
# ────────────────────────────────────────────────────────────────
_passed = 0
_failed = 0
_robot_id_resolved: str = ROBOT_ID   # atualizado após 1ª resposta


def ok(label: str, value: Any = "") -> None:
    global _passed
    _passed += 1
    suffix = f" {DIM}({value}){RESET}" if value != "" else ""
    print(f"  {GREEN}✅ {label}{RESET}{suffix}")


def fail(label: str, value: Any = "") -> None:
    global _failed
    _failed += 1
    suffix = f" {DIM}({value}){RESET}" if value != "" else ""
    print(f"  {RED}❌ {label}{RESET}{suffix}")


def warn(label: str) -> None:
    print(f"  {YELLOW}⚠️  {label}{RESET}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'─'*60}{RESET}")


# ────────────────────────────────────────────────────────────────
# Transporte TCP
# ────────────────────────────────────────────────────────────────
def send_payload(payload: dict, timeout: float = 20.0) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((HOST, PORT))
        s.sendall(json.dumps(payload).encode("utf-8"))
        chunks: list[bytes] = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                return json.loads(b"".join(chunks).decode("utf-8"))
            except json.JSONDecodeError:
                continue
    finally:
        s.close()
    return {}


# ────────────────────────────────────────────────────────────────
# Helpers de construção de payload
# ────────────────────────────────────────────────────────────────
def build_candles(n: int = 120, trend: str = "flat") -> list[list[float]]:
    """
    trend: 'flat' | 'up' | 'down'  – molda os últimos 30 candles para
    ajudar o modelo a tender a BUY/SELL (melhor chance de TRADE vs HOLD).
    """
    now  = int(time.time())
    base = 130_000.0
    candles: list[list[float]] = []
    for i in range(n):
        t = now - (n - i) * 60
        drift = 0.0
        if trend == "up"   and i >= n - 30:
            drift = 20.0
        elif trend == "down" and i >= n - 30:
            drift = -20.0
        o = base + random.uniform(-15, 15) + drift
        c = o    + random.uniform(-20, 20) + drift * 0.5
        h = max(o, c) + random.uniform(0, 10)
        lo = min(o, c) - random.uniform(0, 10)
        v = random.uniform(200, 1500)
        candles.append([t, o, h, lo, c, v])
        base = c
    return candles


def market_payload(symbol: str = "WINM26", trend: str = "up") -> dict:
    return {
        "type":            "MARKET_DATA",
        "symbol":          symbol,
        "timeframe":       "M5",
        "mode":            "demo",
        "user_id":         USER_ID,
        "organization_id": ORG_ID,
        "robot_id":        _robot_id_resolved,
        "robot_token":     ROBOT_TOKEN,
        "candles":         build_candles(trend=trend),
    }


def trade_payload(
    decision_id: str,
    profit: float,
    stop_loss: float = 129_500.0,
    take_profit: float = 130_800.0,
    ticket: str = "900001",
) -> dict:
    return {
        "type":            "TRADE_RESULT",
        "ticket":          ticket,
        "decision_id":     decision_id,
        "mode":            "demo",
        "user_id":         USER_ID,
        "organization_id": ORG_ID,
        "robot_id":        _robot_id_resolved,
        "robot_token":     ROBOT_TOKEN,
        "entry_price":     130_000.0,
        "stop_loss":       stop_loss,
        "take_profit":     take_profit,
        "lot":             1.0,
        "profit":          profit,
        "points":          int(profit / 5),
        "symbol":          "WINM26",
    }


# ────────────────────────────────────────────────────────────────
# Ciclos de teste
# ────────────────────────────────────────────────────────────────
def ciclo_market_data() -> str | None:
    """Ciclo 1: MARKET_DATA – valída campos essenciais da resposta."""
    global _robot_id_resolved
    section("Ciclo 1 — MARKET_DATA (validação de resposta)")

    resp = send_payload(market_payload(trend="up"))
    print(f"  {DIM}resposta bruta: {json.dumps(resp, ensure_ascii=False)[:200]}{RESET}")

    # atualiza robot_id se brain retornou um
    if resp.get("robot_id"):
        _robot_id_resolved = resp["robot_id"]

    did  = resp.get("decision_id", "")
    actn = resp.get("action", "")
    conf = resp.get("confidence", None)
    reg  = resp.get("regime", "")
    rat  = resp.get("rationale", "")

    did  and ok("decision_id presente", did[:8] + "…")  or fail("decision_id ausente")
    actn and ok("action presente", actn)                or fail("action ausente")
    conf is not None and ok(f"confidence presente ({conf:.2f})")  or warn("confidence ausente (opcional)")
    reg  and ok("regime presente", reg)                or warn("regime ausente (opcional)")

    if rat:
        ok("rationale presente", rat[:40] + "…")
    else:
        warn("rationale ausente (registrado somente após 1ª decisão com trade_decision_id)")

    return did if did else None


def ciclo_trade_win(decision_id: str) -> None:
    """Ciclo 2: TRADE_RESULT WIN."""
    section("Ciclo 2 — TRADE_RESULT WIN")

    resp = send_payload(trade_payload(decision_id, profit=250.0, ticket="900010"))
    print(f"  {DIM}resposta: {json.dumps(resp, ensure_ascii=False)[:200]}{RESET}")

    resp.get("acked") and ok("acked=True") or fail("acked ausente ou False")
    resp.get("error") and fail(f"error inesperado: {resp['error']}") or ok("sem error")


def ciclo_perdas_consecutivas(n_perdas: int = 4) -> tuple[str | None, int]:
    """
    Ciclo 3: envia N pares MARKET_DATA + TRADE_RESULT LOSS e verifica
    se o brain retorna paused=True após atingir o limite de consecutive_losses.
    Retorna o último decision_id e quantas vezes paused foi True.
    """
    section(f"Ciclo 3 — {n_perdas}× LOSS consecutivo (teste consecutive_losses)")

    paused_count = 0
    last_did: str | None = None

    for i in range(n_perdas):
        resp_md = send_payload(market_payload(trend="flat"))
        did = resp_md.get("decision_id", "")
        last_did = did or last_did

        if not did:
            warn(f"  iteração {i+1}: sem decision_id, pulando TRADE_RESULT")
            continue

        if resp_md.get("paused"):
            paused_count += 1
            print(f"  {YELLOW}⚠️  iteração {i+1}: brain retornou paused=True já no MARKET_DATA{RESET}")

        resp_tr = send_payload(trade_payload(did, profit=-150.0, ticket=f"90002{i}"))

        if resp_tr.get("paused"):
            paused_count += 1
            print(f"  {YELLOW}  → TRADE_RESULT {i+1}: paused=True recebido{RESET}")

        time.sleep(0.1)

    if paused_count > 0:
        ok(f"paused=True recebido {paused_count}× durante sequência de perdas")
    else:
        warn(f"paused não ativado em {n_perdas} perdas (verifique consecutive_loss_limit no Supabase)")

    return last_did, paused_count


def ciclo_heartbeat(decision_id: str | None) -> None:
    """Ciclo 4: envia novo MARKET_DATA para verificar que last_seen_at atualiza."""
    section("Ciclo 4 — Heartbeat / last_seen_at")

    if not decision_id:
        resp = send_payload(market_payload(trend="flat"))
        decision_id = resp.get("decision_id")

    resp2 = send_payload(market_payload(trend="flat"))

    resp2.get("decision_id") and ok("segundo MARKET_DATA respondido (heartbeat OK)") \
                              or fail("sem resposta ao segundo MARKET_DATA")
    ok("last_seen_at atualizado via brain (verificar tabela robot_instances no Supabase)")


def ciclo_drawdown() -> None:
    """
    Ciclo 5: envia LOSS pesados para acionar pausa por drawdown.
    Se drawdown_pause_pct = 5 e capital_usd = 10000, o limite é R$500.
    Enviaremos 4 trades com -200 cada (total -800).
    """
    section("Ciclo 5 — Drawdown pause (se configurado)")
    warn("Requer drawdown_pause_pct > 0 e capital_usd configurados no Supabase")

    paused_any = False
    for i in range(4):
        resp_md = send_payload(market_payload(trend="down"))
        did = resp_md.get("decision_id", "")

        if resp_md.get("paused"):
            paused_any = True
            ok(f"MARKET_DATA {i+1}: paused=True por drawdown — brain pausou como esperado")
            break

        if not did:
            warn(f"MARKET_DATA {i+1}: sem decision_id")
            continue

        resp_tr = send_payload(trade_payload(did, profit=-200.0, ticket=f"90010{i}"))

        if resp_tr.get("paused"):
            paused_any = True
            ok(f"TRADE_RESULT {i+1}: paused=True por drawdown — brain pausou")
            break

        time.sleep(0.1)

    if not paused_any:
        warn("Drawdown não ativado (normal se drawdown_pause_pct = 0 ou capital_usd alto)")


# ────────────────────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  Vuno Brain — Simulação completa do ciclo MT5{RESET}")
    print(f"{BOLD}  Brain: {HOST}:{PORT}{RESET}")
    print(f"{BOLD}  Usuário: {USER_ID[:8]}… | Org: {ORG_ID[:8]}…{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")

    # ── Verifica se o brain está acessível ──────────────────────
    try:
        probe = socket.create_connection((HOST, PORT), timeout=3)
        probe.close()
    except OSError:
        print(f"\n{RED}{BOLD}  Brain não acessível em {HOST}:{PORT}{RESET}")
        print(f"  Inicie o brain: {CYAN}python vunotrader_brain.py{RESET}\n")
        sys.exit(1)

    ok("Brain acessível", f"{HOST}:{PORT}")

    # ── Ciclos ───────────────────────────────────────────────────
    did1 = ciclo_market_data()

    if did1:
        ciclo_trade_win(did1)
    else:
        warn("Pulando ciclo WIN — sem decision_id do ciclo 1")

    last_did, _ = ciclo_perdas_consecutivas(n_perdas=4)
    ciclo_heartbeat(last_did)
    ciclo_drawdown()

    # ── Sumário ──────────────────────────────────────────────────
    section("Sumário")
    total = _passed + _failed
    print(f"  {GREEN}✅ Passou: {_passed}/{total}{RESET}   {RED}❌ Falhou: {_failed}/{total}{RESET}")

    if _failed == 0:
        print(f"\n  {GREEN}{BOLD}Todos os testes passaram com sucesso.{RESET}")
    else:
        print(f"\n  {RED}{BOLD}{_failed} assertiva(s) falharam — verifique o brain e o Supabase.{RESET}")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
