# Frontend Home Base

## Data

2026-03-29

## Objetivo

Criar a base do frontend SaaS e entregar a primeira home institucional com navegacao, hero sections e componentes reutilizaveis em Tailwind.

## Caminho escolhido

- Next.js com App Router
- Tailwind CSS
- pasta dedicada [web](../web)
- composicao da home a partir de blocos reutilizaveis

## Motivo da escolha

- alinha com o plano SaaS definido para site publico e area autenticada
- facilita evolucao futura para login, dashboard e areas privadas no mesmo frontend
- permite reuso de secoes, containers e cards sem espalhar markup repetido

## Alternativas analisadas e nao adotadas agora

### Vite + React

Nao adotado porque o projeto ja foi direcionado para um SaaS com rotas publicas e autenticadas, onde Next.js traz uma base mais consistente para crescimento.

### Separar site institucional e app em projetos diferentes agora

Nao adotado neste momento para evitar duplicacao de design system, autenticacao e infraestrutura cedo demais.

## Arquivos criados e alterados

- [web/src/app/page.tsx](../web/src/app/page.tsx)
- [web/src/app/layout.tsx](../web/src/app/layout.tsx)
- [web/src/app/globals.css](../web/src/app/globals.css)
- [web/src/lib/marketing-content.ts](../web/src/lib/marketing-content.ts)
- [web/src/components/marketing/section-shell.tsx](../web/src/components/marketing/section-shell.tsx)
- [web/src/components/marketing/feature-card.tsx](../web/src/components/marketing/feature-card.tsx)
- [web/src/components/marketing/metric-pill.tsx](../web/src/components/marketing/metric-pill.tsx)
- [web/src/components/marketing/cta-banner.tsx](../web/src/components/marketing/cta-banner.tsx)

## Entrega funcional desta etapa

- home institucional inicial
- cabecalho com navegacao
- hero principal
- secoes de recursos, fluxo, planos e FAQ
- CTA final
- blocos reutilizaveis para futuras paginas

## Observacoes

- o scaffold criou um .git interno no frontend e ele foi removido para manter um unico repositorio principal
- o lint do frontend passou sem erros

## Proximos passos

- criar telas de login, cadastro e recuperacao de senha
- integrar frontend com backend auth
- iniciar dashboard autenticado