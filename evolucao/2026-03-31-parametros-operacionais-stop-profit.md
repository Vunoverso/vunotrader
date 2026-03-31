# 2026-03-31 - Parametros operacionais de stop e profit

## Contexto

A pagina de parametros ja cobria metas agregadas e guardrails de risco, mas ainda nao expunha a politica operacional por trade.

Tambem havia divergencia entre backend e UI: `capital_usd` ja era usado pelo brain para drawdown percentual, mas nao aparecia no formulario nem no schema consolidado em `projeto/supabase_schema.sql`.

## Objetivo

Adicionar ao painel do Vuno configuracoes de saida por operacao para orientar stop loss e take profit, mantendo claro que os valores efetivamente executados continuam vindo do MetaTrader para o Vuno.

## Decisao

Foram adicionados ao `user_parameters`:

- `capital_usd`
- `per_trade_stop_loss_mode`
- `per_trade_stop_loss_value`
- `per_trade_take_profit_rr`

No frontend, a tela `/app/parametros` passou a exibir:

- capital de referencia para calculo de drawdown e risco
- modo de stop loss por trade (`ATR` ou `pontos fixos`)
- valor operacional do stop loss
- take profit por relacao risco-retorno (`R`)

Foi mantido um texto explicito na UI informando que entrada, stop e take profit executados continuam sendo capturados no MT5 e enviados ao Vuno apos a execucao.

## Arquivos impactados

- `web/src/components/app/parametros-form.tsx`
- `web/src/app/app/parametros/page.tsx`
- `projeto/supabase_schema.sql`
- `supabase/migrations/20260331_000011_user_parameters_trade_exit_controls.sql`
- `vunotrader_brain.py`

## Riscos e observacoes

- Nesta etapa, os novos campos ficam persistidos e disponiveis ao brain, mas o EA ainda calcula SL/TP localmente com ATR e RR fixo.
- Para a configuracao impactar a execucao em tempo real, falta um proximo passo de consumo desses campos no contrato Brain -> MT5.
- O fluxo MT5 -> Vuno para valores executados ja estava correto e foi preservado.

## Proximos passos

1. Ajustar a resposta `SIGNAL` do brain para incluir `suggested_stop_loss` e `suggested_take_profit`.
2. Atualizar o EA `VunoTrader_v2.mq5` para priorizar niveis enviados pelo brain quando disponiveis.
3. Exibir na auditoria a diferenca entre politica configurada e valores efetivamente executados.