-- Runtime do shadow visual: bucket, lock de worker e metadata da imagem.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'mt5-visual-captures',
  'mt5-visual-captures',
  false,
  5242880,
  array['image/png']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

alter table if exists public.trade_visual_contexts
  add column if not exists chart_image_captured_at timestamptz,
  add column if not exists visual_worker_lock_owner text,
  add column if not exists visual_worker_locked_at timestamptz;

create index if not exists idx_trade_visual_contexts_lock_owner
  on public.trade_visual_contexts(robot_instance_id, cycle_id, visual_worker_locked_at desc);