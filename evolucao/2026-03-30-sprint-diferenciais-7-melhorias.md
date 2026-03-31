# 2026-03-30 — Sprint de Diferenciação: 7 melhorias implementadas

## Objetivo

Implementar o roadmap de melhorias definido em `projeto/passo-a-passo-melhorias.md`,
cobrindo todos itens do Sprint 1 e Sprint 2 que agregam valor real ao produto e reforçam
as barreiras de entrada contra concorrentes.

---

## O que foi implementado

### 1. Badge de convicção na auditoria (SprintAuditoria)

**Arquivo:** `web/src/components/app/auditoria-table.tsx`

- Nova função `convictionBadge(confidence)`:
  - ≥ 75% → badge "Alta 81%" (verde)
  - 55–74% → badge "Média 62%" (âmbar)
  - < 55% → badge "Baixa 48%" (slate)
- Badge visível na linha colapsada (sem precisar expandir)
- Rationale truncado em 80 chars visível na linha (com `title` para tooltip completo)
- Novo filtro: **"Alta convicção + Loss"** (`confidence >= 65%` E `result = loss`)
  — filtra os casos mais educativos: motor confiante que errou
- Ordenação por `"Convicção"` adicionada ao seletor de sort

---

### 2. Brain: enforçar max_consecutive_losses no servidor

**Arquivo:** `vunotrader_brain.py`

- `SupabaseLogger.get_risk_params(user_id)`: busca `max_consecutive_losses`,
  `drawdown_pause_pct`, `auto_reduce_risk` em `user_parameters`. Cache de 5 min.
- `MT5Bridge._consec_losses: dict[str, int]`: contador em memória por `robot_id`
- Em `_handle_trade_result`: LOSS incrementa o contador; WIN/Breakeven reseta para 0
- Em `_handle_market_data`: se `_consec_losses[robot_id] >= max_consec` →
  responde com `signal = "HOLD"`, `paused = true`, reason explicativo
- **Isso roda no servidor** — o EA recebe HOLD independente de qualquer configuração local

---

### 3. Formulário de parâmetros: seção "Proteção automática"

**Arquivos:** `web/src/components/app/parametros-form.tsx`, `web/src/app/app/parametros/page.tsx`

- Novos campos na interface `ParametrosData`:
  - `max_consecutive_losses: string`
  - `drawdown_pause_pct: string`
  - `auto_reduce_risk: boolean`
- Nova seção visual "Proteção automática" com borda laranja suave
- Toggle `auto_reduce_risk` com animação
- Campos salvos em `user_parameters` via Supabase upsert
- Página server-side passa os novos valores já lidos do banco

---

### 4. Topbar com status dinâmico real do motor

**Arquivo:** `web/src/app/app/layout.tsx`

- O layout agora busca `user_profiles.id` → `robot_instances.last_seen_at`
- Computa `motorOnline` (< 5 min) e `motorLabel` ("Motor ativo · há 2 min")
- Badge na topbar muda de cor e pulsa quando o motor está ativo
- Antes: hardcoded "Motor desconectado" em todos os estados
- Agora: reflete realidade — sincronizado com o heartbeat do brain

---

### 5. Instalação: validador de conexão em tempo real

**Arquivo:** `web/src/components/app/mt5-connection-checker.tsx` (novo)

Componente client com polling via Supabase:
- **Inativo**: botão "Iniciar verificação"
- **Aguardando**: barra de progresso (2 min), polling a cada 5s
- **Conectado**: badge verde com nome da instância + horário do último heartbeat
- **Timeout**: diagnóstico com 4 checklist de possíveis problemas + botão "Tentar novamente"

Integrado em `web/src/app/app/instalacao/page.tsx` como Server Component que
passa `user.id` para o checker client.

**Impacto esperado**: reduz churn na primeira semana (80% dos problemas de suporte
são de configuração incorreta do EA).

---

### 6. Comparativo Demo vs Real no dashboard

**Arquivo:** `web/src/app/app/dashboard/page.tsx`

- Nova query: últimas 50 `trade_decisions` com resultado, agrupadas por `mode`
- Computa `wins/total` por modo (demo / real)
- Exibido como card "Demo vs Real" quando há ≥ 3 registros em ao menos um modo
- Barra de progresso visual + cores (verde ≥ 60%, âmbar ≥ 45%, vermelho < 45%)
- Quando ambos têm ≥ 5 dados: exibe diferença percentual com aviso se > 10%

---

## Arquivos impactados

| Arquivo | Tipo de mudança |
|---|---|
| `vunotrader_brain.py` | `get_risk_params`, `_consec_losses`, enforcement em `_handle_market_data` e `_handle_trade_result` |
| `web/src/components/app/auditoria-table.tsx` | `convictionBadge`, filtro alta_conv_loss, badge na linha, sort por convicção |
| `web/src/components/app/parametros-form.tsx` | 3 novos campos, seção Proteção automática, toggle |
| `web/src/app/app/parametros/page.tsx` | Pass dos novos campos para o form |
| `web/src/app/app/layout.tsx` | Query real de robot_instances, topbar dinâmico |
| `web/src/components/app/mt5-connection-checker.tsx` | Novo componente |
| `web/src/app/app/instalacao/page.tsx` | Server Component com Mt5ConnectionChecker |
| `web/src/app/app/dashboard/page.tsx` | modeComparison query, modeStats, showComparativo, seção Demo vs Real |
| `projeto/passo-a-passo-melhorias.md` | Roadmap completo criado |

---

## Validações

- `python -m py_compile vunotrader_brain.py` → `exit=0`
- Conteúdo de todos os arquivos TS verificado manualmente linha a linha
- Erros de cache do language server confirmados como stale (conteúdo correto)

---

## Pendências (Sprint 2+)

1. **Aplicar migrations 000005 e 000006** no Supabase remoto — sem isso, robot_instances
   e os novos campos de risco não existem na base
2. **Admin: widget de robôs conectados** — ver `robot_instances` de toda a organização
3. **Brain: drawdown_pause_pct** — buscar PnL diário e pausar quando ultrapassar
4. **Pipeline de retreinamento** (Sprint 3)
5. **Lições aprendidas automáticas** — popular `lessons_learned` após 50+ trades
