-- ============================================================
-- Migration 000010 – Memoria global agregada (admin-only)
-- ============================================================
-- Objetivo:
-- - Criar camada de agregacao global anonima para cruzar configuracoes
-- - Permitir leitura somente para platform admin
-- - Escrita via service role (scripts internos)
-- ============================================================

create or replace function public.is_platform_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.user_profiles up
    where up.auth_user_id = auth.uid()
      and coalesce(up.is_platform_admin, false) = true
  );
$$;

create table if not exists public.global_memory_signals (
  id uuid primary key default gen_random_uuid(),
  symbol text not null,
  timeframe text not null,
  regime text not null,
  side text not null check (side in ('buy', 'sell', 'hold')),
  mode text not null check (mode in ('observer', 'demo', 'real')),
  config_fingerprint text not null,
  sample_size int not null default 0,
  wins int not null default 0,
  losses int not null default 0,
  breakevens int not null default 0,
  win_rate numeric(7,4),
  avg_pnl_points numeric(14,4),
  avg_confidence numeric(7,4),
  avg_risk_pct numeric(7,4),
  last_event_at timestamptz,
  computed_at timestamptz not null default now(),
  raw_stats jsonb,
  unique (symbol, timeframe, regime, side, mode, config_fingerprint)
);

create index if not exists idx_global_memory_signals_lookup
  on public.global_memory_signals (symbol, timeframe, regime, side, mode, sample_size desc);

create index if not exists idx_global_memory_signals_computed_at
  on public.global_memory_signals (computed_at desc);

alter table public.global_memory_signals enable row level security;
alter table public.global_memory_signals force row level security;

drop policy if exists global_memory_signals_admin_select on public.global_memory_signals;
create policy global_memory_signals_admin_select on public.global_memory_signals
  for select to authenticated
  using (public.is_platform_admin());

comment on table public.global_memory_signals is
  'Memoria global anonima agregada para otimizar configuracoes sem expor tenants.';
