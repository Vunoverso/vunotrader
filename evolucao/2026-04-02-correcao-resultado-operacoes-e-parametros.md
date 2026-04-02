# 2026-04-02 — Correção: Resultado de Operações Zerado + Parâmetros não Lidos

## Contexto

Auditoria pela navegação no painel https://vunotrader.vercel.app com conta `vunodecor@gmail.com` (plano Scale, modo Observer ativo).

## Problemas encontrados

### 1. Bug crítico — Página "Operações" sempre zerada

**Causa raiz:**
- `trade-opened` atualizava apenas `trade_decisions.outcome_status = "executing"` — nunca criava registro em `executed_trades`
- `trade-outcome` atualizava apenas `trade_decisions` (outcome_status, outcome_profit, etc.) — nunca criava `executed_trades` nem `trade_outcomes`
- Frontend `/app/operacoes` busca de `executed_trades` com JOIN em `trade_decisions` e `trade_outcomes` → tabela sempre vazia → 0 operações

**Sintoma observado:** Página de Operações mostra "Nenhuma operação encontrada" mesmo com o robô ativo e enviando sinais.

### 2. Parâmetros do painel não chegam ao robô

**Causa raiz:**
- EA MQL5 usa `input` fixos no MetaTrader (MaxDailyLoss, MaxDrawdown, TradingStart, TradingEnd)
- Backend `/api/mt5/signal` buscava apenas 3 parâmetros de SL/TP do `user_parameters`
- `SignalResponse` não retornava mode, limites, horários → EA nunca sabia o que foi configurado no painel Vuno

**Observação extra:** O usuário estava configurado como `mode = "observer"` no painel mas o EA não recebia essa informação do backend.

### 3. Modo Observer e símbolos divergentes

- Conta configurada como Observer → nenhuma execução real → sem TRADE_RESULT
- `user_parameters.allowed_symbols = "WIN$N, WDO$N"` mas screener rodando com XAUUSD, EURUSD, GBPUSD
- Não é um bug técnico, mas indica configuração inconsistente do usuário

### 4. Frontend Render com 500 global

**Diagnóstico confirmado por automação em Chrome externo e navegador integrado:**
- `https://vunotrader-web.onrender.com/auth/login` responde `500 Internal Server Error`
- `https://vunotrader-web.onrender.com/` também responde `500`
- portanto o problema não estava limitado à página de Auditoria

**Causa raiz mais provável identificada no código/config:**
- `render.yaml` do frontend publicava `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`
- `web/src/middleware.ts` exigia `NEXT_PUBLIC_SUPABASE_ANON_KEY` sem fallback
- `web/src/lib/supabase/client.ts` também exigia `NEXT_PUBLIC_SUPABASE_ANON_KEY` sem fallback
- com isso, o build local passava, mas o runtime no Render podia quebrar logo no middleware/browser client por chave pública ausente no nome esperado

## Correções aplicadas

### `backend/app/api/routes/mt5.py`

**`/api/mt5/trade-opened`:**
- Adicionado: após atualizar `trade_decisions`, cria registro em `executed_trades` com `status="open"`
- Idempotente: verifica se já existe registro para `trade_decision_id` antes de inserir

**`/api/mt5/trade-outcome`:**
- Refatorado completamente
- Busca `trade_decisions` para obter `entry_price`, `stop_loss`, `take_profit` e calcular duração
- Atualiza `trade_decisions` com resultado (mantido como estava)
- **Novo:** Busca ou cria `executed_trades` para este `decision_id`
- **Novo:** Cria `trade_outcomes` vinculado ao `executed_trade_id` (com guard anti-duplicata)
- Edge case tratado: se `trade-opened` não foi chamado, cria `executed_trades` como opened_at ≈ closed_at

**`SignalResponse` (schema):**
- Adicionados campos opcionais: `user_mode`, `daily_loss_limit`, `max_drawdown_pct`, `max_trades_day`, `trading_start`, `trading_end`, `allowed_symbols`

**`/api/mt5/signal`:**
- `user_parameters` query ampliada para buscar todos os campos operacionais
- Retorno inclui os parâmetros acima para o EA poder sincronizar com o painel

### `VunoTrader_v2.mq5`

- Adicionado: após receber resposta do sinal, lê `user_mode` do response
- Se `user_mode` não for vazio/null, sobrescreve `effMode` local com o valor do painel
- Log a cada 5 minutos informando o modo sincronizado
- Isso resolve: modo configurado no painel Vuno → EA respeita imediatamente sem precisar reconfigurar no MT5

### Frontend Render / Supabase

**`web/src/middleware.ts`:**
- agora aceita fallback na ordem:
	- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
	- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`
	- `SUPABASE_ANON_KEY`
- se URL/key estiverem ausentes, loga o problema e não derruba a aplicação no middleware

**`web/src/lib/supabase/client.ts`:**
- browser client passou a aceitar `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY` como fallback

**`render.yaml`:**
- adicionado `NEXT_PUBLIC_SUPABASE_ANON_KEY` no serviço `vunotrader-web`

**`web/src/app/app/layout.tsx` e `web/src/app/app/auditoria/page.tsx`:**
- adicionados fallbacks de runtime para falhas de Supabase/query sem causar 500 total da rota
- com cuidado para não capturar indevidamente o `DYNAMIC_SERVER_USAGE` do Next no build

## Arquivos impactados

- `backend/app/api/routes/mt5.py`
- `VunoTrader_v2.mq5`

## Próximos passos

1. **Deploy no Render** do backend atualizado para ativar as correções de `executed_trades` / `trade_outcomes`
2. **Recompilar** `VunoTrader_v2.mq5` no MetaEditor e reinstalar no MT5
3. **Deploy no Render** do frontend atualizado para publicar o fallback correto de env (`NEXT_PUBLIC_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY`)
4. **Conferir env vars no serviço `vunotrader-web`**: `NEXT_PUBLIC_SUPABASE_URL` e pelo menos uma das chaves públicas precisam existir de fato no painel do Render
5. **Considerar** adicionar leitura de `trading_start`, `trading_end`, `allowed_symbols` no EA (atualmente recebidos mas não consumidos dinamicamente)
6. **Migração Supabase**: verificar se colunas `outcome_profit`, `closed_at`, `duration_seconds` existem em `trade_decisions` — se não, aplicar migrations `20260402_000014_auditoria_v2_columns.sql` / `20260402_000015_auditoria_v2_pnl.sql`
7. **Resolver divergência de ativos**: alinhar `allowed_symbols` no painel com os ativos rodando no screener
8. **Testar fluxo completo** com conta demo: abrir trade → verificar se aparece em Operações → fechar → verificar resultado

## Riscos

- O `user_mode` retornado pelo backend pode ser `None` se o usuário não tiver `user_parameters` cadastrado. O EA mantém o comportamento local nesse caso.
- A migração das colunas extras de `trade_decisions` precisa ser validada no banco real — o backend já insere esses campos assumindo que existem.
