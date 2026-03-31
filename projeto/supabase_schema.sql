-- Supabase schema inicial para o projeto trader
-- Ajuste tipos e constraints conforme evolucao do sistema

create extension if not exists pgcrypto;

create table if not exists user_profiles (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique,
  owner_profile_id uuid references user_profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists organization_members (
  organization_id uuid not null references organizations(id) on delete cascade,
  profile_id uuid not null references user_profiles(id) on delete cascade,
  role text not null check (role in ('owner', 'admin', 'analyst', 'viewer')),
  created_at timestamptz not null default now(),
  primary key (organization_id, profile_id)
);

create table if not exists saas_plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text,
  monthly_price numeric(14,2) not null default 0,
  yearly_price numeric(14,2),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists saas_plan_limits (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references saas_plans(id) on delete cascade,
  max_users int,
  max_trades_per_month int,
  max_ai_tokens_per_day int,
  max_storage_gb numeric(8,2),
  max_bots int,
  created_at timestamptz not null default now()
);

create table if not exists saas_subscriptions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  plan_id uuid not null references saas_plans(id),
  status text not null check (status in ('trialing', 'active', 'past_due', 'canceled', 'paused')),
  billing_cycle text not null check (billing_cycle in ('monthly', 'yearly')),
  current_period_start timestamptz,
  current_period_end timestamptz,
  trial_ends_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists billing_events (
  id uuid primary key default gen_random_uuid(),
  subscription_id uuid references saas_subscriptions(id) on delete set null,
  event_type text,
  amount numeric(14,2),
  currency text,
  provider text,
  provider_event_id text,
  payload jsonb,
  created_at timestamptz not null default now()
);

create table if not exists strategies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists model_versions (
  id uuid primary key default gen_random_uuid(),
  strategy_id uuid references strategies(id),
  version_name text not null,
  mode text not null check (mode in ('observer', 'demo', 'real')),
  metrics jsonb,
  is_active boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists user_parameters (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  user_id text not null,
  mode text not null check (mode in ('observer', 'demo', 'real')),
  capital_usd numeric(12,2) default 10000.00,
  daily_profit_target numeric(14,2),
  weekly_profit_target numeric(14,2),
  monthly_profit_target numeric(14,2),
  daily_loss_limit numeric(14,2),
  max_drawdown_pct numeric(7,3),
  risk_per_trade_pct numeric(7,3),
  per_trade_stop_loss_mode text check (per_trade_stop_loss_mode in ('atr', 'fixed_points')) default 'atr',
  per_trade_stop_loss_value numeric(12,3),
  per_trade_take_profit_rr numeric(7,3),
  max_trades_per_day int,
  trading_start_time time,
  trading_end_time time,
  allowed_symbols text[],
  max_consecutive_losses int default 3,
  drawdown_pause_pct numeric(7,3) default 5.0,
  auto_reduce_risk boolean default true,
  updated_at timestamptz not null default now()
);

create table if not exists robot_instances (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  profile_id uuid not null references user_profiles(id) on delete cascade,
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

create table if not exists market_snapshots (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  symbol text not null,
  timeframe text not null,
  regime text,
  spread numeric(12,6),
  volatility numeric(14,6),
  indicators jsonb,
  captured_at timestamptz not null default now()
);

create table if not exists trade_decisions (
  id uuid primary key default gen_random_uuid(),
  trade_id text not null unique,
  organization_id uuid references organizations(id) on delete cascade,
  user_id text,
  robot_instance_id uuid references robot_instances(id) on delete set null,
  mode text not null check (mode in ('observer', 'demo', 'real')),
  strategy_id uuid references strategies(id),
  model_version_id uuid references model_versions(id),
  snapshot_id uuid references market_snapshots(id),
  symbol text not null,
  timeframe text not null,
  side text not null check (side in ('buy', 'sell', 'hold')),
  confidence numeric(7,4),
  risk_pct numeric(7,3),
  score numeric(10,4),
  rationale text,
  created_at timestamptz not null default now()
);

create table if not exists executed_trades (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  robot_instance_id uuid references robot_instances(id) on delete set null,
  trade_decision_id uuid not null references trade_decisions(id) on delete cascade,
  broker_ticket text,
  entry_price numeric(14,6),
  stop_loss numeric(14,6),
  take_profit numeric(14,6),
  lot numeric(12,4),
  opened_at timestamptz,
  closed_at timestamptz,
  status text check (status in ('open', 'closed', 'canceled')),
  created_at timestamptz not null default now()
);

create table if not exists trade_outcomes (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  robot_instance_id uuid references robot_instances(id) on delete set null,
  executed_trade_id uuid not null references executed_trades(id) on delete cascade,
  result text not null check (result in ('win', 'loss', 'breakeven')),
  pnl_money numeric(14,2),
  pnl_points numeric(14,2),
  win_loss_reason text,
  post_analysis text,
  created_at timestamptz not null default now()
);

create table if not exists ai_usage_logs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  robot_instance_id uuid references robot_instances(id) on delete set null,
  trade_decision_id uuid references trade_decisions(id) on delete set null,
  user_id text,
  provider text,
  model_name text,
  prompt_tokens int,
  completion_tokens int,
  total_tokens int,
  estimated_cost numeric(14,6),
  task_type text,
  created_at timestamptz not null default now()
);

create table if not exists study_materials (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  user_id text,
  material_type text not null check (material_type in ('video_url', 'pdf', 'note')),
  title text not null,
  source_url text,
  storage_path text,
  processing_status text not null default 'pending' check (processing_status in ('pending', 'processing', 'processed', 'error')),
  processing_error text,
  summary text,
  extracted_text text,
  processed_at timestamptz,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table if not exists study_material_chunks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  material_id uuid not null references study_materials(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  summary text,
  semantic_keywords text[],
  embedding jsonb,
  token_estimate int,
  created_at timestamptz not null default now(),
  unique (material_id, chunk_index)
);

create table if not exists study_tags (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists study_material_tags (
  material_id uuid not null references study_materials(id) on delete cascade,
  tag_id uuid not null references study_tags(id) on delete cascade,
  primary key (material_id, tag_id)
);

create table if not exists media_assets (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  trade_decision_id uuid references trade_decisions(id) on delete set null,
  material_id uuid references study_materials(id) on delete set null,
  asset_type text not null check (asset_type in ('screenshot', 'video_frame', 'pdf_page', 'other')),
  storage_path text not null,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create table if not exists lessons_learned (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid references organizations(id) on delete cascade,
  trade_outcome_id uuid references trade_outcomes(id) on delete set null,
  strategy_id uuid references strategies(id) on delete set null,
  lesson_type text,
  title text,
  description text,
  confidence numeric(7,4),
  created_at timestamptz not null default now()
);

create table if not exists anonymized_trade_events (
  id uuid primary key default gen_random_uuid(),
  source_trade_decision_id uuid references trade_decisions(id) on delete set null,
  source_trade_outcome_id uuid references trade_outcomes(id) on delete set null,
  anonymous_user_hash text not null,
  anonymous_org_hash text,
  mode text,
  symbol text,
  timeframe text,
  side text,
  confidence numeric(7,4),
  risk_pct numeric(7,3),
  score numeric(10,4),
  result text,
  pnl_points numeric(14,2),
  volatility numeric(14,6),
  regime text,
  feature_vector jsonb,
  rationale_redacted text,
  loss_win_reason_redacted text,
  consent_scope text,
  created_at timestamptz not null default now()
);

create index if not exists idx_trade_decisions_user_created
  on trade_decisions(user_id, created_at desc);

create index if not exists idx_trade_decisions_org_created
  on trade_decisions(organization_id, created_at desc);

create index if not exists idx_trade_decisions_symbol_timeframe
  on trade_decisions(symbol, timeframe, created_at desc);

create index if not exists idx_trade_outcomes_result_created
  on trade_outcomes(result, created_at desc);

create index if not exists idx_ai_usage_logs_user_created
  on ai_usage_logs(user_id, created_at desc);

create index if not exists idx_ai_usage_logs_org_created
  on ai_usage_logs(organization_id, created_at desc);

create index if not exists idx_study_materials_user_created
  on study_materials(user_id, created_at desc);

create index if not exists idx_study_materials_processing_status
  on study_materials(processing_status, created_at desc);

create index if not exists idx_study_material_chunks_material
  on study_material_chunks(material_id, chunk_index);

create index if not exists idx_organization_members_profile
  on organization_members(profile_id);

create index if not exists idx_saas_subscriptions_org_status
  on saas_subscriptions(organization_id, status);

create index if not exists idx_anonymized_trade_events_created
  on anonymized_trade_events(created_at desc);
