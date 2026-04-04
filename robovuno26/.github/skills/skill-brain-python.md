# Habilidade: Brain Python (FastAPI)

## Quando usar
Criar, editar ou revisar o serviço de decisão em `brain/main.py`.

## Contrato fixo — não quebrar

**POST /decide**

Headers obrigatórios:
- `x-brain-secret` — autenticação
- `x-tenant-id` — UUID do tenant
- `x-robot-id` — UUID do robô

Body (`MarketContext`):
```json
{
  "symbol": "EURUSD",
  "timeframe": "H1",
  "close_prices": [1.08, 1.082, ...],
  "mode": "demo"
}
```

Resposta (`DecisionResponse`):
```json
{
  "signal": "BUY",
  "confidence": 72.5,
  "rationale": "Explicação em português.",
  "regime": "tendência_alta",
  "risk_ok": true,
  "timestamp": "2026-04-02T12:00:00Z"
}
```

**POST /heartbeat**
```json
{
  "robot_token": "...",
  "symbol": "EURUSD",
  "account": "***123"
}
```

## Regras de segurança

- Nunca logar `robot_token`, senha ou chave.
- Conta MT5 sempre anonimizada (apenas últimos 3 dígitos).
- `BRAIN_SECRET` só via variável de ambiente.
- `SUPABASE_SERVICE_KEY` só no brain, nunca no frontend.
- Erros não expõem stack trace ao cliente.

## Padrão de autenticação

```python
def verify_secret(x_brain_secret: str = Header(...)):
    if not BRAIN_SECRET or x_brain_secret != BRAIN_SECRET:
        raise HTTPException(status_code=401, detail="Não autorizado")
```

## Padrão de persistência no Supabase

```python
async def persist_decision(tenant_id: str, robot_id: str, result: DecisionResponse, mode: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/trade_decisions",
            json={
                "tenant_id": tenant_id,
                "robot_id": robot_id,
                "signal": result.signal,
                "confidence": result.confidence,
                "rationale": result.rationale,
                "regime": result.regime,
                "mode": mode,
                "ai_cost": 0,
            },
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            timeout=5,
        )
```

## Lógica de decisão atual

Cruzamento de médias simples (SMA5 × SMA20):
- `SMA5 > SMA20` e preço acima de SMA5 → **BUY**
- `SMA5 < SMA20` e preço abaixo de SMA5 → **SELL**
- Diferença < 0.1% ou confiança < 30 → **HOLD**

Para adicionar nova lógica: criar função separada e chamar dentro de `decide()`. Não misturar cálculo com persistência.

## Variáveis de ambiente obrigatórias

```
BRAIN_SECRET=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
FRONTEND_URL=
```
