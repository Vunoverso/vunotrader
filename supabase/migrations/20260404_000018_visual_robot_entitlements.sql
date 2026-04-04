-- Entitlements SaaS e campos base do Robo Hibrido Visual.

create table if not exists public.saas_features (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text,
  scope text not null check (scope in ('product', 'ops', 'visual', 'admin')),
  default_enabled boolean not null default false,
  config_schema jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.saas_plan_features (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references public.saas_plans(id) on delete cascade,
  feature_id uuid not null references public.saas_features(id) on delete cascade,
  is_enabled boolean not null default true,
  config jsonb,
  created_at timestamptz not null default now(),
  unique (plan_id, feature_id)
);

create index if not exists idx_saas_plan_features_plan_id
  on public.saas_plan_features(plan_id);

create index if not exists idx_saas_plan_features_feature_id
  on public.saas_plan_features(feature_id);

insert into public.saas_features (code, name, description, scope, default_enabled)
values
  ('robot.integrated', 'Robo Integrado', 'Linha oficial com bridge local e execucao estruturada.', 'product', true),
  ('robot.visual_hybrid', 'Robo Hibrido Visual', 'Linha visual assistida com screenshot e leitura enriquecida.', 'visual', false),
  ('robot.visual_shadow', 'Shadow visual', 'Processamento visual em shadow mode para auditoria e comparacao.', 'visual', false),
  ('robot.visual_storage_extended', 'Retencao visual expandida', 'Retencao maior dos artefatos visuais e screenshots.', 'visual', false),
  ('robot.visual_compare', 'Comparativo visual', 'Comparativos avancados entre leitura estruturada e leitura visual.', 'visual', false),
  ('ops.desktop_recovery', 'Recuperacao desktop', 'Assistencia operacional para recuperacao e suporte remoto guiado.', 'ops', false)
on conflict (code) do nothing;

insert into public.saas_plan_features (plan_id, feature_id, is_enabled)
select p.id, f.id, true
from public.saas_plans p
join public.saas_features f
  on (
    (p.code = 'starter' and f.code in ('robot.integrated'))
    or (p.code = 'pro' and f.code in ('robot.integrated', 'robot.visual_hybrid', 'robot.visual_shadow'))
    or (p.code = 'scale' and f.code in (
      'robot.integrated',
      'robot.visual_hybrid',
      'robot.visual_shadow',
      'robot.visual_storage_extended',
      'robot.visual_compare',
      'ops.desktop_recovery'
    ))
  )
on conflict (plan_id, feature_id) do nothing;

alter table if exists public.robot_instances
  add column if not exists robot_product_type text not null default 'robo_integrado'
    check (robot_product_type in ('robo_integrado', 'robo_hibrido_visual', 'python_laboratorio')),
  add column if not exists visual_shadow_enabled boolean not null default false,
  add column if not exists computer_use_enabled boolean not null default false,
  add column if not exists human_approval_required boolean not null default false;

create index if not exists idx_robot_instances_product_type
  on public.robot_instances(robot_product_type, created_at desc);

create table if not exists public.trade_visual_contexts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  robot_instance_id uuid not null references public.robot_instances(id) on delete cascade,
  trade_decision_id uuid references public.trade_decisions(id) on delete set null,
  cycle_id text not null,
  chart_image_storage_path text,
  chart_image_hash text,
  visual_shadow_status text not null default 'pending'
    check (visual_shadow_status in ('pending', 'processed', 'error', 'skipped')),
  visual_context jsonb,
  visual_alignment text not null default 'not_applicable'
    check (visual_alignment in ('aligned', 'divergent_low', 'divergent_high', 'not_applicable', 'error')),
  visual_conflict_reason text,
  visual_model_version text,
  processed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (robot_instance_id, cycle_id)
);

create index if not exists idx_trade_visual_contexts_org_created
  on public.trade_visual_contexts(organization_id, created_at desc);

create index if not exists idx_trade_visual_contexts_robot_created
  on public.trade_visual_contexts(robot_instance_id, created_at desc);

alter table public.trade_visual_contexts enable row level security;
alter table public.trade_visual_contexts force row level security;

drop policy if exists trade_visual_contexts_org_policy on public.trade_visual_contexts;
create policy trade_visual_contexts_org_policy on public.trade_visual_contexts
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));