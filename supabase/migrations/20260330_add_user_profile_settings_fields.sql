alter table public.user_profiles
  add column if not exists phone text,
  add column if not exists address_line1 text,
  add column if not exists address_line2 text,
  add column if not exists city text,
  add column if not exists state text,
  add column if not exists postal_code text,
  add column if not exists country text default 'BR',
  add column if not exists document_type text,
  add column if not exists document_value text,
  add column if not exists document_verified boolean not null default false;

alter table public.user_profiles
  drop constraint if exists user_profiles_document_type_check;

alter table public.user_profiles
  add constraint user_profiles_document_type_check
  check (document_type is null or document_type in ('cpf', 'rg'));

create index if not exists idx_user_profiles_document_value on public.user_profiles (document_value);
