# Evolução - Parâmetros, Monitoramento e Ligação MT5 Real

Data: 2026-04-02

## Objetivo

Fechar três frentes do núcleo operacional:

- user_parameters no backend
- consultas de auditoria e status das instâncias
- contrato operacional sincronizado do backend para o EA via agente local

## Arquivos impactados

- README.md
- backend/app/database.py
- backend/app/models.py
- backend/app/parameter_store.py
- backend/app/routes/agent.py
- backend/app/routes/parameters.py
- backend/app/routes/monitoring.py
- backend/app/main.py
- agent-local/app/config.py
- agent-local/app/api_client.py
- agent-local/app/bridge.py
- agent-local/app/main.py
- agent-local/app/runtime_contract.py
- agent-local/config.example.json
- agent-local/runtime/config.json
- agent-local/configure-mt5-bridge.ps1
- mt5/VunoRemoteBridge.mq5
- mt5/vuno-bridge/vuno-bridge-runtime.mqh
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/vuno-bridge/vuno-bridge-execution.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- mt5/ligacao-mt5-real.md

## Decisão

Foi introduzido um contrato operacional explícito entre backend, agente local e EA.

Fluxo definido:

1. tenant configura user_parameters
2. robot instance consulta runtime-config por token
3. agente local grava runtime.settings.json na bridge
4. EA lê runtime.settings.json e aplica as regras locais de execução

Também foram expostos endpoints de leitura para:

- status das instâncias
- trilha de auditoria

## Alternativas descartadas

- manter parâmetros apenas como inputs fixos do EA: descartado por baixa governança operacional
- deixar stop/take apenas no motor heurístico: descartado por conflito com os parâmetros do tenant
- conectar o MT5 diretamente ao backend: descartado por manter a ponte local como camada de resiliência

## Validação executada

- compilação de sintaxe Python concluída com sucesso
- endpoints /api/parameters, /api/robot-instances, /api/audit-events e /api/agent/runtime-config validados por chamada real
- agente local sincronizou runtime.settings.json com sucesso
- comando gerado para EURUSD passou a respeitar stop_loss_points = 140 e take_profit_points = 280 vindos dos parâmetros do tenant
- script configure-mt5-bridge.ps1 foi validado contra diretório temporário e criou corretamente as pastas in, out e feedback

## Riscos e observações

- a compilação do EA no MetaEditor ainda depende de validação na máquina com MT5 instalado
- a tela web ainda não expõe esses endpoints como produto final; por enquanto o núcleo está pronto na API e no agente

## Próximos passos

1. expor parâmetros, auditoria e status em dashboard autenticado
2. adicionar atualização controlada do modo da instância DEMO ou REAL
3. validar a ponte com uma instalação real do MT5 na máquina operacional