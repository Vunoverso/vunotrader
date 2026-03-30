# Setup do Supabase

## O que ja foi preparado

- Configuracao MCP do projeto em [.vscode/mcp.json](../.vscode/mcp.json)
- Schema principal em [projeto/supabase_schema.sql](supabase_schema.sql)
- Script de auth e seguranca em [projeto/supabase_auth_security.sql](supabase_auth_security.sql)
- Migracao padrao do Supabase em [supabase/migrations/20260329_000001_initial_trader_schema.sql](../supabase/migrations/20260329_000001_initial_trader_schema.sql)
- Migracao de auth e RLS em [supabase/migrations/20260329_000002_auth_security.sql](../supabase/migrations/20260329_000002_auth_security.sql)

## O que falta para aplicar no projeto remoto

Para executar a migracao no Supabase remoto, ainda falta um destes acessos:

- service role key
- database password da conexao Postgres
- ou acesso manual ao SQL Editor do projeto

Com a publishable key nao da para aplicar schema administrativo.

## Formas de aplicar

### Opcao 1. SQL Editor do Supabase

1. Abrir o projeto Supabase.
2. Entrar no SQL Editor.
3. Executar primeiro [projeto/supabase_schema.sql](supabase_schema.sql).
4. Executar depois [projeto/supabase_auth_security.sql](supabase_auth_security.sql).

### Opcao 2. Supabase CLI

Se voce tiver o access token e o projeto linkado:

```powershell
supabase link --project-ref mztrtovhjododrkzkehk
supabase db push
```

### Opcao 3. psql direto no banco

Se voce tiver a senha do banco e a string de conexao:

```powershell
psql "postgresql://postgres:[SENHA]@db.mztrtovhjododrkzkehk.supabase.co:5432/postgres" -f "supabase/migrations/20260329_000001_initial_trader_schema.sql"
```

## Variaveis publicas do app

Para o frontend futuro, usar:

```env
NEXT_PUBLIC_SUPABASE_URL=https://mztrtovhjododrkzkehk.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_DEFAULT_KEY=definir_no_ambiente
```

## Observacoes

- Nao grave senha real em arquivo versionado.
- Use service role apenas no backend.
- A publishable key serve para cliente web e nao para migracao administrativa.