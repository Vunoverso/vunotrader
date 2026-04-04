Data: 2026-04-03

# Cooldown de reentrada para evitar entradas seguidas

## Objetivo

Reduzir reentradas muito proximas no mesmo ativo quando o robo continua lendo o mercado em ciclos curtos.

## Situacao encontrada

- o EA ja bloqueava posicoes simultaneas pelo limite por simbolo
- o robo continuava analisando em ciclos curtos de timer
- quando uma posicao fechava rapido e o sinal persistia, nao existia respiro explicito antes de uma nova entrada no mesmo ativo

## Arquivos impactados

- backend/app/models.py
- backend/app/parameter_store.py
- backend/migrations/sqlite/0002_add_reentry_cooldown_to_user_parameters.sql
- backend/migrations/postgres/0002_add_reentry_cooldown_to_user_parameters.sql
- backend/tests/test_operational_flow.py
- backend/static/index.html
- backend/static/js/app.js
- agent-local/app/runtime_contract.py
- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-runtime.mqh
- mt5/vuno-bridge/vuno-bridge-execution.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- README.md
- mt5/ligacao-mt5-real.md

## Decisao tomada

- foi criado o parametro `reentry_cooldown_seconds` no contrato de `user_parameters`
- o backend passou a persistir esse campo com migration dedicada
- o agente local passou a sincronizar esse valor para `runtime.settings.json`
- o painel passou a exibir o campo como `Respiro entre entradas no mesmo ativo (s)`
- o EA agora consulta o historico de deals fechados do mesmo simbolo e bloqueia nova entrada ate o cooldown expirar

## Alternativas descartadas

- apenas aumentar o timer de leitura do EA: descartado porque reduziria responsividade sem resolver a causa raiz
- bloquear novas entradas por um tempo global: descartado porque o problema e por ativo, nao da conta inteira
- depender apenas de `max_positions_per_symbol`: descartado porque essa trava so impede posicao simultanea, nao reentrada logo apos o fechamento

## Validacao executada

- validacao de erros nos arquivos backend, frontend e MQL5 afetados
- migration `0002` confirmada como aplicada no banco local atual
- leitura manual da tela confirmando o novo campo em `Protecoes`
- teste backend ajustado para validar o novo campo no endpoint `/api/parameters` e no `/api/agent/runtime-config`

## Riscos e observacoes

- o cooldown usa o historico do MT5 para o simbolo e magic number do EA
- o valor default foi definido em 60 segundos, mas pode ser zerado para desativar o bloqueio
- para o EA obedecer o novo parametro, o arquivo precisa ser recompilado no MetaEditor apos esta mudanca

## Proximos passos

1. expor no painel a ultima entrada e o tempo restante de cooldown por ativo
2. avaliar cooldown separado por ativo e timeframe quando o contrato de comando evoluir para suportar timeframe no roteamento