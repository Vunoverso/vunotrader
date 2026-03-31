-- Migration 000008: Tabela lessons_learned
-- 2026-03-30
--
-- Armazena lições geradas automaticamente pelo brain após análise
-- de N resultados acumulados por robô. Alimenta o módulo de estudos
-- e o painel de evolução de estratégia.

create table if not exists public.lessons_learned (
  id               uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references public.organizations(id) on delete cascade,
  robot_instance_id uuid references public.robot_instances(id) on delete set null,
  user_id          uuid not null references public.user_profiles(id) on delete cascade,

  -- Período analisado
  period_start     timestamptz not null,
  period_end       timestamptz not null,

  -- Conteúdo da lição
  title            text not null,
  summary          text not null,
  regime           text,          -- tendencia | lateral | volatil | mixed
  category         text not null default 'general',
  -- Categorias: general | entry_timing | risk_management | regime_mismatch | overconfidence

  -- Métricas do período analisado
  total_trades     int not null default 0,
  win_rate         numeric(5, 2) not null default 0,
  avg_confidence   numeric(5, 3) not null default 0,
  total_pnl        numeric(12, 2) not null default 0,

  -- Contexto raw para pesquisa futura
  raw_stats        jsonb,

  generated_by     text not null default 'brain_auto',  -- brain_auto | admin_manual
  created_at       timestamptz not null default now()
);

create index if not exists idx_lessons_learned_org_robot
  on public.lessons_learned (organization_id, robot_instance_id, created_at desc);

create index if not exists idx_lessons_learned_user
  on public.lessons_learned (user_id, created_at desc);

create index if not exists idx_lessons_learned_regime
  on public.lessons_learned (regime, category);

alter table public.lessons_learned enable row level security;

drop policy if exists lessons_learned_org_policy on public.lessons_learned;
create policy lessons_learned_org_policy on public.lessons_learned
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));
