Data: 2026-04-03

# Onboarding do agente sem terminal manual

## Objetivo

Remover do fluxo principal do painel a dependencia de prompt, navegacao manual por pasta e colagem de comandos para iniciar o robo.

## Situacao encontrada

- o painel orientava o usuario a baixar apenas `config.json`
- o passo seguinte exigia copiar comandos de PowerShell
- a area de instancias deixava o token bruto como foco principal da UX
- o tutorial instruia copiar so `mt5/VunoRemoteBridge.mq5`, embora o EA modular tambem dependa da pasta `mt5/vuno-bridge`

## Arquivos impactados

- backend/app/agent_package.py
- backend/app/routes/robot_instances.py
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_operational_flow.py
- agent-local/install.ps1
- agent-local/run-agent.ps1
- agent-local/iniciar-vuno-robo.ps1
- agent-local/iniciar-vuno-robo.cmd
- README.md

## Decisao tomada

- o backend agora gera um zip por instancia autenticada em `GET /api/robot-instances/{id}/agent-package`
- o pacote inclui `runtime/config.json` ja preenchido com a chave do robo e a URL do backend
- o pacote inclui `agent-local/iniciar-vuno-robo.cmd`, que prepara ambiente, configura a bridge e inicia o agente por duplo clique
- o painel passou a destacar `Baixar robo pronto` como acao principal
- o tutorial deixou de orientar copia de comando e passou a orientar extrair o zip e abrir o atalho
- a instrucao de MT5 foi corrigida para incluir tambem a pasta `mt5/vuno-bridge`

## Alternativas descartadas

- empacotar agora um instalador `.exe` completo: descartado nesta iteracao por aumentar custo e tempo de entrega sem necessidade para validar o fluxo SaaS
- manter download apenas de `config.json` e esconder o comando em outro lugar: descartado porque ainda preservaria a dependencia mental de terminal

## Validacao executada

- teste automatizado do backend cobrindo download do pacote, estrutura do zip e `runtime/config.json` preconfigurado

## Riscos e observacoes

- o endpoint de pacote depende de o deploy do backend conter tambem as pastas irmas `agent-local/` e `mt5/`
- se `agent-local/dist/vuno-agent.exe` nao existir no servidor, o pacote continua operando em modo fallback com preparacao automatica de Python
- em deploy Linux ou Railway, o backend nao deve construir o `.exe` em tempo real; o binario precisa vir de uma etapa anterior de build Windows

## Proximos passos

1. adicionar pipeline dedicada para gerar e publicar `agent-local/dist/vuno-agent.exe` antes do deploy do backend
2. transformar o tutorial em wizard guiado com validacao de cada etapa

## Atualizacao complementar

- a lista de instancias agora exibe `Baixar robo pronto` em cada linha da tabela
- `agent-local/iniciar-vuno-robo.ps1` passou a preferir `dist/vuno-agent.exe` quando o binario estiver presente
- o gerador do pacote anexa `agent-local/dist/vuno-agent.exe` automaticamente quando esse build existir no servidor
- o backend passou a expor `package_delivery_mode` na listagem de instancias com fonte unica em `backend/app/agent_package.py`
- o heartbeat agora envia `agent_runtime` e o painel mostra esse resumo sem criar tabela nova
- `.gitignore` foi ajustado para evitar versionamento acidental de artefatos de PyInstaller

## Correcao operacional de offline

- causa 1 confirmada: a instancia `vun bot2` estava com token correto em `agent-local/runtime/config.json`, mas sem heartbeat no backend
- causa 2 confirmada: o backend estava ativo e o MT5 estava gerando snapshots em `Common\Files\VunoBridge\in`, entao o gargalo estava no agente local
- causa 3 confirmada: o executavel do agente falhava por imports quebrados no empacotamento do PyInstaller
- causa 4 confirmada: o agente travava ao arquivar snapshots entre unidades diferentes (`C:` -> `E:`) usando `Path.replace`

## Ajustes aplicados

- `agent-local/app/main.py` e `agent-local/app/runtime_contract.py`: imports ajustados para execucao por pacote e por script
- `agent-local/start_agent.py`: nova entrada unica para o executavel
- `agent-local/build-agent.ps1`: build alinhado para usar `start_agent.py`
- `agent-local/run-agent.ps1`: execucao Python alinhada para `python -m app.main`
- `agent-local/app/bridge.py`: arquivamento trocado para `shutil.move`, suportando mover entre unidades no Windows
- `backend/app/main.py`: rota `GET /favicon.ico` retornando `204` para eliminar ruido de console do navegador

## Validacao operacional

- `GET /favicon.ico` passou a responder `204`
- a instancia `vun bot2` voltou a gravar `last_status=ACTIVE`
- `last_heartbeat_payload` voltou a registrar `agent_runtime`, `pending_snapshots` e `pending_feedback`
- snapshots passaram a ser consumidos e comandos `SELL` passaram a ser escritos na pasta `VunoBridge\out`

## Observacao residual

- ainda existem leituras ocasionais de snapshot em arquivo em uso pelo MT5 (`WinError 32`), mas o agente continuou operando e enviando heartbeat; isso pode ser endurecido depois com retry curto em leitura/arquivo bloqueado