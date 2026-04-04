# Habilidade: Nova Página ou Rota

## Quando usar
Criar uma nova página dentro de `/app/app/` no projeto Vuno Trader.

## Estrutura obrigatória

Toda página nova segue este padrão:

```
/app/app/nome-da-pagina/
├── page.tsx          → Server Component (busca dados)
├── NomeForm.tsx      → Client Component (se tiver formulário)
└── NomePanel.tsx     → Client Component adicional (se precisar)
```

## Checklist da página

- [ ] `page.tsx` é Server Component (sem `"use client"`)
- [ ] Busca `tenant_id` via `profiles` com `auth.getUser()`
- [ ] Tem `<header>` com `<h1>` e `<p>` de descrição
- [ ] Tem estado empty quando não há dados
- [ ] Sections com `aria-label` descritivo
- [ ] Máximo 200 linhas — extrair se passar

## Template base

```tsx
import { createServerSupabase } from '@/lib/supabase-server'

export default async function NomePage() {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null

  const { data: profile } = await supabase
    .from('profiles')
    .select('tenant_id')
    .eq('id', user.id)
    .single()

  const tenantId = profile?.tenant_id

  // buscar dados aqui...

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-xl font-semibold text-zinc-100">Título</h1>
        <p className="text-sm text-zinc-500 mt-1">Descrição curta</p>
      </header>

      <section aria-label="Descrição da seção">
        {/* conteúdo ou <EmptyState /> */}
      </section>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-12 text-center border border-zinc-800 border-dashed rounded-lg">
      <p className="text-sm text-zinc-600">{message}</p>
    </div>
  )
}
```

## Adicionar na sidebar

Editar `src/components/layout/Sidebar.tsx`, array `NAV`:

```ts
const NAV = [
  { href: '/app/dashboard',   label: 'Dashboard',   icon: '▦' },
  { href: '/app/operacoes',   label: 'Operações',   icon: '↕' },
  { href: '/app/parametros',  label: 'Parâmetros',  icon: '⚙' },
  { href: '/app/nova-pagina', label: 'Nova Página', icon: '◈' }, // adicionar aqui
]
```

## Páginas já existentes (não recriar)

- `/app/dashboard` — status, métricas, últimas decisões
- `/app/operacoes` — tabela de trades + auditoria
- `/app/parametros` — risco + token do robô
