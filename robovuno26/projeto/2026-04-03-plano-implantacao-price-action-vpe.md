Data: 2026-04-03

# Plano de implantacao do motor de Price Action VPE

## Objetivo

Registrar, sem perda de contexto, o comparativo entre o motor atual do robo e o motor desejado com base nos PDFs de Price Action, alem de definir uma rota tecnica clara para implantacao no robo.

## Fontes usadas

- projeto/price_action_completo_vpe (1).pdf
- projeto/Ebook-Price-Action.pdf
- projeto/CURSO_PRICE_ACTION.pdf
- projeto/VPE_Especificacao_Completa_v2 (2).docx
- backend/app/decision_engine.py
- backend/app/models.py
- mt5/vuno-bridge/vuno-bridge-io.mqh

## Resumo executivo

O motor atual do robo ainda nao faz Price Action de verdade. Hoje ele decide por heuristica curta de tendencia e filtro de RSI, usando apenas alguns numeros soltos do snapshot.

Os PDFs apontam outra direcao:

- leitura do preco puro
- interpretacao de candle
- padroes de entrada
- zonas de suporte e resistencia
- market structure
- confluencia entre padrao, local e contexto
- auditoria clara do motivo da entrada

Conclusao pratica: antes de pensar em imagem de grafico, o robo precisa primeiro receber e interpretar sequencias de candles OHLC. Essa e a base correta para a VPE.

Revisao com a especificacao v2: o plano continua correto na ordem das fases, mas precisa endurecer quatro pontos antes de seguir para uma versao mais seria de DEMO e REAL.

- timeframe operacional e timeframe de confirmacao precisam ser tratados como configuracao explicita da estrategia
- o contrato de candles precisa usar apenas candles fechados
- pausa de noticias de alto impacto precisa ser obrigatoria para XAUUSD antes de go-live
- a ida para DEMO precisa ter portao minimo de performance em backtest

## O que os PDFs pedem para o motor

### 1. Price Action como leitura primaria

O motor deve ler:

- open
- high
- low
- close
- corpo do candle
- pavio superior
- pavio inferior
- relacao entre candles sequenciais

Indicador derivado pode continuar existindo como filtro auxiliar, mas nao como nucleo da decisao.

### 2. Padroes principais de entrada

Os materiais convergem para um nucleo inicial claro:

- Pin Bar
- Engolfo
- Inside Bar

O PDF VPE tambem explicita que padrao sozinho nao basta. A entrada precisa responder as tres perguntas:

- O QUE: qual padrao apareceu
- ONDE: em qual zona ele apareceu
- QUANDO: qual confirmacao temporal e de fechamento existe

### 3. Zonas de suporte e resistencia

O motor deve deixar de pensar em um preco unico e passar a pensar em zona.

Isso inclui:

- suporte recente
- resistencia recente
- borda inferior de range
- borda superior de range
- zona de reacao por repeticao de toques

### 4. Market Structure

Os PDFs e o documento VPE puxam para:

- topos e fundos
- continuidade de tendencia
- perda de estrutura
- lateralizacao
- rompimento e reteste

### 5. Confluencia e score

O motor precisa sair de uma resposta binaria simples e construir um score de assertividade.

Esse score deve combinar:

- qualidade do padrao
- qualidade da zona
- alinhamento da estrutura
- confirmacao do fechamento
- filtros operacionais

### 6. Auditoria real da decisao

O usuario precisa entender:

- qual padrao foi detectado
- em qual zona ele apareceu
- qual era a estrutura no momento
- por que virou BUY, SELL ou HOLD
- qual foi a invalidacao da leitura

## Estado atual do robo

### Snapshot atual recebido pelo backend

Hoje o snapshot carrega apenas:

- symbol
- timeframe
- bid
- ask
- spread_points
- close
- ema_fast
- ema_slow
- rsi
- balance
- equity
- open_positions
- captured_at
- local_memory

Isso e insuficiente para Price Action serio.

### Logica atual do motor

Hoje o motor decide por:

- HOLD se spread estiver alto
- BUY se ema_fast > ema_slow e RSI estiver abaixo do limite
- SELL se ema_fast < ema_slow e RSI estiver acima do limite
- ajuste defensivo pequeno por memoria recente

### O que nao existe hoje

- historico de candles
- leitura de candle body/wick
- Pin Bar
- Engolfo
- Inside Bar
- swing highs e swing lows
- suporte e resistencia por zona
- range detection
- breakout + retest
- market structure
- score por confluencia
- explicacao estruturada de setup
- auditoria visual de setup

## Comparativo: motor atual x motor VPE desejado

| Tema | Motor atual | Motor desejado |
| --- | --- | --- |
| Entrada principal | EMA + RSI | Price Action puro com confluencia |
| Dados de entrada | 1 candle resumido + indicadores | serie de candles OHLC |
| Leitura de padrao | inexistente | Pin Bar, Engolfo, Inside Bar |
| Leitura de zona | inexistente | suporte, resistencia, bordas de range |
| Estrutura | inexistente | topos, fundos, tendencia, lateralizacao |
| Auditoria | rationale simples | setup, zona, estrutura, gatilho, invalidacao |
| HOLD inteligente | muito limitado | HOLD no meio do range, sem confluencia ou sem confirmacao |
| Explicabilidade | baixa | alta |

## Direcao tecnica recomendada

## Fase 1 - Trocar o snapshot para OHLC real

O primeiro passo correto nao e imagem. E ampliar o snapshot vindo do MT5.

### Novo contrato minimo de snapshot

Adicionar ao backend uma estrutura como:

```json
{
  "symbol": "XAUUSD",
  "timeframe": "M5",
  "captured_at": "...",
  "spread_points": 18.0,
  "open_positions": 0,
  "candles": [
    {"time": "...", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
  ],
  "htf_candles": [
    {"time": "...", "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
  ]
}
```

### Recomendacao de quantidade

- 80 candles do timeframe operacional
- 30 candles do timeframe de confirmacao

Exemplo:

- M5 como operacional
- H1 como confirmacao

### Ajustes obrigatorios apos a revisao v2

#### 1. Timeframes como configuracao da estrategia

- o timeframe operacional nao deve ser inferido dentro da logica do score
- o timeframe operacional deve vir do grafico da instancia e ser tratado como parte da configuracao do setup
- o timeframe de confirmacao deve vir de configuracao explicita e ficar rastreavel na estrategia usada
- no estado atual, isso ja existe parcialmente via timeframe do grafico + `InpHigherTimeframe`, mas ainda falta espelhar essa definicao de forma mais clara no runtime e no painel

#### 2. Contrato de candles fechados

- o snapshot deve carregar apenas candles fechados
- os arrays devem seguir em ordem cronologica, do mais antigo para o mais recente
- o ultimo item do array deve ser o candle fechado mais recente
- `close`, `ema_fast`, `ema_slow` e `rsi` tambem precisam refletir o candle fechado mais recente

Observacao tecnica: a sugestao de usar `candles[0]` como candle mais recente nao foi adotada neste plano porque o backend ja opera melhor com serie cronologica. O ponto obrigatorio nao e inverter o array; e impedir que candle aberto contamine a leitura.

## Fase 2 - Criar o nucleo VPE no backend

Criar modulos novos em vez de entupir decision_engine.py.

### Estrutura sugerida

- backend/app/price_action.py
- backend/app/price_action_patterns.py
- backend/app/price_action_zones.py
- backend/app/price_action_structure.py
- backend/app/price_action_score.py

### Papel de cada modulo

price_action_patterns.py:

- detectar Pin Bar
- detectar Engolfo
- detectar Inside Bar
- classificar forca do padrao

price_action_zones.py:

- detectar suporte
- detectar resistencia
- agrupar toques em zona
- detectar range lateral

price_action_structure.py:

- detectar swing highs
- detectar swing lows
- classificar bullish, bearish ou lateral
- detectar breakout e retest

price_action_score.py:

- somar score do padrao
- somar score da zona
- somar score da estrutura
- aplicar penalidades por spread, falta de confirmacao e meio do range

price_action.py:

- orquestrar tudo
- devolver BUY, SELL ou HOLD
- montar rationale estruturado

## Fase 3 - Regras minimas da V1

## BUY somente quando

- houver padrao bullish valido
- o padrao aparecer em suporte ou borda inferior de range
- a estrutura nao estiver bearish forte
- houver fechamento de confirmacao
- spread e filtros operacionais estiverem aceitaveis
- score final ficar acima do minimo de entrada

## SELL somente quando

- houver padrao bearish valido
- o padrao aparecer em resistencia ou borda superior de range
- a estrutura nao estiver bullish forte
- houver fechamento de confirmacao
- spread e filtros operacionais estiverem aceitaveis
- score final ficar acima do minimo de entrada

## HOLD quando

- o preco estiver no meio do range
- nao houver padrao confiavel
- o padrao existir mas fora da zona certa
- a estrutura estiver confusa
- o spread estiver alto
- houver conflito entre timeframe operacional e confirmacao

## Regras propostas por setup na V1

### Pin Bar

Base do PDF VPE:

- shadow dominante >= 2.5 x body
- alta conviccao ideal >= 3.5 x body

Regra de implantacao:

- Pin Bar bullish exige pavio inferior dominante
- Pin Bar bearish exige pavio superior dominante
- precisa nascer em zona valida
- candle seguinte ou fechamento do proprio candle precisa confirmar rejeicao

### Engolfo

Regra proposta para implantacao:

- corpo do candle atual precisa engolfar o corpo do candle anterior
- o fechamento precisa favorecer a direcao do engolfo
- o padrao precisa estar em zona ou reteste relevante

### Inside Bar

Regra proposta para implantacao:

- candle atual fica dentro da maxima e minima da mother bar
- nao entrar no mero aparecimento
- usar somente com breakout confirmado da mother bar e contexto favoravel

## Fase 4 - Zonas de suporte e resistencia

### Regras propostas para a V1

- construir swing highs e swing lows com fractal simples
- agrupar niveis proximos em zona, nao em linha unica
- tolerancia inicial da zona pode usar fracao do range recente ou ATR
- marcar lateralizacao quando as ultimas oscilacoes estiverem comprimidas e sem estrutura clara de continuidade

### O que entra agora

- suporte e resistencia horizontais
- borda superior e inferior de range
- reteste simples apos rompimento

### O que fica para depois

- order blocks completos
- FVG
- CHoCH e BOS mais sofisticados
- SMC completo

## Fase 5 - Saida e gerenciamento

Os PDFs reforcam que o motor precisa pensar entrada e saida.

Para a V1, a saida pode continuar simples, mas melhor que a atual:

- stop abaixo da rejeicao ou do ultimo fundo para BUY
- stop acima da rejeicao ou do ultimo topo para SELL
- take na proxima zona relevante
- opcionalmente usar RR minimo

Filtros adicionais recomendados:

- restricao de horario
- bloqueio em spread alto
- cooldown de reentrada por ativo
- pausa diaria apos sequencia ruim ou perda acumulada

## Filtro de noticias antes do go-live

- para XAUUSD, a pausa de noticias deixa de ser opcional e passa a ser requisito tecnico antes de DEMO validatorio e REAL
- a V1 deve considerar uma janela de bloqueio ao redor de noticias de alto impacto
- a integracao pode comecar simples, consumindo calendario economico externo e refletindo o bloqueio em `pause_new_orders`
- sem esse filtro, qualquer leitura boa de Price Action pode ser invalidada por NFP, FOMC e eventos equivalentes

## Fase 6 - Auditoria e painel

O painel precisa mostrar mais que Compra ou Venda.

### O que deve aparecer no dashboard

- setup detectado
- ativo e timeframe
- zona atual
- estado da estrutura
- score final
- motivo do HOLD quando nao entrar

### O que deve ser salvo em decision_payload

- setup_name
- setup_direction
- setup_score
- zone_type
- zone_low
- zone_high
- structure_state
- trigger_type
- invalidation_reason
- checklist_passed

## O que NAO fazer primeiro

- nao comecar por imagem do grafico
- nao tentar LLM visual antes de OHLC estruturado
- nao colocar order blocks e SMC completos na primeira iteracao
- nao apagar o contrato atual sem fase de transicao

## Estrategia de implantacao segura

### Etapa 1

Expandir o snapshot do MT5 para OHLC historico.

### Etapa 2

Criar o motor VPE em paralelo ao motor atual.

### Etapa 3

Permitir chave de runtime para escolher entre:

- motor simples atual
- motor price action V1

### Etapa 4

Rodar primeiro em DEMO com auditoria detalhada.

### Etapa 5

So depois liberar para REAL.

## Arquivos que serao impactados na implantacao

- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-io.mqh
- backend/app/models.py
- backend/app/decision_engine.py
- backend/app/routes/agent.py
- backend/app/routes/monitoring.py
- backend/static/js/app.js
- backend/static/index.html

## Definicao de pronto da V1

- robo recebe serie de candles e nao apenas um resumo com indicadores
- motor detecta ao menos Pin Bar, Engolfo e Inside Bar
- motor detecta suporte, resistencia e range lateral simples
- BUY e SELL exigem confluencia minima
- HOLD explica claramente por que nao entrou
- dashboard mostra setup, zona e estrutura
- existe filtro de noticias de alto impacto antes do go-live em XAUUSD
- existe portao minimo de performance com profit factor >= 1.3 em pelo menos 100 trades simulados antes de avancar para DEMO
- tudo roda primeiro em DEMO com auditoria suficiente

## Proxima ordem de implementacao recomendada

1. expandir SnapshotRequest para OHLC historico
2. exportar candles do MT5
3. criar modulo price_action_patterns.py
4. criar modulo price_action_zones.py
5. criar modulo price_action_structure.py
6. trocar decision_engine.py para orquestrar o VPE
7. mostrar setup e score no painel
