# 2026-04-04 - Limpeza de legado no painel e rotas mortas

## Data

- 2026-04-04

## Objetivo

- remover itens mortos ou sem consumo real no painel do usuario e na superficie web MT5
- alinhar a linguagem do painel ao fluxo atual `agent-local + bridge`
- evitar que o codigo morto continue confundindo a leitura do produto

## Arquivos impactados

- `backend/app/api/router.py`
- `backend/app/api/routes/trading_profile.py`
- `web/src/app/api/mt5/robot-credentials/route.ts`
- `web/src/components/app/trading-profile-selector.tsx`
- `web/src/app/app/dashboard/page.tsx`
- `web/src/app/app/admin/page.tsx`
- `web/src/components/app/parametros-form.tsx`
- `projeto/implantacao-mt5-visao-shadow-e-duplo-robo.md`

## Decisao

- removida a rota web `POST /api/mt5/robot-credentials`, porque o fluxo atual do painel usa `POST /api/mt5/robot-package` e nao havia mais nenhum consumo interno da rota antiga
- removido o componente `trading-profile-selector`, porque nao tinha nenhum import no app e dependia de um proxy `/api/profile/*` que nao existe na web atual
- removidas as rotas backend de `trading_profile`, porque estavam desacopladas do painel atual e sem consumidor interno identificado
- ajustada a linguagem herdada de `brain Python` para `motor`, `agent-local` e `bridge`, reduzindo divergencia entre UI e arquitetura oficial em transicao

## Validacao executada

- busca de referencias no workspace para confirmar ausencia de imports do `trading-profile-selector`
- busca de chamadas frontend para confirmar ausencia de consumo de `web/src/app/api/mt5/robot-credentials/route.ts`
- validacao de erros do editor apos a limpeza

## Alternativas descartadas

- remover `backend/app/api/routes/mt5.py`: descartado porque ainda e legado ativo do fluxo principal da raiz
- mexer no `vuno_core` e nos scripts Python auxiliares: descartado porque continuam sendo parte viva da camada de inteligencia e CLI

## Riscos e observacoes

- a duplicacao entre telas que leem instancias do robo continua existindo, mas ainda nao e codigo morto; ela exige refactor, nao exclusao cega
- o fluxo `/api/mt5/*` continua vivo na raiz e nao foi removido nesta limpeza

## Proximos passos

1. consolidar leitura e alteracao de instancias em um hook compartilhado do painel
2. migrar a semantica restante do dashboard para `Robo Integrado` e `Robo Hibrido Visual`
3. tratar o legado `/api/mt5/*` em migracao controlada para o contrato alvo `/api/agent/*`