Data: 2026-04-03

## Objetivo

Mapear exatamente quais arquivos do projeto importado `robotrademeta5` devem ser portados primeiro para a base atual e executar a primeira extracao segura da camada SaaS, sem tocar no motor de decisao do Vuno.

## Arquivos fonte que valem portar primeiro

### Bloco 1 - Assinatura e gating basico

- `robotrademeta5/supabase/migrations/20260329_000001_initial_trader_schema.sql`
  - portar apenas o recorte de `saas_plans` e `saas_subscriptions`
- `robotrademeta5/backend/app/services/auth.py`
  - reaproveitar a ideia de trial inicial no onboarding
- `robotrademeta5/web/src/lib/subscription-access.ts`
  - reaproveitar a logica de leitura do acesso por assinatura, adaptada ao backend atual
- `robotrademeta5/web/src/app/app/assinatura/page.tsx`
  - servir de base para a tela futura de assinatura
- `robotrademeta5/web/src/components/app/plan-gate-card.tsx`
  - servir de base para bloqueio visual de modulos pagos

### Bloco 2 - Admin de catalogo e faturamento

- `robotrademeta5/web/src/app/app/admin/planos/page.tsx`
- `robotrademeta5/web/src/app/app/admin/faturamento/page.tsx`
- `robotrademeta5/supabase/migrations/20260330_create_plan_changes_table.sql`

Esses arquivos devem entrar apenas depois de consolidar o schema minimo de assinatura e a tela basica de planos.

### Bloco 3 - Web app autenticado e middleware

- `robotrademeta5/web/src/middleware.ts`
- `robotrademeta5/web/src/app/app/layout.tsx`
- `robotrademeta5/web/src/app/app/dashboard/page.tsx`

Esses arquivos so fazem sentido quando a base atual migrar do painel estatico para uma app web dedicada.

## Mapeamento executado nesta etapa

Arquivos fonte relevantes:

- `robotrademeta5/supabase/migrations/20260329_000001_initial_trader_schema.sql`
- `robotrademeta5/backend/app/services/auth.py`
- `robotrademeta5/web/src/lib/subscription-access.ts`

Arquivos de destino criados ou ajustados na base atual:

- `backend/migrations/sqlite/0010_saas_plans_and_subscriptions.sql`
- `backend/migrations/postgres/0010_saas_plans_and_subscriptions.sql`
- `backend/app/subscription_store.py`
- `backend/app/routes/subscription.py`
- `backend/app/routes/auth.py`
- `backend/app/main.py`
- `backend/tests/test_subscription_saas.py`

## Decisao tomada

Foi escolhida como primeira extracao a fundacao de assinatura no backend atual:

- catalogo local de planos
- assinatura por tenant
- trial automatico ao registrar tenant novo
- endpoint de leitura do catalogo
- endpoint de leitura do acesso atual da assinatura

Motivo da escolha:

- resolve uma lacuna real da base atual
- nao altera o motor de decisao
- prepara o terreno para gating de modulos e futura tela de assinatura
- permite portar depois UI, admin e faturamento em etapas pequenas

## Alternativas descartadas nesta etapa

- portar primeiro as telas admin de planos e faturamento: descartado porque a base atual ainda nao tinha o schema minimo de assinatura
- portar diretamente o middleware e o layout Next.js: descartado porque a interface atual ainda e esttica e a migracao de frontend precisa ser separada da fundacao de dados
- portar checkout ou cobranca real agora: descartado porque o foco desta fase e estrutura, nao integracao com gateway

## Riscos e observacoes

- o banco local ja possuia historico antigo com `schema_migrations.version = 0008` apontando para outro tema; por isso a migration nova entrou como `0010_saas_plans_and_subscriptions.sql`
- a camada nova ainda e read-only no ponto de vista do usuario; a ativacao e troca de plano virao em etapa posterior
- a logica atual usa `tenant_id` em vez de `organization_id`, porque essa e a unidade real da base atual

## Validacao executada

- smoke test com `TestClient` validando:
  - cadastro
  - login
  - `/api/subscription/plans`
  - `/api/subscription/access`
- teste automatizado novo aprovado:
  - `backend/tests/test_subscription_saas.py`
- regressao operacional aprovada:
  - `backend/tests/test_operational_flow.py`

## Proximos passos

1. adicionar uma leitura de assinatura no painel atual para expor trial, plano e bloqueios
2. portar uma versao minima de `plan-gate-card` para bloquear modulos nao liberados
3. introduzir tabela de limites do plano antes de portar admin de catalogo
4. planejar a migracao do frontend estatico para uma app web dedicada, reaproveitando `middleware.ts` e as paginas do importado