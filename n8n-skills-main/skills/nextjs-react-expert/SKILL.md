---
name: nextjs-react-expert
description: Guia especializado em desenvolvimento frontend moderno com Next.js, React e otimização de performance.
---

# Next.js & React Expert

Guia para construção de aplicações web de alto desempenho e escaláveis.

## Melhores Práticas de Desenvolvimento

### 1. Renderização e Performance
- **Server Components (RSC)**: Use-os por padrão em Next.js para reduzir o bundle de JS enviado ao cliente.
- **SSG & ISR**: Pré-renderize páginas que mudam pouco para garantir carregamentos instantâneos.

### 2. Gerenciamento de Estado
- Use **Context API** para estados globais simples.
- Use **Zustand** ou **Redux Toolkit** para estados complexos e persistentes.

### 3. Estruturação de Componentes
- Siga o padrão **Atomic Design** ou pastas por funcionalidade.
- Mantenha componentes pequenos e focados em uma única responsabilidade.

## Otimização
- Use o componente `next/image` para otimização automática de imagens.
- Implemente `Dynamic Imports` para adiar o carregamento de componentes pesados.
