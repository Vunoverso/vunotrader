-- Mecanismo de retry com backoff exponencial para ingestao de estudos

alter table if exists public.study_materials
  add column if not exists retry_count int default 0;

alter table if exists public.study_materials
  add column if not exists next_retry_at timestamptz;

alter table if exists public.study_materials
  add column if not exists last_error_at timestamptz;

-- Criar indice para melhorar query de pendentes considerando retry
create index if not exists idx_study_materials_retry_status
  on public.study_materials (processing_status, next_retry_at, created_at desc)
  where processing_status in ('pending', 'error');

-- Reset de campos de retry para materiais processados com sucesso
update public.study_materials
set
  retry_count = 0,
  next_retry_at = null,
  last_error_at = null
where processing_status = 'processed';
