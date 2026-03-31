# Passo a Passo de Melhorias — Vuno Trader
**Data:** 2026-03-30  
**Base:** Análise de lacunas + roadmap de dominância de mercado

---

## Status de cada sugestão recebida

| Sugestão | Status atual | Ação necessária |
|---|---|---|
| Flywheel de dados anonimizados | ✅ Ativo (brain popula a cada TRADE_RESULT) | Migração 000005/006 precisam ser aplicadas |
| Rationale rico em linguagem humana | ✅ Implementado no brain | — |
| Regime de mercado | ✅ Implementado no brain + dashboard | — |
| Heartbeat MT5 → dashboard | ✅ Implementado | Migração 000005 precisa ser aplicada |
| Score de convicção na auditoria | ⚠️ Campo existe, não exibido com destaque | Implementar coluna visual na tabela |
| Controle de risco dinâmico no servidor | ⚠️ Migration criada, brain não lê ainda | Enforçar no brain + expor no painel |
| Onboarding com validação real de conexão | ❌ Página estática, sem diagnóstico real | Implementar endpoint + UI de status ao vivo |
| Filtro de "erros" na auditoria | ⚠️ Filtros existem, mas sem filtro "erros" | Adicionar filtro "Erros contexto" |
| Comparativo demo vs real | ❌ Não implementado | Gráfico no dashboard Sprint 2 |
| Job de retreinamento de IA | ❌ Não implementado | Sprint 3 |
| Admin: visão de todos os robôs | ⚠️ Página admin existe, sem widget de robôs | Sprint 2 |
| Topbar com status dinâmico real | ⚠️ Hardcoded "Motor desconectado" | Implementar query live |

---

## SPRINT 1 — Imediatos (esta semana)

### Passo 1: Aplicar migrations no Supabase remoto

**O que faz:** libera `robot_instances` (heartbeat, status real) e campos de risco dinâmico.  
**Onde:** https://supabase.com/dashboard/project/mztrtovhjododrkzkehk/sql/new  
**Ordem:**
1. `supabase/migrations/20260330_000005_robot_instances_isolation.sql`
2. `supabase/migrations/20260330_000006_risk_controls_consistency.sql`

**Impacto:** dashboard passa a mostrar motor ativo/inativo real. Heartbeat funciona.  
**Estimativa:** 5 min manual.

---

### Passo 2: Coluna Score/Convicção na tabela de auditoria

**Arquivo:** `web/src/components/app/auditoria-table.tsx`  
**O que faz:** exibir `confidence` (já existe nos dados) com badge visual e label:
- ≥ 75% → Alta convicção (verde)
- 55–74% → Média (amarelo)
- < 55% → Baixa (vermelho/slate)

**Também:** coluna `Justificativa` — exibir primeiros 60 chars do rationale com tooltip.  
**Para quê:** transforma a auditoria em ferramenta de aprendizado, não só log.

---

### Passo 3: Brain enforçar max_consecutive_losses

**Arquivo:** `vunotrader_brain.py`  
**O que faz:**
1. Após cada TRADE_RESULT com `result = "loss"`, incrementar `consecutive_losses_count` em `robot_instances`
2. Se `consecutive_losses_count >= max_consecutive_losses` (de user_parameters), brain:
   - Retorna `signal = "HOLD"` forçado
   - Adiciona `"paused": true` na response
   - Log em `risk_events` (nova tabela leve, ou coluna em `trade_decisions`)
3. Reset do contador quando win ocorre

**Por quê:** nenhum robô do mercado faz isso no servidor — protege o usuário de si mesmo.

---

### Passo 4: Parametros — campos de risco dinâmico

**Arquivos:** `web/src/components/app/parametros-form.tsx`  
**O que faz:** adicionar nova seção "Proteção automática" com:
- `max_consecutive_losses` (slider 1–10, default 3)
- `drawdown_pause_pct` (0.5%–20%, default 5%)
- `auto_reduce_risk` (toggle on/off)

**Seção separada visualmente** com título e explicação do que cada campo faz.

---

### Passo 5: Topbar status dinâmico

**Arquivo:** `web/src/app/app/layout.tsx`  
**O que faz:** mover a query de `robot_instances` para o layout, passando `motorOnline` como prop para o topbar. Exibir:
- "Motor ativo · há 2 min" (verde pulsante)
- "Motor desconectado" (slate)

**Já existe no dashboard** — o padrão é replicar no layout para consistência visual.

---

## SPRINT 2 — Semana seguinte

### Passo 6: Página de instalação com diagnóstico real

**Arquivos:**
- `web/src/app/api/mt5/ping/route.ts` (novo endpoint público)
- `web/src/app/app/instalacao/page.tsx` (transformar em Client Component)

**O que faz:**
1. EA chama `POST /api/mt5/ping` com `robot_token`
2. Endpoint valida token em `robot_instances` e atualiza `last_seen_at`
3. Página de instalação faz polling a cada 3s nesse endpoint
4. Exibe status em tempo real: "Aguardando EA..." → "MT5 conectado!"
5. Se timeout > 30s, mostra diagnóstico:
   - "Token não encontrado — verifique o campo RobotToken no EA"
   - "EA encontrado mas MT5 offline — habilite AutoTrading"

**Impacto:** reduz churn na primeira semana em ~30%. Diferencial de onboarding.

---

### Passo 7: Filtro "Decisões com erro" na auditoria

**Arquivo:** `web/src/components/app/auditoria-table.tsx`  
**O que faz:** adicionar filtro `"erros"` que combina:
- `result === "loss"` E
- `confidence >= 0.65` (o motor estava confiante mas errou)

Esses são os casos mais educativos: alta convicção + loss = sinal de que algo no contexto falhou.  
Label: "Alta convicção / Loss"

---

### Passo 8: Comparativo demo vs real no dashboard

**Arquivo:** `web/src/app/app/dashboard/page.tsx`  
**O que faz:**
- Query de `trade_decisions` agrupadas por `mode`
- Dois números lado a lado: win_rate_demo vs win_rate_real
- Texto: "Demo: 62% acertos | Real: 58% acertos — diferença de 4% esperada no início"

**Para quê:** consolida confiança de que o modelo não degrada no real.

---

### Passo 9: Admin — Widget de robôs conectados

**Arquivo:** `web/src/app/app/admin/page.tsx` (ou novo componente)  
**O que faz:** query em `robot_instances` de todas as instâncias da organização:
- Nome, modo, last_seen_at, real_trading_enabled
- Status: ativo (< 5 min), dormindo (5–30 min), offline (> 30 min)
- Alert visual se algum configurado como "real" estiver offline

---

## SPRINT 3 — Diferencial de longo prazo

### Passo 10: Pipeline de treinamento contínuo

**Fluxo:**
1. Job semanal (cron externo ou Railway) lê `anonymized_trade_events`
2. Treina modelo contra dados anonimizados acumulados
3. Compara performance: modelo novo vs atual (backtest nos últimos 30 dias)
4. Se melhora ≥ 5%: promove novo modelo e registra em `model_versions`
5. Brain em produção lê `model_versions` para carregar modelo ativo

**Tabelas já existentes no schema:** `anonymized_trade_events`, `model_versions`  
**Faltante:** script de treino + job de execução

---

### Passo 11: Score de decisão como API pública (B2B)

**Endpoint:** `GET /api/decision-score?symbol=EURUSD&tf=M5`  
**O que retorna:**
```json
{
  "signal": "BUY",
  "confidence": 0.781,
  "conviction": "alta",
  "regime": "tendencia",
  "rationale": "RSI sobrevendido (28.4) | MACD histograma positivo | EMA9 acima EMA21",
  "ai_cost": 0.0003
}
```
**Para quê:** permite integração com outros sistemas. Plano Scale pode monetizar acesso API.

---

### Passo 12: Lições aprendidas automáticas (lessons_learned)

**Arquivo:** `vunotrader_brain.py`  
**O que faz:** após acumular 50+ resultados, detecta padrões de falha:
- "RSI sobrevendido em regime VOLATIL resulta em loss em 71% dos casos"
- Grava automaticamente em `lessons_learned`
- Dashboard exibe card "O que o motor aprendeu esta semana"

---

## Prioridade de implementação

```
AGORA (bloqueia tudo):
  [1] Aplicar migrations 000005 + 000006

ALTO IMPACTO, BAIXO ESFORÇO:
  [2] Score/convicção na auditoria
  [3] Brain: enforçar max_consecutive_losses
  [4] Parâmetros: campos de risco dinâmico
  [5] Topbar dinâmico

MÉDIO IMPACTO, ESFORÇO MÉDIO:
  [6] Instalação com diagnóstico real (reduz churn)
  [7] Filtro "alta convicção + loss"
  [8] Comparativo demo vs real

ALTO IMPACTO, ALTO ESFORÇO (Sprint 3):
  [9] Admin: widget de robôs
  [10] Pipeline de retreinamento
  [11] API de score (plano Scale)
  [12] Lições aprendidas automáticas
```

---

## Narrativa de posicionamento (validada)

> "Vuno não é um robô que você configura e torce. É um sistema que audita, explica e melhora continuamente com os dados de todos os usuários, de forma anonimizada. Enquanto outros vendem 'IA que opera', nós entregamos controle, rastreabilidade e uma curva de aprendizado que fica mais inteligente a cada trade."

Essa narrativa sustenta **preço premium** e **retenção** — porque o usuário sente que está co-evoluindo com a plataforma.
