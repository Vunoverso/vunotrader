# Evolução - Fase 1 Tenant, Robot Instance e Heartbeat

Data: 2026-04-02

## Objetivo

Aplicar a Fase 1 do plano oficial sobre a base reaproveitada, introduzindo tenant, robot_instances, audit_events e heartbeat sem reescrever todo o projeto.

## Arquivos impactados

- README.md
- backend/app/main.py
- backend/app/database.py
- backend/app/models.py
- backend/app/decision_engine.py
- backend/app/audit.py
- backend/app/deps.py
- backend/app/routes/auth.py
- backend/app/routes/robot_instances.py
- backend/app/routes/agent.py
- backend/static/index.html
- backend/static/js/app.js
- agent-local/app/config.py
- agent-local/app/api_client.py
- agent-local/app/bridge.py
- agent-local/app/main.py
- agent-local/config.example.json
- agent-local/runtime/config.json

## Decisão

Foi mantido o bootstrap atual em FastAPI e SQLite local, mas com alinhamento explícito ao MVP enxuto:

- registro agora cria tenant e profile default
- criação de instância do robô passou a usar robot_instances
- decisões e resultados passaram a gravar em trade_decisions e trade_results
- audit_events foi introduzido como trilha mínima de rastreabilidade
- heartbeat passou a atualizar o estado da instância do robô

## Alternativas descartadas

- reescrever tudo para a arquitetura final antes de validar a Fase 1: descartado por custo e baixa velocidade de entrega
- manter devices, snapshots e trade_feedback como nomes centrais do domínio: descartado por desalinhamento com o plano oficial
- registrar todo heartbeat em audit_events: descartado por gerar ruído e crescimento excessivo do log

## Observações

- backend/app/main.py foi quebrado em rotas menores para reduzir acoplamento
- o agente local continua compatível com X-Device-Token, mas passa a enviar também X-Robot-Token
- o contrato de decisão agora expõe rationale e mantém reason por compatibilidade com a ponte local

## Validação executada

- compilação de sintaxe Python concluída com sucesso após a refatoração
- backend respondeu normalmente em /api/health
- fluxo real de registro, login e criação de robot instance foi validado
- heartbeat foi validado por chamada real HTTP
- agente local processou snapshot real de teste e gerou comando local
- trade_feedback foi persistido com sucesso
- contagem final em banco limpo durante a validação:
  - tenants: 1
  - profiles: 1
  - robot_instances: 1
  - trade_decisions: 1
  - trade_results: 1
  - audit_events: 6

## Próximos passos

1. formalizar user_parameters no backend
2. expor consulta de auditoria e status das instâncias
3. iniciar dashboard operacional mínimo
4. avaliar a migração do bootstrap local para persistência SaaS definitiva