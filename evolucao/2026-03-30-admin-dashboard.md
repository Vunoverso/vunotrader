# 2026-03-30 — Admin Dashboard

## Objetivo
Criar painel administrativo da plataforma Vuno Trader para visão consolidada de todos os tenants, usuários, planos e uso da IA.

## Data
2026-03-30

## Arquivos criados/impactados
- `web/src/app/app/admin/page.tsx` — nova página (Server Component)
- `web/src/components/app/app-sidebar.tsx` — adição do link Admin condicional (prop `isAdmin`)
- `web/src/app/app/layout.tsx` — passa `isAdmin` para o sidebar via `user.user_metadata.is_admin`

## Decisão de arquitetura

### Proteção de acesso
- Proteção via `user.user_metadata.is_admin === true`  
- O campo `is_admin` deve ser setado manualmente via Supabase Auth Dashboard ou via SQL:
  ```sql
  UPDATE auth.users SET raw_user_meta_data = raw_user_meta_data || '{"is_admin": true}' WHERE email = 'admin@vunostudio.com.br';
  ```
- Alternativa considerada: tabela dedicada `platform_admins` com RLS — descartada por simplicidade no MVP, pode ser adotada em versão futura

### Dados consultados
- `user_profiles` — contagem de usuários e lista dos 8 mais recentes
- `organizations` — contagem de orgs/tenants
- `saas_subscriptions` — assinaturas ativas + join com saas_plans para MRR
- `ai_usage_logs` — tokens usados hoje (base para custo IA)

### Métricas exibidas
- Total usuários, organizações, assinaturas ativas, MRR estimado
- Distribuição visual por plano (Starter / Pro / Scale) com barra proporcional
- Tokens IA do dia e custo estimado (US$ 0.000002/token)
- Status do sistema: Brain Python, MT5/EA, Supabase

## Riscos
- O campo `is_admin` em `user_metadata` pode ser manipulado via client se RLS não for rigorosa no banco — o redirect no Server Component é adequado para MVP mas deve ser reforçado com RLS adicional
- Consultas de agregação podem ficar lentas com muitos usuários — adicionar índices quando necessário

## Próximos passos
- [ ] Criar página `/app/admin/usuarios` com lista paginada e ações (banir, alterar plano)
- [ ] Criar página `/app/admin/planos` para editar limites e preços
- [ ] Adicionar logs de auditoria de acesso admin
- [ ] Migrar verificação admin para tabela `platform_admins` com RLS
- [ ] Adicionar gráfico de MRR histórico (precisa de `billing_events`)

## Atualização da evolução (2026-03-30)

### Entrega realizada
- Menu de ações em `/app/admin/usuarios` recebeu opção **Trocar plano** (Starter, Pro, Scale)
- Nova server action `changePlanAction` criada para atualizar/registrar assinatura em `saas_subscriptions`
- Ação prioriza plano por `code` em `saas_plans` (ativo), faz update da assinatura existente ou cria nova
- Tela de usuários ajustada para mostrar `Sem plano` quando não há assinatura vinculada
- Menu de ações ganhou atalho **Criar organização e vincular** para usuários sem org
- Nova server action `createOrganizationForUserAction` cria `organizations` + vínculo `organization_members` (owner)
- `createAdminClient` ajustado para aceitar `SUPABASE_URL` como fallback de `NEXT_PUBLIC_SUPABASE_URL`
- Incluída ação **Troca de ciclo mensal/anual** no submenu de plano
- Incluída ação **Gerenciar vínculo** com troca de papel (`owner/admin/analyst/viewer`)
- Incluída ação **Remover usuário da organização** (com proteção para não remover último owner)
- Incluída proteção para não rebaixar o último owner via troca de papel
- Tabela de usuários ganhou coluna **Ciclo** com badge (`Mensal`/`Anual`)

### Arquivos impactados
- `web/src/app/app/admin/usuarios/actions.ts`
- `web/src/app/app/admin/usuarios/page.tsx`
- `web/src/app/app/admin/usuarios/_components/user-action-menu.tsx`

### Observação funcional
- Quando o usuário está `Sem org`, o botão **Trocar plano** fica desabilitado por segurança
- Para habilitar, é necessário vínculo em `organization_members`

### Revisão de backlog
- [x] Criar página `/app/admin/usuarios` com lista paginada e ações (banir, alterar plano)
- [ ] Criar página `/app/admin/planos` para editar limites e preços
