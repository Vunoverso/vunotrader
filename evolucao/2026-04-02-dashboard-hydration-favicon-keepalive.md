# 2026-04-02 — Frontend: hidratação do dashboard, keep-alive e favicon

## Objetivo

Corrigir erro React minificado em produção no dashboard, remover ruído de refresh periódico no console e eliminar 404 de `favicon.ico`.

## Problemas observados

### 1. React minified error #418 no dashboard

Sintoma reportado no browser em produção:

- `Uncaught Error: Minified React error #418`

Diagnóstico:

- o dashboard usa `TerminalFeed` como componente client-side
- esse componente renderizava horários com `new Date(...).toLocaleTimeString("pt-BR")` já no primeiro render
- em SSR/client hydration isso pode divergir por timezone/locale do Node vs navegador
- resultado: mismatch de texto durante hidratação

### 2. Refresh keep-alive barulhento e intrusivo

Sintoma:

- logs repetidos no console: `[Vuno] Refreshing dashboard to keep-alive...`
- `router.refresh()` era disparado a cada 5 minutos no dashboard

Diagnóstico:

- isso não era ideal para UX
- além do ruído no console, forçava refresh da rota sem necessidade
- o objetivo real era apenas manter o backend Render aquecido

### 3. `favicon.ico` retornando 404

Sintoma:

- navegador requisitando `/favicon.ico` com 404

Diagnóstico:

- já existia `app/icon.svg`, mas alguns navegadores continuam pedindo `/favicon.ico`
- faltava fallback explícito

## Correções aplicadas

### `web/src/components/app/terminal-feed.tsx`

- adicionados formatadores `Intl.DateTimeFormat` com timezone fixo `America/Sao_Paulo`
- o relógio do terminal e os horários dos logs agora usam formatação determinística entre SSR e client
- isso remove a principal fonte do hydration mismatch do dashboard

### `web/src/components/app/dashboard-refresher.tsx`

- removido `router.refresh()` periódico
- removido log repetitivo no console
- substituído por ping silencioso `fetch(..., { mode: "no-cors", cache: "no-store" })` para `https://vunotrader-api.onrender.com/`
- o ping respeita aba oculta (`document.visibilityState === "hidden"`)

### `web/src/components/app/auditoria-table.tsx`

- datas de exibição passaram a usar timezone explícito `America/Sao_Paulo`

### `web/src/components/app/operacoes-table.tsx`

- datas de exibição passaram a usar timezone explícito `America/Sao_Paulo`

### `web/src/app/layout.tsx`

- metadata agora declara `icons.icon`, `icons.shortcut` e `icons.apple` apontando para `/icon.svg`

### `web/src/app/favicon.ico/route.ts`

- criado fallback de rota para `/favicon.ico`
- redireciona para `/icon.svg`

## Validação

- `npm run build` em `web/` concluído com sucesso após as mudanças
- dashboard local em `http://localhost:3001/app/dashboard` carregou no navegador integrado sem reproduzir o erro React reportado
- acesso a `http://localhost:3001/favicon.ico` redirecionou corretamente para `/icon.svg`

## Arquivos impactados

- `web/src/components/app/terminal-feed.tsx`
- `web/src/components/app/dashboard-refresher.tsx`
- `web/src/components/app/auditoria-table.tsx`
- `web/src/components/app/operacoes-table.tsx`
- `web/src/app/layout.tsx`
- `web/src/app/favicon.ico/route.ts`

## Observações

- o frontend do Render continuava com `500` global durante a análise; isso é separado deste bug de hidratação e já havia sido rastreado anteriormente para mismatch/configuração de env pública do Supabase
- o keep-alive silencioso pode gerar request de background para o backend Render, mas não deve mais poluir o console da aplicação