# Vuno Web — Instruções de Desenvolvimento Frontend

## Stack

- **Next.js 16** (App Router), **React 19**, **TypeScript 5**, **Tailwind CSS v4**
- **`@supabase/ssr`** para sessão server-side; **`@supabase/supabase-js`** para client-side
- **framer-motion** para animações; sem outras libs de UI externas

---

## Limites por arquivo

| Tipo                      | Máximo       |
|---------------------------|--------------|
| Componente React          | 150 linhas   |
| Server Action / Route Handler | 80 linhas |
| Página (`page.tsx`)       | 100 linhas   |
| Hook customizado          | 80 linhas    |
| Utilitário (`lib/`)       | 120 linhas   |

Ultrapassou? **Extrair** em subcomponentes ou módulos separados.

---

## Estrutura de pastas

```
src/
  app/                   # App Router — rotas e layouts
    (public)/            # Rotas públicas (sem auth)
    app/                 # Rotas protegidas (/app/*)
      layout.tsx         # Valida sessão; redireciona se não autenticado
  components/
    ui/                  # Primitivos reutilizáveis (Button, Input, Badge...)
    layout/              # Header, Footer, Sidebar
    [feature]/           # Componentes de domínio agrupados por feature
  lib/
    supabase/            # client.ts, server.ts, middleware helper
    utils.ts             # helpers puros sem side effects
  middleware.ts          # Proteção de rotas
```

---

## Regras de componente

```tsx
// ✅ Server component por padrão
export default async function OperacoesPage() {
  const data = await fetchOperacoes()   // fetch direto no servidor
  return <OperacoesList items={data} />
}

// ✅ Client component apenas quando necessário
"use client"
export function FiltroAtivo({ onChange }: { onChange: (v: string) => void }) { ... }

// ❌ Nunca buscar dados dentro de client component
"use client"
export function MeuComponente() {
  useEffect(() => fetch('/api/...'), [])  // evitar
}
```

### Tipagem de props

```tsx
// ✅
interface CardProps {
  title: string
  value: number
  variant?: "success" | "danger" | "neutral"
}

// ❌ nunca
type CardProps = any
```

---

## Tailwind CSS v4 — Padrões de design

### Paleta (dark-first)

```
Fundo base:       bg-zinc-950
Superfície:       bg-zinc-900
Borda:            border-zinc-800  /  border-zinc-700/50
Texto primário:   text-zinc-100
Texto secundário: text-zinc-400
Destaque (verde): text-emerald-400  /  bg-emerald-500
Alerta (amarelo): text-amber-400
Perigo (vermelho):text-red-400
```

### Padrão de card

```tsx
<div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
  ...
</div>
```

### Padrão de botão primário

```tsx
<button
  type="button"
  className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium
             text-white transition-colors duration-200 hover:bg-emerald-500
             disabled:cursor-not-allowed disabled:opacity-50"
>
  Salvar
</button>
```

### Responsividade

- Mobile-first: escrever sem prefixo, ajustar com `sm:`, `md:`, `lg:`
- Grids: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`
- Nunca usar `px` fixo para espaçamento; usar escala Tailwind (`gap-4`, `p-6`)

---

## Semântica HTML obrigatória

```tsx
// ✅
<main>
  <section aria-labelledby="titulo-operacoes">
    <h2 id="titulo-operacoes">Operações</h2>
    <article>...</article>
  </section>
</main>

// Ícones sem label
<button type="button" aria-label="Fechar painel">
  <XIcon className="h-4 w-4" aria-hidden="true" />
</button>
```

---

## Loading e erro — padrão obrigatório

```
app/app/[feature]/
  page.tsx          # Conteúdo principal
  loading.tsx       # Skeleton enquanto carrega
  error.tsx         # Erro recuperável com botão de retry
  not-found.tsx     # 404 amigável
```

### Skeleton padrão

```tsx
export default function Loading() {
  return (
    <div className="space-y-3 p-6">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-lg bg-zinc-800" />
      ))}
    </div>
  )
}
```

---

## Segurança frontend

- **Nunca** usar `SUPABASE_SERVICE_ROLE_KEY` em componente ou rota do Next.js
- **Nunca** expor `process.env` sem prefixo `NEXT_PUBLIC_` no cliente
- **Sempre** validar retorno do Supabase antes de renderizar (`if (error) throw error`)
- **Sempre** usar `createServerClient` (SSR) para leitura de dados em Server Components
- XSS: nunca usar `dangerouslySetInnerHTML` com dados do usuário sem sanitização
- CSRF: Route Handlers de mutação validam `Content-Type: application/json`

---

## Middleware — proteção de rotas

```ts
// middleware.ts
export const config = { matcher: ["/app/:path*"] }

export async function middleware(request: NextRequest) {
  // Atualizar sessão SSR
  // Se sem sessão → redirect para /login
}
```

---

## Animações com framer-motion

```tsx
// Transição padrão de entrada
<motion.div
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2 }}
>
  ...
</motion.div>
```

Evitar animações em listas grandes (>50 itens); usar apenas em elementos focais.

---

## Convenções de nomenclatura

| Item              | Padrão           | Exemplo                   |
|-------------------|------------------|---------------------------|
| Arquivo de rota   | `kebab-case`     | `minhas-instancias/`      |
| Componente        | `PascalCase.tsx` | `RobotCard.tsx`           |
| Hook              | `use` + PascalCase | `useOperacoes.ts`       |
| Utilitário        | `kebab-case.ts`  | `format-currency.ts`      |
| Tipo/interface    | `PascalCase`     | `OperacaoRow`             |

---

## Proibições

- Sem `any` no TypeScript
- Sem `console.log` — usar `logger` de `lib/logger.ts`
- Sem `@apply` no Tailwind (exceto em `globals.css` para reset)
- Sem `!important` em nenhum CSS
- Sem instalação de lib de UI externa sem discussão prévia
- Sem inline styles (`style={{...}}`) exceto para valores dinâmicos impossíveis via Tailwind
