---
name: ai-ecosystem-architect
description: Orquestração de múltiplas IAs (Texto, Imagem, Código e Decisão) e agentes autônomos.
---

# Arquiteto de Ecossistemas de IA

Como criar sistemas onde várias IAs colaboram para resolver problemas complexos.

## Padrão de Orquestração

### 1. Separação de Responsabilidades
- **IA de Decisão**: Atua como o "Cérebro" que planeja a execução.
- **IA de Execução**: Especialistas em tarefas específicas (ex: gerar código, analisar logs).
- **IA de Revisão**: Atua como o "Controle de Qualidade".

### 2. Agentes Autônomos (Loop)
- Implemente loops de `Percepção -> Raciocínio -> Ação`.
- Dê ferramentas (Tools) para que o agente possa interagir com o mundo real (n8n, APIs).

## Visão de Mestre
- Não use uma IA para tudo. Crie um **Pipeline** onde a saída de uma IA alimenta a próxima.
- Utilize "Bibliotecas de Habilidades" (Skill Systems) para que a IA possa escolher a melhor ferramenta para o momento.
