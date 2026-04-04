# Corte Técnico da Base Atual

Data: 2026-04-02

## Objetivo

Separar a base ja criada em tres grupos para o MVP enxuto:

- reaproveitar
- reaproveitar com refatoração
- descartar como direção final do produto

## Critério de decisão

O corte foi feito contra a arquitetura oficial do projeto:

- multi-tenant desde o início
- foco em controle operacional
- auditoria obrigatória
- heartbeat do robô
- parâmetros de risco
- integração MT5 simples e resiliente

## Reaproveitar

### 1. Ponte local entre agente e MT5

Arquivos:

- agent-local/app/bridge.py
- agent-local/app/api_client.py

Motivo:

- resolve bem a troca assíncrona por arquivos
- desacopla MT5 da internet direta
- reduz fragilidade operacional

Decisão:

Manter como base do runtime local.

### 2. Executor local e blindagem de ordem no MT5

Arquivo:

- mt5/VunoRemoteBridge.mq5

Motivo:

- já contém spread filter
- já contém clamp de risco
- já contém retry de execução
- já contém limite por símbolo
- já contém fallback local

Decisão:

Manter a lógica de proteção de execução como núcleo do executor.

### 3. Contrato básico de decisão remota

Arquivos:

- backend/app/decision_engine.py
- backend/app/models.py

Motivo:

- já existe um contrato simples de BUY, SELL ou HOLD
- já existe risco e confiança retornados de forma previsível

Decisão:

Manter como esqueleto do brain remoto, com ajuste de nomenclatura e auditoria.

### 4. Instalação local do agente

Arquivos:

- agent-local/install.ps1
- agent-local/run-agent.ps1
- agent-local/config.example.json

Motivo:

- já entrega um fluxo local simples de instalação
- combina com o objetivo de programa local com login SaaS

Decisão:

Manter como bootstrap operacional.

## Reaproveitar com refatoração

### 1. Backend HTTP atual

Arquivo:

- backend/app/main.py

Problema:

- concentra autenticação, dispositivo, decisão e feedback em um arquivo só
- passa da regra de 200 linhas
- ainda não possui tenant, heartbeat, auditoria formal ou parâmetros

Decisão:

Refatorar em rotas e serviços separados:

- auth
- tenants/profiles
- robot-instances
- decisions/results
- heartbeat
- audit
- parameters

### 2. Persistência atual

Arquivo:

- backend/app/database.py

Problema:

- usa SQLite local como solução principal
- modelo ainda centrado em users, sessions, devices, snapshots e trade_feedback
- não atende o alvo de tenant_id em todas as entidades sensíveis

Decisão:

Usar apenas como bootstrap e migrar o desenho para:

- tenants
- profiles
- robot_instances
- user_parameters
- trade_decisions
- trade_results
- ai_usage_logs
- audit_events

### 3. Modelos Pydantic

Arquivo:

- backend/app/models.py

Problema:

- ainda falta refletir tenant, heartbeat, parâmetros e auditoria
- o contrato atual usa reason, mas o plano oficial pede rationale como campo central de explicação

Decisão:

Refatorar os schemas para refletir o contrato oficial do MVP enxuto.

### 4. Loop do agente local

Arquivo:

- agent-local/app/main.py

Problema:

- ainda concentra polling, fallback, envio de feedback e orquestração em um único arquivo
- ainda não envia heartbeat nem parâmetros operacionais do robô

Decisão:

Refatorar em módulos menores:

- snapshot-worker
- heartbeat-worker
- feedback-worker
- command-writer

### 5. Memória local

Arquivo:

- agent-local/app/memory.py

Problema:

- útil para defesa local, mas não pode virar fonte de verdade do sistema

Decisão:

Manter apenas como memória auxiliar de continuidade operacional, nunca como registro oficial.

### 6. EA MQL5 monolítico

Arquivo:

- mt5/VunoRemoteBridge.mq5

Problema:

- arquivo grande
- mistura parser JSON, indicadores, bridge, execução e feedback
- passa da regra de 200 linhas

Decisão:

Refatorar por módulos MQL5, preservando a lógica de proteção já implementada.

## Descartar como direção final

### 1. Web estática embutida no backend

Arquivos:

- backend/static/index.html
- backend/static/js/app.js

Motivo:

- serve para bootstrap e teste local
- não atende a meta de app operacional multi-tenant
- não cobre dashboard, operações, auditoria e parâmetros como produto final

Decisão:

Não usar como interface final do projeto.

### 2. Auth e sessão locais como solução definitiva

Arquivos:

- backend/app/database.py
- backend/app/main.py

Motivo:

- o fluxo atual funciona para teste
- mas não entrega o modelo final com tenant, RLS e operação SaaS segura

Decisão:

Descartar como arquitetura definitiva. Pode sobreviver apenas como bootstrap temporário.

### 3. Nomes atuais centrados em snapshot e feedback como modelo final

Arquivos:

- backend/app/database.py
- backend/app/models.py

Motivo:

- o projeto precisa falar mais claramente em robot instance, trade decision, trade result, audit event e heartbeat

Decisão:

Substituir a modelagem atual pela taxonomia oficial do MVP enxuto.

## O que fica como núcleo técnico do projeto

O núcleo reaproveitável real é este:

- agente local
- bridge por arquivos com MT5
- executor local blindado
- contrato remoto mínimo de decisão

Todo o resto ainda deve ser tratado como bootstrap ou transição.

## Próxima ação recomendada

Executar a Fase 1 do plano oficial sobre a base atual, sem reescrever tudo:

1. introduzir tenant e robot_instances
2. formalizar heartbeat
3. formalizar audit_events e user_parameters
4. quebrar backend/app/main.py em módulos
5. quebrar mt5/VunoRemoteBridge.mq5 em blocos menores