# Arquitetura MVP - Vuno Trader Enxuto

Data: 2026-04-02

## Objetivo

Entregar uma base enxuta, auditável e segura para um motor de decisão e controle operacional do MT5 em modelo SaaS.

O produto não deve ser tratado como promessa de lucro automático. O foco é controle, rastreabilidade, parâmetros de risco e operação assistida por decisão remota.

## Direção do produto

1. Clareza operacional acima de volume de features.
2. Multi-tenant desde o início.
3. Demo-first como regra de segurança.
4. Auditoria obrigatória de decisão e execução.
5. Brain remoto pequeno, previsível e explicável.

## Decisão arquitetural

Foi adotada uma arquitetura em três camadas:

1. Web + Backend SaaS
   - autenticação de usuários
   - cadastro de tenant e vínculo de usuário
   - geração de token de instância do robô
   - dashboard, operações, auditoria e parâmetros
   - persistência central de heartbeat, decisões e resultados

2. Agente local
   - roda na máquina do cliente
   - autentica com token de dispositivo
   - lê snapshots produzidos pelo MT5
   - envia contexto ao backend/brain
   - grava comandos locais para o MT5
   - mantém memória local simples para degradação defensiva e continuidade operacional

3. MT5 Executor
   - gera snapshots de mercado
   - lê comando local
   - envia heartbeat operacional via agente local
   - aplica regras locais de segurança
   - executa ordem somente se o contexto permitir

## Por que essa arquitetura

- reduz acoplamento entre MT5 e internet externa
- mantém a execução sensível dentro da máquina do usuário
- permite modelo SaaS com licenciamento, tenant e tokens
- cria caminho de evolução para motor remoto mais avançado via MCP sem quebrar o executor local

## Escopo oficial do MVP

Entram agora:

- autenticação
- tenant e usuário
- token da instância MT5
- heartbeat do robô
- dashboard operacional básico
- tela de operações
- tela de auditoria
- tela de parâmetros
- integração básica com MT5
- brain remoto em Python com decisão BUY, SELL ou HOLD

Ficam fora desta primeira versão:

- estudos com PDF e vídeo
- recommendation engine
- retreinamento automático
- cobrança avançada
- API pública externa
- automações complexas de administração

## Regras locais de execução

O EA local é a última barreira antes da ordem. Mesmo com comando remoto válido, ele ainda filtra:

- mercado aberto
- spread máximo
- risco clampado
- limite de posições por ativo
- tentativa protegida com retry

Além disso, o modo real deve ficar bloqueado por regra explícita e auditável.

## Contrato mínimo do brain

O brain remoto deve responder de forma pequena e previsível:

- signal
- confidence
- rationale
- risk

O contrato precisa ser suficiente para auditoria e para exibir claramente por que houve BUY, SELL ou HOLD.

## Memória e aprendizado

Nesta versão, memória significa:

- memória local do agente com decisões e resultados recentes
- memória central do backend com heartbeat, decisões e resultados
- ajuste simples de risco com base no histórico recente do símbolo

Não há treino automático de modelo nesta etapa.

## Entidades mínimas

Modelo de dados inicial recomendado:

- tenants
- profiles
- robot_instances
- user_parameters
- trade_decisions
- trade_results
- ai_usage_logs
- audit_events

Se algum dado puder ser derivado, ele não deve ganhar tabela própria no MVP.

## Interface SaaS

O sistema SaaS deve expor no mínimo:

- autenticação
- dashboard operacional
- operações
- auditoria
- parâmetros
- instalação do robô

## Segurança obrigatória

1. Toda leitura e escrita com tenant_id.
2. Logs sem tokens, senhas, conta MT5 ou segredos.
3. Chaves sensíveis só no backend e ambiente seguro.
4. Endpoints com validação de entrada e rate limit.
5. Dados reutilizados por IA devem ser anonimizados.

## Divergência atual com a implementação

Na base criada até aqui, ainda existem diferenças em relação a esta arquitetura-alvo:

- web atual está estática, não em app dedicado multi-tenant
- persistência atual é SQLite local, ainda sem tenant_id e RLS
- heartbeat do robô ainda não está persistido no backend
- auditoria e parâmetros ainda não existem como módulos formais

Essas diferenças ficam aceitas apenas como etapa transitória do bootstrap inicial.

## Evolução prevista

1. consolidar tenant, heartbeat, auditoria e parâmetros
2. substituir a persistência local do backend por base SaaS adequada
3. estruturar frontend autenticado para operação diária
4. adicionar comparativo demo vs real
5. evoluir o motor remoto para MCP quando o núcleo estiver estável