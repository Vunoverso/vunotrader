# Evolução - MVP Agente Remoto MT5 SaaS

Data: 2026-04-02

## Objetivo da mudança

Inicializar o projeto com uma arquitetura mínima para operação remota por snapshot, execução local no MT5 e autenticação SaaS.

## Situação encontrada

- workspace vazia
- sem pasta projeto prévia
- sem pasta evolucao prévia
- sem código base importado do robô existente

## Divergência registrada

O fluxo do projeto exige leitura prévia de evolucao e projeto antes de codar. Como ambas não existiam, foi necessário criar a base documental antes da implementação.

## Arquivos impactados

- README.md
- projeto/2026-04-02-arquitetura-mvp.md
- backend/*
- agent-local/*
- mt5/VunoRemoteBridge.mq5

## Decisões tomadas

- backend em FastAPI por velocidade de entrega
- autenticação simples com SQLite local para MVP
- comunicação MT5 <-> agente local por arquivos comuns
- decisão remota por snapshot JSON
- memória inicial baseada em persistência local e central

## Riscos e observações

- o motor de decisão ainda é heurístico
- não existe empacotamento instalável final nesta etapa
- sem a base atual do usuário, a integração com o robô existente ficou desacoplada e genérica

## Validação executada

- compilação de sintaxe Python concluída com sucesso em backend/app e agent-local/app
- backend subiu localmente e respondeu em /api/health
- fluxo de cadastro, login e criação de dispositivo validado por chamada real HTTP
- endpoint remoto de decisão respondeu BUY para snapshot de teste
- agente local processou snapshot de teste e gerou o arquivo de comando do MT5
- artefatos temporários de teste foram removidos após a validação

## Revisão de direção do produto

Após leitura do arquivo de ideias do projeto, o direcionamento oficial foi ajustado para um MVP mais enxuto.

Pontos incorporados como referência principal:

- foco em controle operacional e auditoria
- multi-tenant desde o início
- demo-first como política padrão
- núcleo do MVP restrito a auth, tenant, heartbeat, decisão, parâmetros, operações e auditoria

Divergências da base atual em relação à nova direção:

- persistência atual ainda local e sem tenant_id
- web atual ainda simplificada e sem aplicação autenticada completa
- heartbeat ainda não implementado no backend
- módulos de auditoria e parâmetros ainda não formalizados

Arquivos de planejamento atualizados:

- projeto/2026-04-02-arquitetura-mvp.md
- projeto/2026-04-02-plano-execucao-mvp.md

## Próximos passos

1. introduzir tenant e robot_instances no backend
2. implementar heartbeat do robô
3. formalizar auditoria e parâmetros no backend
4. decidir se a web segue como bootstrap local ou migra já para app dedicado
5. compilar e validar o EA no MetaEditor