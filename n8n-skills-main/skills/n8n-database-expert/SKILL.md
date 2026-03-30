---
name: n8n-database-expert
description: Melhores práticas para operações de banco de dados no n8n (SQL/NoSQL).
---

# n8n Database Expert

Este guia fornece orientações para interagir de forma eficiente com bancos de dados no n8n.

## Operações Eficientes

### 1. Batching (Processamento em Lote)
- Evite inserir uma linha por vez se tiver milhares de registros. Use modos de "Insert" ou "Update" que suportam múltiplos itens por execução.

### 2. Consultas Personalizadas (Query)
- Use o nó **Execute Query** para consultas complexas que os nós básicos não suportam.
- Sempre use parâmetros bind (ex: `$1`, `$2`) para evitar SQL Injection.

### 3. Conexões
- Certifique-se de que as credenciais possuem apenas as permissões necessárias (Princípio do Menor Privilégio).

## Bancos de Dados Suportados
- **PostgreSQL / MySQL**: Ideais para dados relacionais estruturados.
- **MongoDB**: Excelente para documentos JSON flexíveis.
- **Airtable / Google Sheets**: Ótimos para prototipagem rápida e interface humana.
