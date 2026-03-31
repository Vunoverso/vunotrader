# 2025-07-17 — Dashboard KPIs reais + Página /estudos/[id]

## Objetivo

Substituir dados hardcoded no Dashboard por consultas reais ao Supabase
e criar a página de detalhe de material de estudo com exibição de chunks.

---

## 1. Dashboard KPIs reais

### Arquivos impactados
- `web/src/app/app/dashboard/page.tsx`

### Mudanças aplicadas

#### Novas queries Supabase (Server Component)

1. **`todayDecRaw`** — `trade_decisions` filtrada por `user_id` e `created_at >= todayStart`,
   embeddando `executed_trades(id, status, opened_at, closed_at, trade_outcomes(result, pnl_money))`.
   Derivados: `todayTotalTrades`, `todayOpenTrades`, `todayPnl`.

2. **`winRateCalc`** — reutiliza `recentOutcomes` (20 registros já buscados) para calcular
   win rate quando há ≥ 5 resultados, senão retorna `null`.

3. **`recentClosedRaw`** — últimas 30 decisões, filtradas para as 5 mais recentes com
   `executed_trades.status === "closed"`. Exibidas na tabela "Operações recentes".

#### Objeto `metrics` corrigido
Antes: `totalTrades: 0, winRate: null, pnl: 0, openTrades: 0` (hardcoded).
Depois: valores computados das queries acima.

#### Seção "Operações recentes"
- Substituído `<EmptyState>` estático por lista condicional de `recentClosed`.
- Cada linha navega para `/app/operacoes/${et.id}` via `<Link>`.
- Badge W/L, símbolo, timeframe, lado, modo, PnL e horário de fechamento.

#### Cards de status Brain / MT5
- Ambos os cards agora usam `motorOnline` para alternar entre estados Online / Off.
- Quando online: exibe nome da instância e `motorLastSeenLabel`.
- Quando offline: exibe msg de orientação com link para `/app/instalacao`.

#### Link import
Adicionado `import Link from "next/link"` para substituir `<a>` em navegação interna.

---

## 2. Página /estudos/[id]

### Arquivos criados
- `web/src/app/app/estudos/[id]/page.tsx` — Server Component
- `web/src/app/app/estudos/[id]/reprocess-button.tsx` — Client Component

### Arquivos modificados
- `web/src/components/app/estudos-manager.tsx` — título agora é `<Link>` para `/app/estudos/${item.id}`

### Funcionalidades da página de detalhe

- **Segurança**: verifica `organization_id` do material contra org do usuário autenticado.
  Em caso de divergência (ou material não encontrado), retorna `notFound()`.
- **Dados exibidos**: título, badge de tipo (PDF / YouTube / Nota), badge de status
  (Pendente / Processando / Processado / Erro) com cor semântica, data de processamento.
- **Erro de processamento**: card vermelho com mensagem raw quando `processing_error` está preenchido.
- **Fonte**: link externo para `source_url` quando disponível.
- **Resumo**: texto gerado pela IA em card separado; placeholder quando ausente.
- **Chunks de RAG**: lista colapsável (HTML `<details>`) com número do chunk, preview de
  120 chars, contagem de tokens, texto completo expandido ao clicar.
  Footer do card mostra total de fragmentos e soma de tokens.
- **Botão Reprocessar**: `ReprocessButton` chama `POST /api/study/ingest` com o `materialId`,
  exibe feedback de loading / sucesso / erro sem reload de página.

---

## Decisão técnica

- **Win rate via `recentOutcomes`**: evitou query adicional reutilizando dados já disponíveis
  na página. Só calcula quando há ≥ 5 registros para evitar taxa enganosa.
- **`recentClosedRaw` com `.limit(30)` + filtro client-side**: mais simples que filtrar
  `executed_trades.status` via PostgREST (filtros em relações embeddadas são limitados no
  Supabase JS v2). Alternativa descartada: subquery com `inner join` via `.filter()`.
- **`<details>`/`<summary>` para chunks**: sem estado React, sem bundle JS extra, compatível
  com SSR. Alternativa descartada: accordion com `useState` (requer "use client").

---

## Próximos passos sugeridos

- Adicionar paginação ou infinite scroll na lista de chunks para materiais muito grandes.
- Considerar websocket / Supabase Realtime para atualizar status do processamento sem reload.
- Dashboard: adicionar seletor de período (hoje / semana / mês) para os KPIs.
