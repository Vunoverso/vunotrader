# 2026-03-31 - Motor compartilhado entre Brain e bot CMD

## Contexto

O projeto passou a ter dois caminhos de execução para o MetaTrader 5:

- fluxo principal com EA + socket + `vunotrader_brain.py`
- fluxo local via `scripts/mt5_cmd_bot.py`

Antes desta mudança, os dois caminhos não compartilhavam a mesma inteligência.
O brain usava RF + GB com features técnicas próprias, enquanto o bot CMD usava uma estratégia simples de EMA + RSI.

## Objetivo

Extrair o núcleo de decisão para um módulo reutilizável, permitindo que o brain e o conector local usem a mesma base de:

- engenharia de features
- predição
- ajuste de risco por convicção
- governança local por win rate

## Decisão técnica

Foi criado o pacote `vuno_core` com o módulo `decision_engine.py`.

Esse módulo concentra:

- `DecisionRuntimeConfig`
- `FeatureBuilder`
- `TradingModel`
- `DecisionEngine`
- `generate_bootstrap_market_data()`

O `vunotrader_brain.py` passou a orquestrar persistência, identidade do robô, Skill Engine, shadow global e heartbeat, mas delega a decisão base ao `DecisionEngine`.

O `scripts/mt5_cmd_bot.py` ganhou o comando `run-engine`, que usa o mesmo motor principal compartilhado em loop local no MT5.

## Arquivos impactados

- `vuno_core/__init__.py`
- `vuno_core/decision_engine.py`
- `vunotrader_brain.py`
- `scripts/mt5_cmd_bot.py`

## Uso para o usuário

O usuário continua podendo operar pelo fluxo principal com EA no gráfico.

Agora existe também um caminho alternativo local:

```bash
python scripts/mt5_cmd_bot.py run-engine --symbol EURUSD --timeframe M5 --volume 0.10 --dry-run
```

Esse comando:

- conecta ao terminal MT5 local
- lê candles do ativo
- passa os dados pelo mesmo motor principal compartilhado
- exibe sinal, confiança, risco, regime e rationale
- opcionalmente executa ordem direta no terminal MT5

## Impacto técnico

- reduz divergência entre conectores
- cria base para oferecer dois modos de conexão no produto sem duplicar lógica
- isola melhor as responsabilidades entre decisão e infraestrutura

## Riscos e observações

- o comando `run-engine` ainda não grava auditoria no backend como o fluxo EA + brain + Supabase
- o bootstrap do modelo continua baseado em dados simulados, igual ao brain atual
- o caminho compartilhado cobre o motor principal local, mas a camada de governança externa via Skill Engine continua exclusiva do brain

## Alternativas avaliadas

1. Manter o bot CMD com estratégia simples própria.
Motivo de não adotar: duplicava lógica e criava divergência entre sinais.

2. Fazer o bot CMD importar diretamente `_handle_market_data()` do brain.
Motivo de não adotar: manteria forte acoplamento com socket, Supabase e identidade do robô.

## Próximos passos

1. Persistir e carregar modelos treinados em disco para que brain e CLI compartilhem pesos reais, não apenas bootstrap.
2. Adicionar modo de auditoria opcional do `run-engine` no backend para rastrear execuções locais sem EA.
3. Expor na UI de instalação a escolha entre conector EA e conector local.

## Atualizacao 2026-03-31 - Correcao de regressoes apos revisao do bot

### Problemas encontrados em runtime

1. `run-engine` falhava com `ModuleNotFoundError: No module named 'vuno_core'` quando executado como script:
`python scripts/mt5_cmd_bot.py run-engine ...`

2. Persistencia do modelo compartilhado salvava apenas RF/GB, sem o `StandardScaler`.
Em restart, o carregamento parcial podia deixar o modelo em estado inconsistente para predicao.

3. Spam de warning do sklearn no loop (`X does not have valid feature names`) por remover nomes de colunas antes do `transform`.

### Correcao aplicada

Arquivos ajustados:
- `scripts/mt5_cmd_bot.py`
- `vuno_core/decision_engine.py`

Mudancas:
- Insercao do `PROJECT_ROOT` no `sys.path` antes de importar `vuno_core` no CLI.
- Preload de `brain.env` antes de construir o parser, para defaults coerentes no argparse.
- `save_model_weights()` e `load_model_weights()` passaram a salvar/carregar RF, GB e Scaler.
- `TradingModel.predict()` passou a manter DataFrame com nomes de colunas no `scaler.transform`, eliminando warning repetitivo.

### Resultado

- `run-engine` voltou a subir e processar sinais em loop no MT5.
- Persistencia de pesos ficou consistente para restart.
- Log do loop ficou limpo (sem warning de feature names).

## Atualizacao 2026-03-31 - Itens 1 e 2 concluídos

### Item 1 - Auditoria no backend para `run-engine`

Foi implementado um logger opcional no `scripts/mt5_cmd_bot.py` (`VunoAuditLogger`) para registrar:

- `trade_decisions` por ciclo do motor compartilhado
- `executed_trades` ao abrir ordem
- `trade_outcomes` ao detectar fechamento no histórico do MT5

Ativação por ambiente:

- `VUNO_AUDIT_ENABLED=1`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `BRAIN_USER_ID`
- `BRAIN_ORG_ID`
- opcional: `MT5_ROBOT_INSTANCE_ID`

Observação: o logger é `best effort`; se faltar configuração, o run-engine continua operando sem persistência.

### Item 2 - Pesos compartilhados entre Brain e CLI

Foi adicionada persistência no núcleo compartilhado (`vuno_core/decision_engine.py`):

- `load_model_weights()`
- `save_model_weights()`

Arquivos usados por padrão:

- `brain_model_rf.pkl`
- `brain_model_gb.pkl`

Comportamento após ajuste:

- `vunotrader_brain.py` tenta carregar pesos ao iniciar; se não houver, faz bootstrap, treina e salva.
- `RetrainScheduler` salva pesos após retreino bem-sucedido.
- `scripts/mt5_cmd_bot.py` (`run-engine`) também tenta carregar os mesmos pesos; se não houver, treina bootstrap e salva.

Resultado: brain e conector local passam a usar o mesmo estado de modelo em disco.

## Atualizacao 2026-03-31 - Fase 2 (scanner dinamico multiativos)

### Objetivo

Evoluir o `run-engine` de operacao fixa por simbolo para um modo dinamico com selecao da melhor oportunidade por ciclo.

### Implementacao

Arquivo ajustado:

- `scripts/mt5_cmd_bot.py`

Novo comando adicionado:

- `run-engine-dynamic`

Principais capacidades entregues:

- scanner multiativos com `--symbols` (lista separada por virgula)
- filtro de qualidade por spread (`--max-spread-points`)
- filtro de volatilidade por ATR percentual (`--min-atr-pct`)
- score de oportunidade por ativo (conviccao + volatilidade - custo de spread)
- selecao do melhor ativo do ciclo para execucao
- limites de risco de portfolio:
	- `--max-global-positions`
	- `--max-positions-per-symbol`
	- `--max-correlated-positions` (heuristica por moedas base/cotacao)
- fechamento de posicao oposta opcional por simbolo (`--close-opposite`)
- auditoria reaproveitada com `VunoAuditLogger` para decisao, abertura e fechamento

### Impacto

- o conector local fica mais aderente ao comportamento esperado de alocacao dinamica
- reduz dependencia de operar somente um simbolo fixo
- melhora disciplina de risco em portfolio local sem precisar do brain full time

### Riscos e observacoes

- heuristica de correlacao e simples (FX base/cotacao), adequada para versao inicial
- ativos nao-FX podem exigir regra especifica de correlacao no proximo ajuste

## Atualizacao 2026-03-31 - Status de validacao da Fase 1 nesta sessao

### O que foi preparado

- `scripts/phase1_full_cycle_smoke.py` criado para validar ciclo completo (decisao -> execucao -> outcome) com auditoria ativa.
- `scripts/phase1_audit_probe.py` criado para confirmar baseline e contagens no Supabase.

### Bloqueio operacional encontrado

Durante a execucao via terminal integrado houve falhas recorrentes do `PSReadLine` (erro de cursor no console), interrompendo comandos longos e coleta de saida em tempo real.

### Mitigacao aplicada

- comandos reduzidos e execucao via shell isolado
- captura por arquivos para nao depender de stream de saida

### Proximo passo recomendado

Executar o smoke da Fase 1 em shell limpo (PowerShell externo sem PSReadLine instavel) e validar no probe:

1. `trade_decisions` com incremento
2. `executed_trades` com incremento
3. `trade_outcomes` com incremento