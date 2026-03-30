# SaaS Blueprint - Vuno Trader Platform

## Visao de produto

Plataforma SaaS de robo trader com IA, com area institucional publica e area privada autenticada para operacao, estudo e controle do robo.

## Areas do sistema

### 1. Site institucional (publico)

- home
- recursos
- planos
- faq
- contato
- politicas

### 2. Portal autenticado (app)

- dashboard de performance
- operacoes e historico
- estudos (videos e PDFs)
- parametros do robo
- auditoria de IA
- administracao da conta
- assinatura e cobranca

## Rotas sugeridas

### Publicas

- /
- /recursos
- /planos
- /faq
- /contato
- /politica-privacidade
- /termos
- /auth/login
- /auth/cadastro

### Privadas

- /app/dashboard
- /app/trades
- /app/trades/:id
- /app/estudos
- /app/parametros
- /app/ia-analises
- /app/admin/usuarios
- /app/admin/assinatura
- /app/admin/faturamento

## Papeis e permissoes

- owner: acesso total da organizacao
- admin: gestao operacional
- analyst: analise e configuracao de estrategia
- viewer: leitura de dados

## Planos SaaS

### Starter

- 1 robo
- limite de tokens diario baixo
- limite de operacoes historicas
- 1 usuario admin

### Pro

- multiplos robos
- limite de tokens maior
- mais usuarios
- analise IA avancada

### Scale

- limites altos
- suporte prioritario
- recursos empresariais
- exportacao e webhooks premium

## Metricas de produto

- MRR
- churn
- CAC
- LTV
- ativacao de conta
- engajamento semanal
- custo de IA por cliente

## MVP de entrega

### Sprint 1

- auth
- dashboard basico
- cadastro de parametros
- ingestao de trade

### Sprint 2

- painel admin
- planos e assinatura
- modulo de estudos
- logs de IA e custos

### Sprint 3

- auditoria completa
- anonimização automatica
- comparativo demo x real
- painel institucional completo
