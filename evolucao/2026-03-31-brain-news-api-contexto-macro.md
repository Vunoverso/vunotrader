# 2026-03-31 - Brain com contexto macro via API de noticias financeiras

## Objetivo

Integrar leitura de noticias financeiras no `vunotrader_brain.py` para modular entradas e saidas com contexto macro, sem substituir o motor tecnico principal.

## Arquivos impactados

- `vunotrader_brain.py`
- `brain.env.example`
- `brain.env` (local)

## Implementacao

### 1) Novo modulo `FinancialNewsAnalyzer`

Foi adicionada uma camada opcional com:

- chamada HTTP para API de noticias via `urllib`
- cache em memoria por `(symbol, timeframe)`
- scoring simples de sentimento por termos positivos/negativos
- classificacao de viés: `buy`, `sell`, `neutral`
- confianca calculada por intensidade media do score

### 2) Integracao no ciclo `MARKET_DATA`

No `MT5Bridge._handle_market_data`:

- apos a analise tecnica do `DecisionEngine`, o brain aplica `news_analyzer.apply_to_prediction(...)`
- o resultado de noticias pode:
  - reduzir risco em cenario neutro/oposto moderado
  - aumentar risco quando noticia alinha com sinal tecnico
  - bloquear entrada (`HOLD`) quando noticia oposta e forte
- o `rationale` ganha marcador `NEWS:*`
- `news_context` passa a ser retornado no payload de resposta

### 3) Configuracoes via ambiente

Novas variaveis:

- `ENABLE_FIN_NEWS`
- `FIN_NEWS_API_KEY`
- `FIN_NEWS_API_URL_TEMPLATE`
- `FIN_NEWS_API_URL_TEMPLATES`
- `FIN_NEWS_TIMEOUT_SEC`
- `FIN_NEWS_CACHE_SEC`
- `FIN_NEWS_LANGUAGE`
- `FIN_NEWS_MIN_ARTICLES`

### 4) Fallback de endpoint

Como provedores variam rota/parametros (`query` vs `q`), o leitor tenta multiplos templates automaticamente antes de desistir.

## Decisao tecnica

A camada de noticias foi implementada como `best effort` e desacoplada:

- se API falhar/retornar erro, o brain continua operando com motor tecnico
- nao existe dependencia bloqueante para o ciclo de decisao
- o impacto de noticias e progressivo, com bloqueio apenas em oposicao forte

## Riscos e observacoes

- Sentimento por palavras-chave e um MVP; pode gerar falso positivo em algumas manchetes.
- A API key deve ficar apenas em ambiente local/seguro.
- O endpoint da API pode mudar; o fallback de templates reduz esse risco operacional.

## Proximos passos

1. Evoluir scoring para classificador supervisionado por ativo/regime.
2. Persistir `news_context` estruturado no banco (alem do `rationale`).
3. Adicionar painel no dashboard para mostrar impacto das noticias por decisao.

## Atualizacao 2026-03-31 - Contencao de risco: noticias em shadow por padrao

### Problema identificado

A camada de noticias estava com influencia direta no sinal/risco sem evidencia estatistica previa de ganho de EV.
Isso introduzia risco de ruido, conflito de sinal e degradacao silenciosa.

### Decisao aplicada

Foi adotado o mesmo principio do shadow mode global:

- **baseline tecnico manda por padrao**
- noticias passam a rodar em **modo shadow** por default
- influencia real so ocorre em `FIN_NEWS_MODE=assist` e com threshold de confianca

### Arquivos impactados

- `vunotrader_brain.py`
- `brain.env.example`

### Implementacao tecnica

1. Novos controles de ambiente:
- `FIN_NEWS_MODE` (`off|shadow|assist`, default `shadow`)
- `FIN_NEWS_MIN_CONFIDENCE_TO_INFLUENCE`
- `FIN_NEWS_CONFLICT_RISK_REDUCTION`
- `FIN_NEWS_ALIGNMENT_RISK_BOOST`
- `FIN_NEWS_BLOCK_ON_CONFLICT`
- `FIN_NEWS_BLOCK_CONFIDENCE`

2. `FinancialNewsAnalyzer` agora separa:
- decisao baseline (tecnica)
- decisao candidata com noticias
- decisao efetiva (so muda em `assist`)

3. `_handle_market_data` passa a retornar:
- `news_context` (contexto da API)
- `news_shadow` (baseline vs candidate, `execution_changed`, `can_influence`)

4. Avaliacao offline/real:
- criado log local `news_shadow_eval.csv` com colunas de comparacao
- no `TRADE_RESULT`, o brain fecha o registro com `outcome`, `pnl_money`, `pnl_points`

### Resultado esperado

- elimina alteracao silenciosa de execucao por noticias em ambiente padrao
- viabiliza comparar `EV baseline` vs `EV news candidate` com dados reais antes de ativar `assist`
- reduz risco de sobreajuste contextual por heuristica
