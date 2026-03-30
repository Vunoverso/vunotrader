-- Pipeline de ingestao de estudos: status de processamento + chunks para RAG

alter table if exists public.study_materials
  add column if not exists processing_status text
    check (processing_status in ('pending', 'processing', 'processed', 'error'))
    default 'pending';

alter table if exists public.study_materials
  add column if not exists processing_error text;

alter table if exists public.study_materials
  add column if not exists processed_at timestamptz;

alter table if exists public.study_materials
  add column if not exists updated_at timestamptz default now();

create index if not exists idx_study_materials_processing_status
  on public.study_materials (processing_status, created_at desc);

update public.study_materials
set
  processing_status = case
    when coalesce(summary, '') <> '' and coalesce(extracted_text, '') <> '' then 'processed'
    else 'pending'
  end,
  processed_at = case
    when coalesce(summary, '') <> '' and coalesce(extracted_text, '') <> '' then coalesce(processed_at, now())
    else processed_at
  end
where processing_status is null;

create table if not exists public.study_material_chunks (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  material_id uuid not null references public.study_materials(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  summary text,
  semantic_keywords text[],
  embedding jsonb,
  token_estimate int,
  created_at timestamptz not null default now(),
  unique (material_id, chunk_index)
);

create index if not exists idx_study_material_chunks_material
  on public.study_material_chunks (material_id, chunk_index);

create index if not exists idx_study_material_chunks_org
  on public.study_material_chunks (organization_id, created_at desc);

alter table public.study_material_chunks enable row level security;

drop policy if exists study_material_chunks_org_policy on public.study_material_chunks;
create policy study_material_chunks_org_policy on public.study_material_chunks
  for all to authenticated
  using (public.is_org_member(organization_id))
  with check (public.is_org_member(organization_id, array['owner','admin','analyst']));
