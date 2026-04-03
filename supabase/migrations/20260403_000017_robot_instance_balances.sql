-- Saldo inicial e saldo atual para sincronismo do heartbeat MT5 e KPIs do dashboard

alter table if exists public.robot_instances
  add column if not exists initial_balance numeric(14,2) not null default 0,
  add column if not exists current_balance numeric(14,2) not null default 0;

create index if not exists idx_robot_instances_last_seen_at
  on public.robot_instances (last_seen_at desc);
