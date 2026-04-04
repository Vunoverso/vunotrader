Data: 2026-04-03

# Descoberta automática de símbolos MT5 e setup por instância

## Objetivo

Fechar a próxima etapa do onboarding MT5 para que cada instância passe a exibir no painel, de forma automática, o ativo principal, o timeframe do gráfico e o catálogo de símbolos detectados direto no terminal.

## Situação encontrada

- o painel ainda tratava `selected_symbols` como uma lista manual estática
- não existia persistência para `primary_symbol`, `chart_timeframe` nem catálogo detectado do MT5
- o EA não exportava metadados da corretora/terminal para a bridge
- o agente local só processava snapshots, feedbacks e runtime settings
- a documentação anterior ainda registrava a descoberta automática como etapa futura

## Arquivos impactados

- backend/app/instrument_catalog.py
- backend/app/models.py
- backend/app/routes/robot_instances.py
- backend/app/routes/monitoring.py
- backend/app/routes/agent.py
- backend/app/agent_package.py
- backend/app/migrations.py
- backend/migrations/sqlite/0006_robot_instances_mt5_metadata_and_setup.sql
- backend/migrations/postgres/0006_robot_instances_mt5_metadata_and_setup.sql
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_operational_flow.py
- agent-local/app/config.py
- agent-local/app/bridge.py
- agent-local/app/api_client.py
- agent-local/app/main.py
- agent-local/config.example.json
- agent-local/configure-mt5-bridge.ps1
- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-paths.mqh
- mt5/vuno-bridge/vuno-bridge-symbols.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- mt5/ligacao-mt5-real.md
- README.md

## Decisão tomada

- a instância agora persiste `primary_symbol`, `chart_timeframe`, `discovered_symbols` e `symbols_detected_at`
- o EA exporta um arquivo de catálogo em `metadata/` com bridge, símbolo do gráfico, timeframe, símbolos disponíveis, Market Watch e ativos monitorados
- o agente local reencaminha esse catálogo ao backend usando um endpoint dedicado (`/api/agent/symbol-catalog`)
- o backend atualiza a instância com o setup real detectado no MT5 e registra auditoria apenas quando houver mudança relevante
- o painel ganhou campos explícitos de ativo principal e timeframe, além de modo de edição do setup da instância
- o pacote baixado pelo usuário agora já leva `primary_symbol`, `chart_timeframe` e `metadata_dir` no `runtime/config.json`
- a normalização de símbolos foi ajustada para preservar o nome exato informado/detectado, sem forçar uppercase e sem remover espaços internos

## Alternativas descartadas

- continuar apenas com perfil estático de mercado: descartado porque não resolve a diferença real entre símbolos por corretora/terminal
- sobrescrever o setup manual no painel sem endpoint de edição: descartado porque impediria ajuste fino após a primeira conexão
- enviar o catálogo a cada ciclo sem controle: descartado porque geraria ruído desnecessário na bridge e no backend

## Validação executada

- análise estática sem erros nos arquivos Python, JS, PowerShell e MQL alterados
- teste operacional executado com sucesso:
  - `Set-Location 'e:\vunorobo26\backend'; .\.venv\Scripts\python.exe -m pytest tests/test_operational_flow.py -q`
- o teste passou cobrindo:
  - criação da instância com ativo principal e timeframe
  - download do pacote com os novos campos
  - heartbeat do agente
  - ingestão do catálogo MT5
  - atualização do setup da instância
  - decisão, feedback e resumo operacional

## Riscos e observações

- o painel agora consegue refletir o setup real do MT5, mas isso depende do EA/anexo do gráfico já estar ativo e escrevendo em `metadata/`
- a descoberta automática não substitui a necessidade de o usuário anexar o EA no gráfico correto; ela apenas reduz ambiguidade e confirma o estado real
- ainda não existe compilação automatizada do `.mq5` no CI; a validação do MQL continua dependente do ambiente/editor local

## Próximos passos

1. replicar o mesmo contrato de metadata nos artefatos espelhados em `projeto/vuno-robo/`, se esse espelho continuar sendo distribuído manualmente
2. considerar diferenciação entre símbolos disponíveis no broker e símbolos visíveis no Market Watch no painel, caso isso vire dor operacional
3. avaliar se o runtime operacional deve ganhar override por instância ou se o `chart_timeframe` deve permanecer apenas como setup do gráfico
