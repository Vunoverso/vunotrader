# 2026-04-03 - MT5: parametros remotos, execucao real e saldos do robo

## Objetivo

Corrigir a lacuna entre o painel web e o executor MT5 que fazia o sistema aparentar "sem conexao" mesmo com heartbeat e sinais chegando ao backend.

## Diagnostico consolidado

O problema observado no ambiente live nao era ausencia total de conexao MT5.

O fluxo parcial ja estava funcionando:

- heartbeat chegando ao backend
- `trade_decisions` sendo gravado
- auditoria exibindo sinais recentes
- dashboard marcando motor online

A lacuna estava no trecho de execucao real e sincronismo de parametros:

1. o endpoint MT5 lia `user_parameters` com `trading_start` e `trading_end`, mas o schema e o frontend usam `trading_start_time` e `trading_end_time`
2. quando essa leitura falhava, o EA caia nos defaults locais
3. os clientes MT5 nao aplicavam dinamicamente os parametros retornados pelo backend alem de `user_mode`
4. o screener e o EA single-asset falhavam ao enviar ordem sem logar retcode/descricao do erro do MT5
5. o schema de referencia nao registrava `robot_instances.initial_balance` e `robot_instances.current_balance`, embora backend e dashboard dependam desses campos

## Atualizacao - blindagem de execucao real

Com a nova evidencia do log do MT5, o gargalo restante ficou objetivo:

- `failed market buy XAUUSD [No prices]`

Isso confirma que o problema residual nao era mais falta de persistencia no backend, e sim fragilidade na camada de execucao do cliente MT5 para simbolos multiativos.

Foram tratados os seguintes pontos:

- execucao com retry e recaptura de tick por simbolo
- uso de `SymbolInfoTick` antes da ordem para evitar enviar market order sem preco valido
- `SetTypeFillingBySymbol` em vez de assumir filling fixo
- filtro de spread por ativo antes da execucao
- clamp de risco local para nao confiar cegamente no backend
- fallback local de sinal apenas para visibilidade quando a API falha, sem executar sem `decision_id`
- healing adicional no endpoint `/heartbeat` para criar/atualizar `executed_trades` quando a ordem abriu no MT5 mas o POST `/trade-opened` falhou

## Arquivos impactados

- `backend/app/api/routes/mt5.py`
- `VunoScreener_v3.mq5`
- `VunoTrader_v2.mq5`
- `supabase/migrations/20260403_000017_robot_instance_balances.sql`
- `projeto/supabase_schema.sql`

## Decisoes tomadas

### 1. Backend passa a ler parametros com compatibilidade de schema

Foi criado fallback no carregamento de `user_parameters`:

- primeiro tenta `trading_start_time` e `trading_end_time`
- se falhar, tenta legado com `trading_start` e `trading_end`

Tambem foi normalizada a serializacao de:

- horarios para string
- `allowed_symbols` para CSV consistente

### 2. Clientes MT5 agora aplicam parametros remotos em runtime

Foi introduzido uso efetivo de configuracao remota para:

- `max_drawdown_pct`
- `daily_loss_limit`
- `trading_start`
- `trading_end`
- `allowed_symbols`

A decisao foi manter os inputs locais como fallback e nao sobrescrever `input` diretamente, usando variaveis runtime.

### 3. Falhas de ordem e falhas HTTP agora ficam visiveis

Foram adicionados logs para:

- ATR indisponivel
- lote calculado zero
- `Trade.Buy` / `Trade.Sell` com `ResultRetcode` e `ResultRetcodeDescription`
- falha de `trade-opened`
- falha de `trade-outcome`
- falha de heartbeat
- HTTP nao-200 com corpo de resposta

Na etapa seguinte, a execucao passou a bloquear explicitamente casos como:

- sem tick valido para o simbolo
- mercado fechado ou lado indisponivel
- spread acima do limite por ativo
- lote calculado zero apos clamp de risco

Isso reduz o ponto cego onde o painel recebia sinais mas nenhuma operacao real era persistida.

### 4. Schema oficial passa a refletir os saldos usados pelo produto

Foi criada migration para adicionar em `robot_instances`:

- `initial_balance`
- `current_balance`

O objetivo foi alinhar schema, backend e dashboard para evitar novos ambientes com saldo sempre zero ou falha em selects.

## Alternativas analisadas e nao adotadas

### Armazenar modo efetivo do robo em nova coluna dedicada

Nao adotado neste ajuste para manter a mudanca pequena e focada no bloqueio principal.

Hoje o ganho principal vem de:

- parametros chegando corretamente
- executor consumindo esses parametros
- logs suficientes para identificar falha real de ordem

### Mover toda logica de risco/horario para o backend

Nao adotado agora.

O projeto continua com validacao local no MT5 como camada defensiva, enquanto o backend entrega a configuracao remota.

## Riscos e observacoes

- Ainda e necessario recompilar e reinstalar o EA/Screener no MT5 para que os ajustes de runtime e logging entrem em uso real.
- O arquivo `VunoTrader_v2.ex5` estava atrasado em relacao ao `VunoTrader_v2.mq5`; recompilacao continua obrigatoria se esse cliente estiver em uso.
- O ambiente Supabase remoto precisa receber a migration `20260403_000017_robot_instance_balances.sql`.
- Sem acesso ao MetaEditor neste workspace, a validacao de MQL5 ficou limitada a analise estatica do editor.
- O fallback local de sinal foi mantido sem execucao real propositalmente; executar sem `decision_id` quebraria auditoria, reconciliacao e persistencia de `executed_trades`.

## Proximos passos

1. Aplicar a migration nova no Supabase remoto.
2. Recompilar `VunoScreener_v3.mq5` e/ou `VunoTrader_v2.mq5` no MetaEditor do MT5 em uso.
3. Observar os logs novos no MT5 para identificar se a falha remanescente esta em horario, risco, lote, simbolo nao permitido ou rejeicao da corretora.
4. Revalidar no painel se `Operacoes` comeca a receber `executed_trades` e se `Banca Atual` sai de zero.
