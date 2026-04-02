-- 2026-04-02 - Coleta de ciclos do scanner para aprendizado supervisionado

create table if not exists public.scanner_cycle_logs (
  id uuid primary key default gen_random_uuid(),
  cycle_id text not null,
  cycle_ts timestamptz not null,
  mode text not null default 'demo',
  symbol text not null,
  timeframe text not null,
  signal text not null default 'HOLD',
  decision_status text not null default 'analyzed',
  decision_reason text,
  block_reason text,
  confidence double precision not null default 0,
  risk_pct double precision not null default 0,
  regime text,
  score double precision not null default 0,
  spread_points double precision not null default 0,
  atr_pct double precision not null default 0,
  volume_ratio double precision not null default 0,
  rsi double precision not null default 0,
  momentum_20 double precision not null default 0,
  decision_id uuid,
  executed boolean not null default false,
  broker_ticket text,
  result text,
  pnl_money double precision not null default 0,
  pnl_points double precision not null default 0,
  user_id uuid,
  organization_id uuid,
  robot_instance_id uuid,
  feature_hash text,
  created_at timestamptz not null default now()
);

create index if not exists idx_scanner_cycle_logs_cycle_ts on public.scanner_cycle_logs (cycle_ts desc);
create index if not exists idx_scanner_cycle_logs_symbol_tf on public.scanner_cycle_logs (symbol, timeframe);
create index if not exists idx_scanner_cycle_logs_status on public.scanner_cycle_logs (decision_status, executed, result);
create unique index if not exists uq_scanner_cycle_logs_cycle_id_symbol_tf on public.scanner_cycle_logs (cycle_id, symbol, timeframe);

alter table public.scanner_cycle_logs enable row level security;

-- Service role mantém acesso total. Usuário autenticado acessa apenas dados da própria organização.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'scanner_cycle_logs'
      and policyname = 'scanner_cycle_logs_select_org'
  ) then
    create policy scanner_cycle_logs_select_org
      on public.scanner_cycle_logs
      for select
      to authenticated
      using (
        organization_id in (
          select up.organization_id
          from public.user_profiles up
          where up.user_id = auth.uid()
        )
      );
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'scanner_cycle_logs'
      and policyname = 'scanner_cycle_logs_insert_service'
  ) then
    create policy scanner_cycle_logs_insert_service
      on public.scanner_cycle_logs
      for insert
      to service_role
      with check (true);
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'scanner_cycle_logs'
      and policyname = 'scanner_cycle_logs_update_service'
  ) then
    create policy scanner_cycle_logs_update_service
      on public.scanner_cycle_logs
      for update
      to service_role
      using (true)
      with check (true);
  end if;
end $$;
