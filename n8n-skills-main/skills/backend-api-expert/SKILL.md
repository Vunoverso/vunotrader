---
name: backend-api-expert
description: Arquitetura de sistemas backend, APIs robustas e segurança de dados.
---

# Backend & API Architecture

Construa o motor que alimenta suas aplicações com segurança e escalabilidade.

## Arquitetura de APIs

### 1. REST & GraphQL
- Use nomes de recursos claros no plural (ex: `/api/users`).
- Implemente códigos de status HTTP corretos (200, 201, 400, 401, 500).

### 2. Segurança de Dados
- **Autenticação**: Use JWT (JSON Web Tokens) ou cookies `httpOnly`.
- **Validação**: Sempre valide a entrada do usuário (use Zod ou Joi).
- **Sanitização**: Evite ataques XSS e SQL Injection limpando os dados de entrada.

### 3. Modelagem de Banco de Dados
- Normalize os dados em SQL para evitar redundância.
- Use indexação adequada em colunas que são consultadas com frequência.

## DevOps Básico
- Utilize Variáveis de Ambiente (`.env`) para chaves e senhas.
- Configure logs (Winston ou Pino) para monitorar erros em produção.
