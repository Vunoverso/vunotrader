-- Migration 000011: adiciona controles operacionais por trade em user_parameters
-- 2026-03-31

alter table public.user_parameters
  add column if not exists per_trade_stop_loss_mode text,
  add column if not exists per_trade_stop_loss_value numeric(12, 3),
  add column if not exists per_trade_take_profit_rr numeric(7, 3);

update public.user_parameters
set per_trade_stop_loss_mode = 'atr'
where per_trade_stop_loss_mode is null;

alter table public.user_parameters
  alter column per_trade_stop_loss_mode set default 'atr';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'user_parameters_per_trade_stop_loss_mode_check'
  ) then
    alter table public.user_parameters
      add constraint user_parameters_per_trade_stop_loss_mode_check
      check (per_trade_stop_loss_mode in ('atr', 'fixed_points'));
  end if;
end $$;

comment on column public.user_parameters.per_trade_stop_loss_mode is
  'Modo de definicao do stop loss por operacao: atr ou fixed_points.';

comment on column public.user_parameters.per_trade_stop_loss_value is
  'Valor operacional do stop loss por trade. Em ATR quando mode=atr, ou em pontos quando mode=fixed_points.';

comment on column public.user_parameters.per_trade_take_profit_rr is
  'Relacao risco-retorno alvo por operacao. Ex.: 2.0 significa take profit em 2R.';