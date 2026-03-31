-- Migration 000007: Adiciona capital_usd em user_parameters
-- 2026-03-30
--
-- Necessário para calcular drawdown percentual:
--   drawdown_pause_pct (%) × capital_usd = limite de perda diária em dinheiro
--
-- Ex.: 5% × 10000 = R$ 500 de perda máxima no dia

alter table public.user_parameters
  add column if not exists capital_usd numeric(12, 2) default 10000.00;

comment on column public.user_parameters.capital_usd is
  'Capital de referência em USD/BRL para cálculo de drawdown percentual. Default: 10000.';
