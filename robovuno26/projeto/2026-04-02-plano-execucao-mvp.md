# Plano de Execução - MVP Enxuto

Data: 2026-04-02

## O que entra agora

### Fase 1 - Base segura

- autenticação
- tenant e perfil de usuário
- robot instance com token
- persistência mínima de auditoria
- layout autenticado básico

Critério de pronto:

- usuário autentica
- usuário só acessa dados do próprio tenant
- instância do robô pode ser registrada com token válido

### Fase 2 - Operação principal

- dashboard operacional
- tela de operações
- tela de auditoria
- tela de parâmetros

Critério de pronto:

- dashboard exibe status e resumo operacional
- operações mostram ativo, horário, resultado e status
- auditoria mostra signal, confidence, rationale e motivo do HOLD
- parâmetros de risco podem bloquear operação insegura

### Fase 3 - Integração real

- heartbeat do robô
- decisão remota BUY, SELL ou HOLD
- persistência de trade_decisions
- persistência de trade_results
- ligação entre instância MT5 e tenant

Critério de pronto:

- robô conecta com token válido
- sistema recebe heartbeat
- brain responde decisão com contrato mínimo
- decisões e resultados ficam auditáveis por tenant

## O que fica para depois

### Pós-MVP

- comparativo demo vs real com visão histórica
- alertas simples
- onboarding melhorado
- empacotamento final do agente local

### Fora do escopo inicial

- recommendation engine
- retreinamento automático
- cobrança avançada
- API pública externa
- automações complexas de admin
- ingestão de PDFs, vídeos e estudos

## Regras de corte

Se surgir dúvida sobre prioridade, manter apenas o que suporta este núcleo:

- autenticação
- tenant
- decisão
- auditoria
- parâmetros
- integração MT5

Tudo que não reforça esse núcleo deve sair do MVP.

## Observação sobre a base atual

A implementação já existente pode ser reaproveitada como bootstrap técnico em três pontos:

- agente local
- ponte com MT5
- contrato inicial de decisão remota

Mas ela ainda precisa ser alinhada com tenant, heartbeat, auditoria e parâmetros para aderir a este plano oficial.