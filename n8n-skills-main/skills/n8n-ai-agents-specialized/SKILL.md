---
name: n8n-ai-agents-specialized
description: Guia avançado para construção de agentes de IA no n8n, focando em memória, ferramentas e tipos de agentes.
---

# n8n AI Agents Specialized

Este guia ensina como construir agentes de IA robustos e inteligentes dentro do n8n.

## Melhores Práticas para Agentes

### 1. Escolha do Tipo de Agente
- **ReAct**: Ideal para tarefas que exigem raciocínio passo a passo e uso de ferramentas.
- **Plan-and-Execute**: Melhor para objetivos complexos que precisam de um planejamento inicial antes da execução.

### 2. Gestão de Memória
- Utilize o nó **Window Buffer Memory** para conversas curtas.
- Use **Redis** ou bancos de dados externos para persistência de memória em longo prazo (sessões de dias ou semanas).

### 3. Implementação de Ferramentas (Tools)
- Conecte nós de **HTTP Request** ou **Google Search** como ferramentas do agente.
- Sempre descreva a ferramenta de forma clara no campo "Description" do nó, pois o agente usa essa descrição para decidir quando usá-la.

## Padrões Comuns
- **RAG (Retrieval-Augmented Generation)**: Conecte um nó de Vector Store para que o agente possa consultar seus próprios documentos.
- **Encadeamento de Agentes**: Use um agente para planejar e outro para executar tarefas específicas.
