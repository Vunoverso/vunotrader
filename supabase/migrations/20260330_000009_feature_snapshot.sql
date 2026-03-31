-- ============================================================
-- Migration 000009 – feature_snapshot em anonymized_trade_events
-- ============================================================
-- Objetivo: armazenar snapshot das features técnicas no momento
-- da decisão para uso no retreino do modelo ML.
--
-- Colunas adicionadas:
--   feature_snapshot jsonb  — indicadores técnicos (RSI, MACD,
--                             ATR%, BB width, etc.) no momento
--                             da decisão.
--   model_version    text   — versão/hash do modelo que gerou
--                             a decisão (rastreabilidade).
-- ============================================================

alter table public.anonymized_trade_events
  add column if not exists feature_snapshot jsonb,
  add column if not exists model_version    text;

comment on column public.anonymized_trade_events.feature_snapshot is
  'Snapshot das features técnicas no momento da decisão (RSI, MACD, ATR%, BB width, etc.). Usado para retreino supervisionado do modelo ML.';

comment on column public.anonymized_trade_events.model_version is
  'Versão ou hash do modelo ML que gerou a decisão. Permite rastrear evolução de qualidade entre versões.';

-- Índice GIN para buscas dentro do JSONB (feature engineering)
create index if not exists idx_ate_feature_snapshot
  on public.anonymized_trade_events using gin (feature_snapshot)
  where feature_snapshot is not null;
