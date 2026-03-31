-- Isolamento por instancia de robo (robot_instances) + vinculo em trilha de trades

create table if not exists public.robot_instances (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  profile_id uuid not null references public.user_profiles(id) on delete cascade,
  name text not null,
  robot_token_hash text not null,
  status text not null default 'active' check (status in ('active', 'paused', 'revoked')),
  allowed_modes text[] not null default array['demo'],
  real_trading_enabled boolean not null default false,
  max_risk_real numeric(7,3) not null default 1.500,
  last_seen_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, profile_id, name)
);

create unique index if not exists idx_robot_instances_token_hash
  on public.robot_instances (robot_token_hash);

create index if not exists idx_robot_instances_org_profile
  on public.robot_instances (organization_id, profile_id, created_at desc);

alter table if exists public.trade_decisions
  add column if not exists robot_instance_id uuid references public.robot_instances(id) on delete set null;

alter table if exists public.executed_trades
  add column if not exists robot_instance_id uuid references public.robot_instances(id) on delete set null;

alter table if exists public.trade_outcomes
  add column if not exists robot_instance_id uuid references public.robot_instances(id) on delete set null;

alter table if exists public.ai_usage_logs
  add column if not exists robot_instance_id uuid references public.robot_instances(id) on delete set null;

create index if not exists idx_trade_decisions_robot_instance
  on public.trade_decisions (robot_instance_id, created_at desc);

create index if not exists idx_executed_trades_robot_instance
  on public.executed_trades (robot_instance_id, created_at desc);

create index if not exists idx_trade_outcomes_robot_instance
  on public.trade_outcomes (robot_instance_id, created_at desc);

create index if not exists idx_ai_usage_logs_robot_instance
  on public.ai_usage_logs (robot_instance_id, created_at desc);

alter table public.robot_instances enable row level security;

drop policy if exists robot_instances_org_policy on public.robot_instances;
create policy robot_instances_org_policy on public.robot_instances
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));
