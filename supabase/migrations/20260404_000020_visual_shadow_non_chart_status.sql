-- Formaliza status visual para ciclos fora do grafico anexado.

alter table if exists public.trade_visual_contexts
  drop constraint if exists trade_visual_contexts_visual_shadow_status_check;

alter table if exists public.trade_visual_contexts
  add constraint trade_visual_contexts_visual_shadow_status_check
  check (visual_shadow_status in ('pending', 'processed', 'error', 'skipped', 'skipped_non_chart_symbol'));