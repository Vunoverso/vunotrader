Data: 2026-04-03

# Instância por conta com bridge única e seleção inicial de ativos

## Objetivo

Corrigir a modelagem operacional da instância MT5 para evitar colisão entre robôs na mesma máquina e permitir que o usuário defina, já no painel, quais ativos aquela instância vai acompanhar.

## Situação encontrada

- a instância ainda guardava apenas nome e modo
- o pacote e os scripts assumiam `VunoBridge` fixo para todo mundo
- isso aumentava risco de colisão entre duas instâncias na mesma máquina
- o painel ainda não registrava perfil de mercado nem lista inicial de ativos
- o módulo `vuno-bridge-candles.mqh` falhava para compilar por usar `LongToString`

## Arquivos impactados

- backend/app/instrument_catalog.py
- backend/app/models.py
- backend/app/routes/robot_instances.py
- backend/app/routes/monitoring.py
- backend/app/agent_package.py
- backend/migrations/sqlite/0005_robot_instances_bridge_and_symbols.sql
- backend/migrations/postgres/0005_robot_instances_bridge_and_symbols.sql
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_operational_flow.py
- agent-local/config.example.json
- agent-local/configure-mt5-bridge.ps1
- agent-local/iniciar-vuno-robo.ps1
- mt5/vuno-bridge/vuno-bridge-candles.mqh
- mt5/ligacao-mt5-real.md
- projeto/vuno-robo/agent-local/config.example.json
- projeto/vuno-robo/agent-local/configure-mt5-bridge.ps1
- projeto/vuno-robo/agent-local/iniciar-vuno-robo.ps1
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-candles.mqh
- projeto/vuno-robo/mt5/ligacao-mt5-real.md

## Decisão tomada

- a unidade correta passa a ser uma instância por conta ou terminal MT5, e não uma instância por ativo
- o arquivo do EA continua único; o isolamento operacional entre instâncias passa por token e `bridge_name` próprios
- cada instância agora persiste `broker_profile`, `selected_symbols` e `bridge_name`
- o painel ganhou seleção inicial de perfil de mercado e ativos da instância
- o pacote gerado passa a carregar `bridge_name`, perfil e ativos no `runtime/config.json` e no `LEIA-PRIMEIRO.txt`
- os scripts do agente passaram a preferir automaticamente o `bridge_name` salvo no config da instância
- a conversão de `tick_volume` no EA foi ajustada para `StringFormat`, removendo o erro de compilação MQL

## Alternativas descartadas

- renomear o arquivo do EA por instância: descartado porque o problema real era colisão de bridge e não o nome do `.mq5`
- criar uma instância por ativo: descartado porque multiplicaria tokens, heartbeats e onboarding sem necessidade; o EA já suporta múltiplos ativos no mesmo gráfico
- tentar descobrir automaticamente todos os símbolos da corretora nesta etapa: descartado por exigir leitura direta do catálogo do MT5 pelo agente e ampliar demais o escopo desta entrega

## Validação executada

- análise estática sem erros nos arquivos Python, JS e PowerShell alterados
- validação do módulo MQL corrigido sem erros no workspace
- validação manual do endpoint novo `/api/instrument-profiles`
- validação manual da regra de bloqueio por `performance_gate` ao criar instância

## Riscos e observações

- a seleção atual de ativos é um cadastro inicial guiado por perfil; o nome final ainda precisa ser o símbolo exato do broker no MT5
- para futuros B3, o usuário ainda precisa ajustar vencimento e convenção do broker, como `WINJ26` e `WDOJ26`
- o teste automatizado completo continua bloqueado por um problema preexistente em `backend/app/parameter_store.py`, onde o `INSERT` de `user_parameters` usa quantidade de valores menor que a de colunas

## Próximos passos

1. corrigir o `upsert` de `user_parameters` para destravar a suíte automatizada completa
2. evoluir do perfil estático para descoberta real de símbolos disponíveis via agente/MT5
3. exibir no painel qual ativo foi escolhido como gráfico principal e quais ficaram em `InpAdditionalSymbols`