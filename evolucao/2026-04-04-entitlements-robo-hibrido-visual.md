# 2026-04-04 - Entitlements e schema do Robo Hibrido Visual

## Data

2026-04-04

## Objetivo

Transformar o rollout do Robo Hibrido Visual em enforcement real de schema e acesso, sem depender apenas de planCode ou promessa de UI.

## Arquivos impactados

- supabase/migrations/20260404_000018_visual_robot_entitlements.sql
- web/src/lib/subscription-access.ts
- web/src/lib/mt5/package-template.ts
- web/src/app/api/mt5/robot-package/route.ts
- web/src/app/api/mt5/robot-credentials/instances/route.ts
- web/src/components/app/mt5-credentials-generator.tsx
- web/src/components/app/robot-installation-lanes.tsx
- web/src/components/app/robot-product-dashboard-lanes.tsx
- web/src/components/app/mt5-robot-instances-panel.tsx
- web/src/app/app/instalacao/page.tsx
- web/src/app/app/dashboard/page.tsx
- web/src/app/app/layout.tsx

## Decisao

Foi adotado o backend efetivo do fluxo atual, que esta no app web com Supabase, como ponto de enforcement do novo produto.

Entraram juntos:

- tabelas `saas_features` e `saas_plan_features` com seed inicial para `starter`, `pro` e `scale`
- campos formais em `robot_instances` para `robot_product_type`, `visual_shadow_enabled`, `computer_use_enabled` e `human_approval_required`
- tabela `trade_visual_contexts` com RLS e indices para persistir o ciclo visual quando essa camada entrar em runtime
- carregamento de feature map real em `subscription-access`, com fallback legado por `planCode` apenas para transicao segura
- bloqueio de criacao do `robo_hibrido_visual` no route real de instalacao quando o plano nao liberar a feature
- empacotamento do runtime com `robot_product_type` e `visual_shadow_enabled`
- UI de instalacao e dashboard ajustadas para ler feature flags reais, em vez de inferir `Pro` e `Scale` diretamente

## Alternativas descartadas

- manter entitlement do robo visual espalhado em condicionais por `planCode`: descartado por fragilidade comercial e tecnica
- liberar o seletor visual apenas por UI sem schema correspondente: descartado por incoerencia entre promessa e persistencia
- esperar o runtime visual completo para criar schema e gating: descartado porque isso manteria a linha visual sem governanca real

## Validacao executada

- diagnosticos do editor sem erros nos arquivos alterados
- build do app web com `npm run build`
- correcao adicional no retorno binario de `NextResponse` para usar `Blob` compativel com o typecheck do Next 16

## Riscos e observacoes

- `trade_visual_contexts` entrou apenas como infraestrutura de schema; ainda nao existe escrita real dessa tabela no runtime
- o fallback legado por `planCode` permanece em `subscription-access` para evitar quebra enquanto o seed de feature flags nao estiver presente em todos os ambientes
- ainda nao existe UI administrativa para gerenciar `saas_plan_features`; o seed atual cobre apenas o rollout inicial

## Proximos passos

1. aplicar a migration nos ambientes Supabase ativos e confirmar seed de features
2. ligar o pipeline real de captura e persistencia em `trade_visual_contexts`
3. expor gestao administrativa de feature flags por plano para reduzir dependencia do fallback legado