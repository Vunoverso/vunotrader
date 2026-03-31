# 2026-03-30 — Diferenciação Superior: Motor Explicável, Regime, Consistência, Flywheel

## Objetivo

Implementar os elementos que transformam o Vuno de "mais um painel de robô trader" em
"plataforma de controle e inteligência operacional com explicabilidade real".

Baseado em análise crítica do produto atual + benchmarking implícito contra produtos do mercado.

---

## O que foi implementado

### 1. Rationale Rico (linguagem humana)

**Arquivo:** `vunotrader_brain.py` → `TradingModel._generate_rationale()`

Cada decisão agora gera uma explicação em português que o usuário lê sem precisar saber ML:

```
COMPRA (alta convicção, 81.3%): RSI sobrevendido (28.4) | MACD histograma positivo (momentum de alta) | EMA9 acima da EMA21 (tendência de curto prazo: alta) | volume acima da média (2.1x)
```

Antes era: `"Ensemble RF+GB | WR=68%"` — inútil para o usuário.

Impacto: campo `rationale` nas `trade_decisions` vira dado legível no dashboard e auditoria.

---

### 2. Regime de Mercado (Market State Engine)

**Arquivo:** `vunotrader_brain.py` → `FeatureBuilder.detect_regime()`

Classifica o estado atual do mercado a partir das features já calculadas:
- **TENDENCIA**: EMAs alinhadas na mesma direção + spread > 0.8% + momentum_20 > 1%
- **VOLATIL**: ATR > 1.5% OU Bollinger width > 6%
- **LATERAL**: padrão por eliminação

O campo `regime` agora está incluso na response do socket:
```json
{"type": "SIGNAL", "signal": "BUY", "regime": "tendencia", ...}
```

E no rationale: `"[TENDENCIA] COMPRA (81.3%): RSI sobrevendido..."`

**Dashboard:** lê o regime do rationale da última decisão e exibe badge visual:
- ↗ Tendência (violeta)
- ↔ Lateral (slate)
- ⚡ Volátil (laranja)

---

### 3. Heartbeat → Status Real do Motor

**Arquivo:** `vunotrader_brain.py` → `SupabaseLogger.heartbeat()`

A cada MARKET_DATA recebido, o brain atualiza `robot_instances.last_seen_at`.

**Dashboard:** lê `last_seen_at` e calcula tempo desde o último heartbeat:
- < 5 min → Motor Ativo (badge verde pulsante + nome da instância + "há X min")
- ≥ 5 min → Motor desconectado (banner de aviso)

O topbar e o badge de modo do robô respondem ao estado real, não a placeholder.

---

### 4. Flywheel de Dados Anonimizados (ativo)

**Arquivo:** `vunotrader_brain.py` → `SupabaseLogger.log_anonymized_event()`

Chamado automaticamente na `_handle_trade_result`. A cada fechamento de trade:
- Grava em `anonymized_trade_events`
- User_id e org_id são hasheados com SHA256 + salt antes de gravar
- Nunca expõe identidade
- Inclui: mode, symbol, timeframe, side, confidence, risk_pct, result, pnl_points, regime, volatility

O flywheel passa a ser real — antes a tabela existia no schema mas nunca era populada.

---

### 5. Consistência (nova métrica de qualidade)

**Arquivo:** `web/src/app/app/dashboard/page.tsx`

Query dos últimos 20 trades ativos (BUY/SELL com resultado) → calcula:
```
consistência = wins / total_com_resultado × 100
```

Diferente de win_rate simples: considera apenas trades onde o motor decidiu entrar
(exclui HOLDs). Exibido no painel de estado do sistema quando há ≥ 5 registros:
- ≥ 60% verde
- 45-59% amarelo
- < 45% vermelho

Isso educa o usuário para qualidade operacional, não só lucro bruto.

---

### 6. Migration 000006: Controles de Risco Dinâmico

**Arquivo:** `supabase/migrations/20260330_000006_risk_controls_consistency.sql`

Adiciona a `user_parameters`:
- `max_consecutive_losses int DEFAULT 3` → parar após N perdas consecutivas
- `drawdown_pause_pct numeric DEFAULT 5.0` → pausar se drawdown diário > X%
- `auto_reduce_risk boolean DEFAULT true` → reduzir risco ao perder consistência

Índice full-text em `trade_decisions.rationale` para busca futura.

---

## Arquivos impactados

| Arquivo | Tipo de mudança |
|---|---|
| `vunotrader_brain.py` | FeatureBuilder.detect_regime + TradingModel._generate_rationale + SupabaseLogger.log_anonymized_event + SupabaseLogger.heartbeat + _handle_market_data (regime + heartbeat) + _handle_trade_result (flywheel) |
| `web/src/app/app/dashboard/page.tsx` | Queries de robot_instances (heartbeat), consistência, regime. UI: barra de estado do sistema |
| `supabase/migrations/20260330_000006_risk_controls_consistency.sql` | Campos de proteção dinâmica em user_parameters |

---

## Por que isso diferencia o Vuno

| Recurso | Outros robôs | Vuno |
|---|---|---|
| Explicação de cada decisão | Não existe | Linguagem humana com contexto |
| Estado do mercado visível | Não existe | Tendência / Lateral / Volátil em tempo real |
| Consistência operacional | Inexistente | Métrica separada de win rate |
| Motor ao vivo no dashboard | Não existe | Heartbeat com "ativo há X min" |
| Flywheel de dados | Não existe | auto-populado a cada fechamento |

---

## Pendências técnicas (próximos passos)

1. **Aplicar migration 000006** no Supabase remoto
2. **Brain: ler user_parameters.max_consecutive_losses** antes de processar MARKET_DATA
3. **Brain: pausar automaticamente** quando daily_loss_limit atingida (lê PnL do Supabase)
4. **Painel de parâmetros**: expor `max_consecutive_losses`, `drawdown_pause_pct` no form
5. **Job de retreino**: comparar modelo atual vs modelo retreinado; promover se superar

---

## Decisões não tomadas (e por quê)

- **Análise de padrão de falha automática** (lessons_learned): a tabela existe, mas a
  lógica de detecção requer volume de dados mínimo (~50 resultados). Registrado como
  próximo passo quando flywheel estiver populado.

- **Containerização do brain em Docker**: válido, mas fora do escopo imediato. O brain
  já tem graceful degradation para ausência de Supabase.

- **Job de treino contínuo**: Supabase Edge Functions não têm ambiente Python. Alternativa
  preferida: cron job externo ou worker separado. Registrado como Sprint 3.
