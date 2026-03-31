# 2026-03-31 - CLI Python direto para controlar MetaTrader 5

## Contexto

O projeto ja possuia o fluxo principal baseado em:
- EA MQL5 no terminal MT5
- brain Python por socket TCP
- persistencia e auditoria no Supabase

Esse fluxo continua sendo a arquitetura principal do Vuno.

Porem, faltava um caminho local e simples para rodar no CMD e controlar o MetaTrader 5 diretamente pelo Python, sem depender do EA.

## Objetivo

Adicionar um bot/controlador Python executavel via linha de comando no Windows para:
- conectar no terminal MT5 local
- consultar status da conta
- consultar cotacoes
- listar posicoes
- enviar ordens de compra e venda
- fechar posicoes
- executar uma estrategia simples em loop

## Arquivos impactados

- `scripts/mt5_cmd_bot.py`
- `brain-requirements.txt`
- `brain.env.example`
- `README.md`

## Decisao tecnica

Foi criado o script `scripts/mt5_cmd_bot.py` usando o pacote oficial `MetaTrader5`.

Comandos adicionados:
- `status`
- `quote`
- `positions`
- `buy`
- `sell`
- `close`
- `close-all`
- `run-strategy`

A estrategia inicial e propositalmente simples:
- cruzamento de EMA rapida e lenta
- filtro de RSI
- opcao de `dry-run`
- opcao de fechar posicao oposta antes de inverter

## Separacao de responsabilidades

O novo CLI e um caminho paralelo e local.

Ele NAO substitui:
- o brain `vunotrader_brain.py`
- o EA `VunoTrader_v2.mq5`
- a rastreabilidade de decisoes no Supabase

Isso foi mantido explicito na documentacao para evitar confusao de arquitetura.

## Configuracao

Foram adicionadas variaveis opcionais em `brain.env.example`:
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`
- `MT5_PATH`
- `MT5_TIMEOUT_MS`
- `MT5_MAGIC`
- `MT5_DEVIATION`
- `MT5_TIMEFRAME`

Tambem foi adicionada a dependencia:
- `MetaTrader5>=5.0.45`

## Riscos e observacoes

- O script depende de terminal MT5 instalado localmente no Windows.
- O pacote `MetaTrader5` precisa ser compativel com a versao do Python em uso.
- Como o CLI envia ordens direto ao terminal, o uso recomendado inicial e em conta demo.
- Esse caminho nao grava trade_decisions, executed_trades nem trade_outcomes no backend atual.

## Alternativas avaliadas

1. Reaproveitar o `vunotrader_brain.py` como CLI direto de execucao.
Motivo de nao adotar agora: misturaria duas responsabilidades diferentes no mesmo entrypoint.

2. Forcar todo controle a passar apenas pelo EA MQL5.
Motivo de nao adotar agora: nao atende o pedido de um bot Python rodando no CMD e controlando o MT5 diretamente.

## Proximos passos

1. Adicionar modo de risco percentual por saldo para calcular lote automaticamente.
2. Integrar esse CLI ao backend Vuno quando houver necessidade de auditoria direta sem EA.
3. Criar comando de backtest local para validar a estrategia simples antes de operar.

## Atualizacao 2026-03-31 - Ajuste de filling mode apos execucao real

### Contexto

No primeiro envio real de ordem demo (`BUY EURUSD 0.01`) o retorno foi:
- `retcode=10030`
- `comment=Unsupported filling mode`

### Correcao aplicada

Arquivo ajustado:
- `scripts/mt5_cmd_bot.py`

Mudanca:
- Removido `type_filling` fixo em `ORDER_FILLING_IOC`.
- Implementado fallback automatico de filling mode em ordem de tentativa:
	1. `symbol_info.filling_mode` (quando valido)
	2. `ORDER_FILLING_IOC`
	3. `ORDER_FILLING_FOK`
	4. `ORDER_FILLING_RETURN`
- Aplicado tanto para abertura (`send_market_order`) quanto fechamento (`close_position`).

### Resultado

Ordem de teste executada com sucesso na conta demo:
- `retcode=10009`
- `comment=Request executed`
- ticket aberto em `EURUSD` com SL/TP corretamente definidos.

### Risco/observacao

- Brokers diferentes podem ter restricoes adicionais de execucao alem de filling mode.
- O fallback cobre o caso mais comum sem exigir ajuste manual por corretora.