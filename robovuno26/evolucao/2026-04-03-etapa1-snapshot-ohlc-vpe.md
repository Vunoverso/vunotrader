Data: 2026-04-03

# Etapa 1 do VPE: snapshot com serie de candles OHLC

## Objetivo

Executar a primeira etapa da implantacao do motor de Price Action: ampliar o snapshot do MT5 para enviar serie de candles ao backend sem quebrar o motor atual.

## Situacao encontrada

- o snapshot atual enviava apenas um resumo numerico do candle atual e alguns indicadores derivados
- isso era insuficiente para leitura de Price Action, suporte/resistencia, estrutura e confluencia
- o melhor caminho definido no planejamento era ampliar primeiro o dado de entrada antes de criar o motor novo

## Arquivos impactados

- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-candles.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- backend/app/models.py
- backend/tests/test_operational_flow.py
- README.md
- mt5/ligacao-mt5-real.md

## Decisao tomada

- o EA ganhou novos inputs para quantidade de candles e timeframe de confirmacao
- o snapshot passou a enviar `candles` e `htf_candles` com OHLC e tick_volume
- o backend passou a aceitar esse contrato expandido de forma retrocompativel
- o motor atual nao foi trocado nesta etapa; ele continua operando enquanto a base do VPE e preparada

## Alternativas descartadas

- tentar construir o motor de Price Action sem OHLC historico: descartado por gerar retrabalho e fragilidade analitica
- remover ja os campos antigos baseados em EMA/RSI: descartado para manter compatibilidade durante a transicao
- mandar imagem do grafico nesta etapa: descartado porque o problema principal ainda era ausencia da estrutura numerica do preco

## Validacao executada

- validacao de erros nos arquivos MQL5 e Python alterados
- teste backend atualizado para aceitar snapshot expandido com `candles` e `htf_candles`

## Riscos e observacoes

- o EA precisa ser recompilado no MetaEditor para passar a exportar o novo snapshot
- snapshots ficam maiores, principalmente em multi-ativo com timer curto
- o motor atual ainda ignora esses candles; o ganho analitico virá na proxima etapa com os modulos de Price Action

## Proximos passos

1. criar os modulos `price_action_patterns`, `price_action_zones` e `price_action_structure` no backend
2. orquestrar o VPE no `decision_engine.py` mantendo fallback controlado para o motor simples
3. mostrar no painel o setup detectado, a zona e o score
