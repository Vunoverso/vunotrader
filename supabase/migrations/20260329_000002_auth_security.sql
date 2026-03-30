-- Fonte original: projeto/supabase_auth_security.sql

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.user_profiles (auth_user_id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'full_name', '')
  )
  on conflict (auth_user_id) do update
    set email = excluded.email,
        full_name = excluded.full_name,
        updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.is_org_member(org_id uuid, allowed_roles text[] default array['owner','admin','analyst','viewer'])
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.organization_members om
    join public.user_profiles up on up.id = om.profile_id
    where om.organization_id = org_id
      and up.auth_user_id = auth.uid()
      and om.role = any(allowed_roles)
  );
$$;

alter table public.user_profiles enable row level security;
alter table public.organizations enable row level security;
alter table public.organization_members enable row level security;
alter table public.user_parameters enable row level security;
alter table public.market_snapshots enable row level security;
alter table public.trade_decisions enable row level security;
alter table public.executed_trades enable row level security;
alter table public.trade_outcomes enable row level security;
alter table public.ai_usage_logs enable row level security;
alter table public.study_materials enable row level security;
alter table public.media_assets enable row level security;
alter table public.lessons_learned enable row level security;

alter table public.user_profiles force row level security;
alter table public.organizations force row level security;
alter table public.organization_members force row level security;
alter table public.user_parameters force row level security;
alter table public.market_snapshots force row level security;
alter table public.trade_decisions force row level security;
alter table public.executed_trades force row level security;
alter table public.trade_outcomes force row level security;
alter table public.ai_usage_logs force row level security;
alter table public.study_materials force row level security;
alter table public.media_assets force row level security;
alter table public.lessons_learned force row level security;

drop policy if exists user_profiles_select_own on public.user_profiles;
create policy user_profiles_select_own on public.user_profiles
  for select to authenticated
  using (auth.uid() = auth_user_id);

drop policy if exists user_profiles_update_own on public.user_profiles;
create policy user_profiles_update_own on public.user_profiles
  for update to authenticated
  using (auth.uid() = auth_user_id)
  with check (auth.uid() = auth_user_id);

drop policy if exists organizations_select_member on public.organizations;
create policy organizations_select_member on public.organizations
  for select to authenticated
  using (public.is_org_member(id));

drop policy if exists organizations_manage_owner_admin on public.organizations;
create policy organizations_manage_owner_admin on public.organizations
  for all to authenticated
  using (public.is_org_member(id, array['owner','admin']))
  with check (public.is_org_member(id, array['owner','admin']));

drop policy if exists organization_members_select_member on public.organization_members;
create policy organization_members_select_member on public.organization_members
  for select to authenticated
  using (public.is_org_member(organization_id));

drop policy if exists organization_members_manage_owner_admin on public.organization_members;
create policy organization_members_manage_owner_admin on public.organization_members
  for all to authenticated
  using (public.is_org_member(organization_id, array['owner','admin']))
  with check (public.is_org_member(organization_id, array['owner','admin']));

drop policy if exists user_parameters_org_policy on public.user_parameters;
create policy user_parameters_org_policy on public.user_parameters
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists market_snapshots_org_policy on public.market_snapshots;
create policy market_snapshots_org_policy on public.market_snapshots
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists trade_decisions_org_policy on public.trade_decisions;
create policy trade_decisions_org_policy on public.trade_decisions
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists executed_trades_org_policy on public.executed_trades;
create policy executed_trades_org_policy on public.executed_trades
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists trade_outcomes_org_policy on public.trade_outcomes;
create policy trade_outcomes_org_policy on public.trade_outcomes
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists ai_usage_logs_org_policy on public.ai_usage_logs;
create policy ai_usage_logs_org_policy on public.ai_usage_logs
  for select to authenticated
  using (public.is_org_member(organization_id));

drop policy if exists study_materials_org_policy on public.study_materials;
create policy study_materials_org_policy on public.study_materials
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists media_assets_org_policy on public.media_assets;
create policy media_assets_org_policy on public.media_assets
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));

drop policy if exists lessons_learned_org_policy on public.lessons_learned;
create policy lessons_learned_org_policy on public.lessons_learned
  for select to authenticated
  using (public.is_org_member(organization_id));

create index if not exists idx_user_parameters_organization_id on public.user_parameters (organization_id);
create index if not exists idx_market_snapshots_organization_id on public.market_snapshots (organization_id);
create index if not exists idx_trade_decisions_snapshot_id on public.trade_decisions (snapshot_id);
create index if not exists idx_trade_decisions_strategy_id on public.trade_decisions (strategy_id);
create index if not exists idx_trade_decisions_model_version_id on public.trade_decisions (model_version_id);
create index if not exists idx_executed_trades_trade_decision_id on public.executed_trades (trade_decision_id);
create index if not exists idx_executed_trades_organization_id on public.executed_trades (organization_id);
create index if not exists idx_trade_outcomes_executed_trade_id on public.trade_outcomes (executed_trade_id);
create index if not exists idx_trade_outcomes_organization_id on public.trade_outcomes (organization_id);
create index if not exists idx_ai_usage_logs_trade_decision_id on public.ai_usage_logs (trade_decision_id);
create index if not exists idx_study_materials_organization_id on public.study_materials (organization_id);
create index if not exists idx_media_assets_trade_decision_id on public.media_assets (trade_decision_id);
create index if not exists idx_media_assets_material_id on public.media_assets (material_id);
create index if not exists idx_lessons_learned_trade_outcome_id on public.lessons_learned (trade_outcome_id);
create index if not exists idx_lessons_learned_strategy_id on public.lessons_learned (strategy_id);

insert into public.saas_plans (code, name, description, monthly_price, yearly_price)
values
  ('starter', 'Starter', 'Plano inicial para validacao do robo', 99.00, 990.00),
  ('pro', 'Pro', 'Plano profissional com IA ampliada', 249.00, 2490.00),
  ('scale', 'Scale', 'Plano de escala com limites elevados', 599.00, 5990.00)
on conflict (code) do nothing;