Data: 2026-04-03

# MT5 com multiplos ativos por lista no mesmo EA

## Objetivo

Remover a dependencia de abrir ou arrastar o EA em varios graficos apenas para acompanhar varios ativos ao mesmo tempo.

## Situacao encontrada

- o EA lia apenas `_Symbol` e `_Period` do grafico onde estava anexado
- na pratica, o usuario precisava repetir o arraste em varios graficos para monitorar varios ativos
- o pedido de uso mostrou friccao real no MT5: ao arrastar, o comportamento natural da plataforma continua sendo um grafico por vez

## Arquivos impactados

- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-symbols.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/ligacao-mt5-real.md
- backend/static/index.html
- README.md

## Decisao tomada

- foi criado o input `InpAdditionalSymbols` no EA para aceitar uma lista de ativos extras separada por virgula
- o `OnTimer()` passou a exportar snapshot e processar comando para cada simbolo configurado
- o controle de ultimo comando processado passou a ser por simbolo, evitando bloquear ativos diferentes entre si
- o feedback de operacao fechada passou a aceitar qualquer simbolo monitorado pelo mesmo EA
- o tutorial e a documentacao agora explicam o fluxo multi-ativo sem precisar anexar o EA em varios graficos

## Alternativas descartadas

- obrigar um grafico por ativo como unica forma oficial: descartado porque mantinha a friccao pratica relatada pelo uso real
- tentar resolver multi-ativo no frontend SaaS: descartado porque o gargalo estava no EA do MT5, nao no painel
- suportar agora o mesmo ativo em varios timeframes pelo mesmo arquivo de comando: descartado nesta iteracao por exigir redesenho do contrato de comando para incluir timeframe no roteamento

## Validacao executada

- leitura critica do fluxo do EA apos ajuste
- validacao de erros nos arquivos MQL5 alterados
- validacao de erros nos arquivos de documentacao/tutorial atualizados

## Riscos e observacoes

- os ativos extras usam o mesmo timeframe do grafico onde o EA foi anexado
- para o mesmo ativo em timeframes diferentes, ainda e mais seguro usar um grafico separado por timeframe
- o usuario precisa recompilar o EA no MetaEditor para usar o novo input

## Proximos passos

1. expor no painel a ultima analise com simbolo e timeframe para confirmar visualmente quais ativos estao rodando
2. estudar evolucao futura do contrato `.command.json` para suportar o mesmo simbolo em multiplos timeframes sem colisao