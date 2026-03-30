---
name: ai-rag-memory
description: Implementação de Retrieval-Augmented Generation e sistemas de memória persistente.
---

# RAG & Memória Estruturada

Ensine a IA a nunca esquecer e a consultar conhecimentos externos de forma inteligente.

## Arquitetura RAG (Busca Externa)

### 1. Fragmentação (Chunking) e Embedding
- Divida documentos grandes em pedaços menores (ex: 500 tokens).
- Transforme esses pedaços em vetores (Embeddings) para busca semântica.

### 2. Recuperação (Retrieval)
- Use bancos de dados vetoriais (Pinecone, ChromaDB, Weaviate) para encontrar os pedaços mais relevantes para a pergunta.

## Gestão de Memória
- **Memória de Curto Prazo**: Últimas mensagens da conversa (Buffer).
- **Memória de Longo Prazo**: Resumos de interações passadas ou Knowledge Graphs que guardam relações entre conceitos.

## Dica de Mestre
- Sempre peça para a IA citar a fonte da informação recuperada para evitar alucinações.
