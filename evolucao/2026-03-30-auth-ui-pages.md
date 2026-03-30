# 2026-03-30 — Páginas de Autenticação (Auth UI)

## Objetivo
Criar as telas de autenticação padrão de sistema SaaS: login, cadastro e recuperação de senha. Apenas UI — integração com Supabase Auth fica como próximo passo.

## Arquivos criados

| Arquivo | Rota | Descrição |
|---|---|---|
| `web/src/app/auth/layout.tsx` | `/auth/*` | Layout compartilhado: header mínimo com logo VT, footer com crédito Vuno Studio |
| `web/src/app/auth/login/page.tsx` | `/auth/login` | Formulário email + senha, link "Esqueceu a senha?", link para cadastro |
| `web/src/app/auth/cadastro/page.tsx` | `/auth/cadastro` | Nome, email, senha, confirmar senha, checkbox de aceite de Termos + Política |
| `web/src/app/auth/esqueceu-senha/page.tsx` | `/auth/esqueceu-senha` | Campo de e-mail, botão enviar, estado de confirmação com instrução ao usuário |

## Decisões tomadas

- **Apenas UI, sem chamada Supabase**: placeholder `TODO` marcado nas três páginas. A integração real com `supabase.auth.signIn`, `signUp` e `resetPasswordForEmail` será feita em etapa separada.
- **Client Components** (`"use client"`): necessário para estado do formulário (useState) e feedback dinâmico de loading/erro.
- **Validação client-side simples**: senha mínima 8 chars, confirmação de senha, e-mail com `@`, termos obrigatórios. Validação server-side virá com Supabase e middleware.
- **Checkbox de termos obrigatório**: botão "Criar conta" fica `disabled` até o checkbox estar marcado — uso de `accent-sky-600` para consistência visual.
- **Estado "sent"** na esqueceu-senha: após submit simulado, exibe tela de confirmação com ícone de envelope, e-mail digitado repetido, instrução sobre spam e opção de "tentar novamente". Isso evita enumeration attack ao não confirmar se o e-mail existe.
- **Layout auth separado** do layout raiz: não carrega header/footer institucional, mantém logo mínimo e link de volta para `/`.
- **Rotas de termos e política** no cadastro apontam para `/termos` e `/politica-privacidade` (ainda 404 — páginas a criar).

## Atualização — 2026-03-30: Integração Supabase Auth

### Pacotes instalados
- `@supabase/supabase-js`
- `@supabase/ssr`

### Arquivos criados/alterados

| Arquivo | Ação |
|---|---|
| `web/.env.local` | Criado com `NEXT_PUBLIC_SUPABASE_URL` e `NEXT_PUBLIC_SUPABASE_ANON_KEY` (nunca usa service role no frontend) |
| `web/src/lib/supabase/client.ts` | `createBrowserClient` do `@supabase/ssr` para uso em Client Components |
| `web/src/middleware.ts` | Middleware Next.js com `createServerClient` — protege `/app/*` e redireciona usuário logado para fora das páginas auth |
| `web/src/app/auth/login/page.tsx` | Integrado com `supabase.auth.signInWithPassword` — redireciona para `/app/dashboard` após sucesso |
| `web/src/app/auth/cadastro/page.tsx` | Integrado com `supabase.auth.signUp` com metadata `full_name` — redireciona para `/auth/confirmar-email` |
| `web/src/app/auth/esqueceu-senha/page.tsx` | Integrado com `supabase.auth.resetPasswordForEmail` com `redirectTo` apontando para `/auth/redefinir-senha` |
| `web/src/app/auth/confirmar-email/page.tsx` | Página estática de confirmação pós-cadastro |
| `.gitignore` | Adicionado `web/.env.local` |

### Fluxo de auth implementado

```
/auth/cadastro → signUp → /auth/confirmar-email
(usuário clica no e-mail de confirmação)
→ Supabase redireciona → /auth/redefinir-senha (a criar) ou direto para login

/auth/login → signInWithPassword → /app/dashboard
/auth/esqueceu-senha → resetPasswordForEmail → tela "verifique e-mail"
```

### Pendências
- Página `/auth/redefinir-senha` (formulário de nova senha — recebe token via URL do Supabase)
- Integração do `full_name` com a tabela `user_profiles` (trigger já existe no banco)
- Página `/app/dashboard` ainda 404 — próximo módulo

