---
name: n8n-performance-optimization
description: Orientações sobre como otimizar fluxos de trabalho do n8n para velocidade e eficiência de memória.
---

# n8n Performance Optimization

Mantenha seu servidor n8n rápido, mesmo com fluxos complexos.

## Dicas de Performance

### 1. Limite a Transferência de Dados
- Busque apenas as colunas/campos que você realmente vai usar.
- Use filtros na fonte (ex: na query SQL ou no filtro da API) em vez de baixar tudo e filtrar no n8n.

### 2. Evite Loops Desnecessários
- O nó **Split In Batches** é útil, mas processar um por um pode ser lento. Se possível, use nós que suportam operações em massa.

### 3. Gestão de Memória
- Se estiver processando arquivos grandes (PDF, Imagens), use o nó **Read Binary File** com cautela e limpe os dados assim que terminar o processamento.

## Configuração do Servidor
- Utilize o modo "Main" ou "Queue" dependendo do volume de execuções.
