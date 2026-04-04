# Habilidade: Componente React

## Quando usar
Criar, editar ou revisar componentes React no projeto Vuno Trader.

## Regras obrigatórias

- Server Component por padrão. Usar `"use client"` só se precisar de hook ou interatividade.
- Props sempre tipadas com `interface`, nunca `type`.
- Sem `any`. Usar tipos de `src/types/index.ts`.
- Máximo 200 linhas. Se passar, extrair subcomponente ou hook.
- Nomes de arquivo em `kebab-case`. Componente em `PascalCase`.
- `<button type="button">` para ações. `<a>` só para navegação.
- `aria-label` obrigatório em ícones sem texto visível.
- Estados obrigatórios em toda tela crítica: loading, empty, error.

## Estrutura padrão — Server Component

```tsx
import { createServerSupabase } from '@/lib/supabase-server'
import type { MinhaEntidade } from '@/types'

export default async function MeuComponente() {
  const supabase = await createServerSupabase()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null

  const { data: profile } = await supabase
    .from('profiles')
    .select('tenant_id')
    .eq('id', user.id)
    .single()

  const { data } = await supabase
    .from('minha_tabela')
    .select('*')
    .eq('tenant_id', profile?.tenant_id)

  return (
    <section aria-label="...">
      {/* conteúdo */}
    </section>
  )
}
```

## Estrutura padrão — Client Component

```tsx
'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase-client'

interface Props {
  tenantId: string
}

export default function MeuForm({ tenantId }: Props) {
  const supabase = createClient()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    // ...
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit}>
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={loading}>
        {loading ? 'Aguarde...' : 'Salvar'}
      </button>
    </form>
  )
}
```

## Componentes UI disponíveis

- `<SignalBadge signal="BUY" />` — badge BUY/SELL/HOLD
- `<StatusDot online={true} />` — indicador verde/cinza

## Tailwind

- Dark-first: `bg-zinc-900`, `text-zinc-100`, `border-zinc-800`
- Dados numéricos: classe `mono` (IBM Plex Mono)
- Transições: `transition-colors duration-150`
- Mobile-first com `sm:` `md:` `lg:`
