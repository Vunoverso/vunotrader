# Habilidade: Banco de Dados Supabase

## Quando usar
Criar, editar ou revisar queries, migrações ou lógica de acesso ao banco no Vuno Trader.

## Regras absolutas

1. **Toda query filtra por `tenant_id`** — sem exceção.
2. Nunca usar `service role` no frontend.
3. Nunca interpolação de string em SQL — sempre queries parametrizadas.
4. RLS ativo em todas as tabelas. Nunca desativar.
5. Frontend usa apenas `anon key`.

## Tabelas disponíveis

| Tabela | Campos principais |
|---|---|
| `profiles` | `id`, `tenant_id`, `name`, `email`, `plan` |
| `robot_instances` | `id`, `tenant_id`, `token`, `label`, `mode`, `last_heartbeat` |
| `user_parameters` | `tenant_id`, `risk_per_trade`, `stop_loss`, `take_profit`, `max_consecutive_loss`, `pause_on_drawdown`, `mode` |
| `trade_decisions` | `id`, `tenant_id`, `robot_id`, `signal`, `confidence`, `rationale`, `regime`, `ai_cost`, `mode` |
| `trade_results` | `id`, `tenant_id`, `decision_id`, `symbol`, `direction`, `lot_size`, `open_price`, `close_price`, `profit`, `status` |

## Padrão de leitura — Server Component

```ts
const supabase = await createServerSupabase()
const { data: { user } } = await supabase.auth.getUser()

const { data: profile } = await supabase
  .from('profiles')
  .select('tenant_id')
  .eq('id', user!.id)
  .single()

const { data } = await supabase
  .from('trade_decisions')
  .select('*')
  .eq('tenant_id', profile!.tenant_id)
  .order('created_at', { ascending: false })
  .limit(50)
```

## Padrão de escrita — Client Component

```ts
const supabase = createClient()

const { error } = await supabase
  .from('user_parameters')
  .upsert({
    tenant_id: tenantId,   // sempre incluir
    risk_per_trade: 1.5,
    updated_at: new Date().toISOString(),
  })
```

## Busca paralela (quando precisar de múltiplas tabelas)

```ts
const [decisionsRes, resultsRes] = await Promise.all([
  supabase.from('trade_decisions').select('*').eq('tenant_id', tenantId),
  supabase.from('trade_results').select('*').eq('tenant_id', tenantId),
])

const decisions = decisionsRes.data ?? []
const results = resultsRes.data ?? []
```

## Nova migração SQL

Sempre incluir:
1. `enable row level security`
2. Policy com `tenant_id` do usuário autenticado
3. Index em `(tenant_id, created_at desc)` para tabelas com volume

```sql
create table public.nova_tabela (
  id         uuid primary key default uuid_generate_v4(),
  tenant_id  uuid not null references public.profiles(tenant_id),
  -- campos...
  created_at timestamptz not null default now()
);

alter table public.nova_tabela enable row level security;

create policy "nova_tabela: somente tenant"
  on public.nova_tabela for all
  using (
    tenant_id = (select tenant_id from public.profiles where id = auth.uid())
  );

create index nova_tabela_tenant_created
  on public.nova_tabela(tenant_id, created_at desc);
```
