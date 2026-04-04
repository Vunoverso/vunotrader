## Data
- 2026-04-03

## Objetivo
- Revisar o plano do VPE com base no documento VPE_Especificacao_Completa_v2 (2).docx, corrigindo a divergencia mais critica do contrato atual e registrando os gates obrigatorios antes de uma validacao mais seria.

## Arquivos impactados
- mt5/vuno-bridge/vuno-bridge-candles.mqh
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-candles.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-market.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh
- mt5/ligacao-mt5-real.md
- README.md
- projeto/2026-04-03-plano-implantacao-price-action-vpe.md

## Decisao tomada
- A revisao confirmou que o plano geral estava correto, mas o contrato de snapshot ainda tinha um problema relevante: usava candle em formacao para `candles`, `close`, `ema_fast`, `ema_slow` e `rsi`.
- Esse ponto foi corrigido na origem do MT5 para trabalhar apenas com candles fechados.
- A copia espelhada em `projeto/vuno-robo` tambem foi alinhada para nao deixar duas versoes contraditorias do mesmo contrato dentro do workspace.
- Os quatro ajustes considerados obrigatorios a partir da revisao foram:
  - timeframes como configuracao explicita da estrategia
  - contrato de candles fechados
  - pausa de noticias de alto impacto antes de go-live em XAUUSD
  - gate minimo de performance antes de avancar para DEMO

## Alternativas descartadas
- inverter o array para `candles[0]` = candle mais recente: descartado por agora, porque o backend ja foi estruturado para serie cronologica e a inversao nao traz ganho real se o contrato deixar claro que o ultimo item e o candle fechado mais recente
- adiar a correcao de candle fechado para uma etapa futura: descartado, porque isso contaminaria patterns, zones e structure com dado instavel
- implementar integracao de calendario economico nesta mesma mudanca: descartado neste momento para manter escopo controlado; o requisito ficou documentado como gate obrigatorio de go-live

## Riscos e observacoes
- o backend agora passa a receber dado mais estavel, mas o EA precisa ser recompilado no MetaEditor para aplicar a mudanca
- pausa de noticias e gate de performance ainda nao estao implementados em codigo; por enquanto ficaram formalizados como requisito tecnico do plano
- timeframes ainda estao parcialmente configurados no MT5, mas ainda nao centralizados como configuracao versionada no painel/runtime

## Proximos passos
- recompilar o EA e validar snapshots reais com o contrato fechado
- expor timeframes operacionais da estrategia de forma mais explicita no runtime e no painel
- implementar filtro de noticias para XAUUSD antes de validar VPE em serio
- criar um portao de performance com metricas minimas para habilitar DEMO/REAL