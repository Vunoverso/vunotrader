# Evolução - Corte Técnico da Base Atual

Data: 2026-04-02

## Objetivo

Registrar a decisão sobre o que da base inicial pode ser mantido, o que exige refatoração e o que não deve seguir como arquitetura final.

## Arquivos impactados

- projeto/2026-04-02-corte-tecnico-base-atual.md

## Decisão

Foi definido que o núcleo realmente aproveitável do bootstrap inicial é:

- agente local
- ponte por arquivos com MT5
- execução local blindada no EA
- contrato remoto mínimo de decisão

Foi definido também que a parte atual de web estática e persistência local do backend não representa a arquitetura final do produto.

## Alternativas descartadas

- manter a base atual como arquitetura definitiva: descartado por ausência de tenant, heartbeat, auditoria formal e parâmetros
- descartar toda a base e recomeçar: descartado porque a ponte local, o executor MT5 e o contrato remoto já entregam valor técnico real

## Observações

- backend/app/main.py e mt5/VunoRemoteBridge.mq5 devem ser refatorados para respeitar a regra de arquivos menores
- a memória local do agente deve continuar apenas como apoio, nunca como registro oficial do sistema

## Próximos passos

1. aplicar a Fase 1 do plano oficial sobre a base reaproveitada
2. introduzir tenant e robot_instances
3. implementar heartbeat e audit_events