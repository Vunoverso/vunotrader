-- =============================================================
-- Migration 000006: Controles de risco dinâmico + consistência
-- 2026-03-30
--
-- Adiciona campos a user_parameters para proteção automática:
--   max_consecutive_losses  → para operações após N perdas seguidas
--   drawdown_pause_pct      → pausa quando drawdown diário atinge X%
--   auto_reduce_risk        → reduz risco automaticamente ao perder consistência
--
-- Adiciona regime ao market_snapshots já existente (era nullable)
-- =============================================================

-- Campos de proteção dinâmica (todos opcionais, brain valida)
alter table public.user_parameters
  add column if not exists max_consecutive_losses int default 3,
  add column if not exists drawdown_pause_pct numeric(7, 3) default 5.0,
  add column if not exists auto_reduce_risk boolean default true;

-- Índice para busca rápida de user_parameters por user_id
create index if not exists idx_user_parameters_user_id
  on public.user_parameters(user_id);

-- Campo regime com check explícito (market_snapshots já tem coluna regime text)
-- Não modifica estrutura, apenas documenta valores esperados:
-- 'tendencia', 'lateral', 'volatil'
comment on column public.market_snapshots.regime is
  'Regime de mercado calculado pelo brain: tendencia | lateral | volatil';

-- Campo rationale indexado para busca textual básica em trade_decisions
create index if not exists idx_trade_decisions_rationale_pattern
  on public.trade_decisions using gin(to_tsvector('portuguese', coalesce(rationale, '')));
