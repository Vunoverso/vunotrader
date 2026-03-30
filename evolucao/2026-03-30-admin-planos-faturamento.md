# 2026-03-30 - Admin: Planos (criação, histórico), Faturamento e Auditoria

**Data:** 2026-03-30  
**Status:** ✅ Completo  
**Trabalho:** Expansão do admin panel para completar o ciclo SaaS (items 1 e 3 do roadmap)

## Objetivo

Implementar as funcionalidades solicitadas pelo usuário para o painel admin:
1. **Criar novo plano** + **histórico de alterações** (preço/limites)
2. **Faturamento** com eventos de cobrança e histórico de pagamentos

## Arquivos impactados

### Criados

- **`web/src/app/app/admin/planos/page.tsx`** (melhorado)
  - Adicionado form "Novo plano" no topo com action `createPlanAction`
  - Link para página de histórico no header
  - Grid de planos editáveis com limites operacionais

- **`web/src/app/app/admin/planos/historico/page.tsx`** (novo)
  - Página de auditoria completa de mudanças em planos
  - Filtro por plano, pagination (25 por página)
  - Mostra tipo de mudança (price_update, limit_update, status_change, plan_created)
  - Exibe valor anterior e novo valor com timestamps e usuário

- **`web/src/app/app/admin/faturamento/page.tsx`** (novo)
  - Painel de controle de eventos de cobrança
  - Status: charge_succeeded, charge_failed, refund_issued, etc.
  - Filtros por status e provider
  - Integração com `billing_events` table do Supabase
  - Pagination (20 por página)
  - Métricas de cobranças bem-sucedidas, falhadas, reembolsos

- **`supabase/migrations/20260330_create_plan_changes_table.sql`** (novo)
  - Tabela `plan_changes` para auditoria de mudanças em planos
  - Campos: plan_id, change_type, field_name, old_value, new_value, changed_by, created_at
  - RLS Policy: apenas admins podem ler
  - Índices para perfomance em queries frequentes

- **`web/src/app/app/admin/planos/actions.ts`** (atualizado)
  - Adicionada função `logPlanChange()` para registrar mudanças
  - `createPlanAction()` agora registra plano criado + preços + limites definidos
  - `updatePlanAction()` agora compara valores anteriores e registra apenas mudanças detectadas
  - Logs incluem user_id de quem fez a alteração

### Modificados

- **`web/src/components/app/app-sidebar.tsx`**
  - Adicionado link `/app/admin/faturamento` ao submenu de admin

## Decisões técnicas

### Auditoria sem triggers SQL

❌ **Não usando:** triggers SQL na tabela `saas_plans`  
✅ **Usando:** logging explícito em `updatePlanAction()` e `createPlanAction()`

**Motivo:** Easier to track `changed_by` (user_id), avoids state sync issues between plans/limits tables, simplifies testing.

### Normalização de dados Supabase

Problema: Supabase retorna arrays para relacionamentos, não objetos únicos. Ex:
```typescript
saas_plans: [{ id: '...', name: '...' }]  // array
```

Solução: Helper functions `normalizeEvent()` e `normalizeChange()` que extraem primeiro item de arrays se presentes.

## Validação

✅ Sem erros TypeScript  
✅ Todas as páginas com admin guard (`is_admin` check)  
✅ RLS policies aplicadas na tabela `plan_changes`  
✅ Forms wired corretamente com `revalidatePath()` em múltiplas rotas

## Schema & Data

### Novo

Tabela `plan_changes`:
```sql
- id (UUID, PK)
- plan_id (FK → saas_plans)
- change_type (price_update | limit_update | status_change | plan_created)
- field_name (monthly_price, max_users, is_active, etc)
- old_value (nullable)
- new_value (required)
- changed_by (FK → auth.users, nullable)
- created_at (timestamp)
```

### Reutilizado

- `billing_events` (já existia)
  - Agora visualizável no painel faturamento
  - Filtros por status/provider

## User Experience

### Item 1: Planos + Histórico

Fluxo:
1. Admin vai para `/app/admin/planos`
2. Vê grid de planos ativos + métricas (MRR, capacity, subscriptions)
3. Usa form "Novo plano" para criar plans com preço e limites
4. Clica em "Ver histórico" para ver todas as mudanças (timeline completa)
5. Página de histórico permite filtrar por plano e ver valor antes/depois

### Item 3: Faturamento

Fluxo:
1. Admin vai para `/app/admin/faturamento`
2. Vê métricas rápidas (sucessos, falhas, reembolsos)
3. Filtra por status (sucesso/pendente/falha) ou provider
4. Vê tabela completa com org, plano, valor, provedor e event_id

## Próximos passos (opcional)

- [ ] Criar webhook Stripe para popular `billing_events` em tempo real
- [ ] Email notifications em charge_failed com retry automático
- [ ] Invoice PDF generation para histórico de faturamento
- [ ] Gráficos de MRR over time
- [ ] Export de histórico de planos para CSV/Excel

## Notas

- Todas as três páginas seguem padrão: server component + RLS queries + admin guard
- Sidebar atualizado para chamar atenção: `/app/admin` e sub-pages
- Plan changes auditadas automaticamente, mudanças não salvas sem registro
- Histórico imutável (append-only log pattern)

## Atualização 2026-03-30 (UX Admin Usuários)

**Objetivo:** corrigir navegação do menu de ações por usuário no admin quando o dropdown ficava fora da viewport e parecia “bloqueado”.

**Arquivos impactados:**
- `web/src/app/app/admin/usuarios/_components/user-action-menu.tsx`

**Decisões aplicadas:**
- Posicionamento inteligente do menu com base na altura real renderizada (abre acima quando necessário).
- Clamp lateral/vertical para manter o menu sempre dentro da viewport.
- `maxHeight` dinâmico com rolagem interna para evitar corte em telas menores.
- Quando não há organização vinculada, esconder ações dependentes (`Trocar plano`, `Gerenciar vínculo`) e exibir apenas o caminho correto (`Criar organização e vincular`).

**Resultado validado:**
- Usuário sem org: menu mostra ação clara de criação de organização.
- Usuário com org: opções de plano e vínculo aparecem ativas e navegáveis.

## Atualização 2026-03-30 (Trial 7 dias + Bloqueio por plano)

**Objetivo:** aplicar regra de negócio prioritária para usuários autenticados: trial grátis de 7 dias no cadastro, acesso ao sistema liberado, mas bloqueio dos módulos críticos sem plano ativo.

**Arquivos impactados:**
- `backend/app/services/auth.py`
- `web/src/lib/subscription-access.ts`
- `web/src/components/app/plan-gate-card.tsx`
- `web/src/app/app/assinatura/page.tsx`
- `web/src/app/app/layout.tsx`
- `web/src/components/app/app-sidebar.tsx`
- `web/src/app/app/operacoes/page.tsx`
- `web/src/app/app/parametros/page.tsx`
- `web/src/app/app/auditoria/page.tsx`
- `web/src/app/app/estudos/page.tsx`
- `web/src/app/app/dashboard/page.tsx`

**Decisões aplicadas:**
- Signup agora cria assinatura `trialing` com `trial_ends_at` em +7 dias para a organização recém-criada (plano starter/fallback ativo).
- Regra centralizada em helper (`getSubscriptionAccess`) para evitar validações duplicadas e divergentes.
- Módulos bloqueados sem plano ativo: Operações, Parâmetros, Auditoria e Estudos.
- Usuário continua acessando Dashboard, Instalação e nova rota de Assinatura.
- Sidebar direciona módulos bloqueados para `/app/assinatura` e sinaliza estado bloqueado.

**Observações:**
- Checkout ainda não está integrado; página `/app/assinatura` mostra catálogo e estado atual, com ativação via suporte enquanto gateway não entra em produção.

## Atualização 2026-03-30 (Menu Configurações do Usuário)

**Objetivo:** criar área de configurações self-service para dados pessoais, segurança, assinatura e conta.

**Arquivos impactados:**
- `supabase/migrations/20260330_add_user_profile_settings_fields.sql`
- `web/src/app/app/configuracoes/page.tsx`
- `web/src/app/app/configuracoes/actions.ts`
- `web/src/components/app/app-sidebar.tsx`

**Entregas:**
- Menu lateral com rota de Configurações.
- Perfil: nome completo, foto (avatar_url), telefone, endereço completo, documento (CPF/RG).
- Validação de CPF no backend com marcação `document_verified`.
- Segurança: troca de email e senha.
- Assinatura: ver plano atual, trocar plano/ciclo e cancelar plano.
- Conta: exclusão de conta com confirmação explícita (`EXCLUIR`).

**Observações técnicas:**
- Novos campos de perfil exigem aplicar migration no banco antes do uso em produção.
- Alteração de email/senha usa `supabase.auth.updateUser` no contexto do usuário autenticado.

## Atualização 2026-03-30 (Configurações: Avatar por Upload + Ajustes React)

**Objetivo:** concluir o fluxo de foto de perfil conforme requisito de produto (upload de arquivo, não URL manual) e eliminar warnings de formulário/controlado na tela.

**Arquivos impactados:**
- `web/src/app/app/configuracoes/actions.ts`
- `web/src/app/app/configuracoes/page.tsx`

**Decisões aplicadas:**
- Removido o uso de URL textual para avatar no formulário de perfil.
- Criada action dedicada para upload de avatar com validação de tipo (`jpg`, `jpeg`, `png`, `webp`) e tamanho (até 5MB).
- Upload realizado no Supabase Storage (bucket configurável por env, fallback `profile-avatars`) e atualização de `avatar_url` no `user_profiles`.
- Campo de email exibido com `defaultValue` (somente leitura), evitando warning de input controlado em render server.
- Form com server action sem `encType` manual para evitar warning de compatibilidade no React/Next.

**Riscos e observações:**
- Necessário garantir existência do bucket de avatar no Storage (`profile-avatars`) e policies adequadas para o fluxo autenticado.
- Em ambientes sem bucket criado, upload retornará erro de backend até a configuração ser concluída.

**Próximos passos:**
- Validar no ambiente alvo: upload de avatar, persistência em `avatar_url` e renderização do preview após refresh.
