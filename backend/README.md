# Vuno Trader Backend

Backend FastAPI para auth, multi-tenant, seguranca e APIs de dominio do ecossistema Vuno Trader.

## Stack

- FastAPI
- Supabase Auth
- Supabase Postgres

## Funcionalidades iniciais

- signup com criacao de organizacao padrao
- login por email e senha
- refresh de sessao
- recuperacao de senha
- update de senha
- endpoint de usuario autenticado
- middleware de seguranca
- CORS e trusted hosts

## Estrutura

- app/main.py
- app/core/config.py
- app/core/dependencies.py
- app/core/security.py
- app/core/supabase.py
- app/services/auth.py
- app/api/routes/auth.py
- app/api/routes/account.py

## Variaveis de ambiente

Use [backend/.env.example](.env.example) como base.

## Instalar

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Rodar

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Worker de estudos

Processa materiais pendentes de `study_materials`, extrai texto de PDF e gera resumo heuristico.

Executar um ciclo:

```powershell
cd backend
python -m app.workers.study_ingestion_worker --once
```

Executar em loop:

```powershell
cd backend
python -m app.workers.study_ingestion_worker
```

Variaveis opcionais:

- `STUDY_BUCKET` (padrao: `training-videos`)
- `STUDY_WORKER_POLL_SECONDS` (padrao: `30`)
- `STUDY_WORKER_BATCH_SIZE` (padrao: `10`)

## Endpoints iniciais

- POST /api/auth/signup
- POST /api/auth/login
- POST /api/auth/refresh
- POST /api/auth/recover
- POST /api/auth/update-password
- GET /api/account/me
- GET /api/health

## Dependencias de banco

Executar as migracoes do Supabase nesta ordem:

1. [supabase/migrations/20260329_000001_initial_trader_schema.sql](../supabase/migrations/20260329_000001_initial_trader_schema.sql)
2. [supabase/migrations/20260329_000002_auth_security.sql](../supabase/migrations/20260329_000002_auth_security.sql)

## Deploy em Railway

### Pre-requisitos

1. Conta Railway: https://railway.app
2. Projeto conectado ao GitHub (push automático dispara deploy)
3. Variáveis de ambiente settings (Railway Dashboard)

### Configuração

Railway lê automaticamente:
- **Procfile** - define processos (web, worker)
- **Dockerfile** - container multi-stage otimizado
- **railway.toml** - config avançada (opcional)

### Variáveis de Ambiente (Railway Dashboard)

Adicionar no Railway:

```
SUPABASE_URL=https://mztrtovhjododrkzkehk.supabase.co
SUPABASE_ANON_KEY=sb_publishable_...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
SUPABASE_JWT_SECRET=your_jwt_secret

APP_ENV=production
APP_DEBUG=false
APP_ALLOWED_ORIGINS=https://vunotrader.vercel.app,https://vunotrader-*.vercel.app
APP_TRUSTED_HOSTS=*
```

### Deploy

1. Conectar GitHub repo ao Railway
2. Apontar para pasta `backend/` como root
3. Deixar Railway detectar Node.js e Python automaticamente
4. Railway fará auto-deploy em cada push em `main`

### Monitorar

- Railway Dashboard: logs em tempo real
- `/api/health` deve retornar 200 OK
- Logs indicam status do worker de estudos

## Observacoes de seguranca

- service role key somente no backend
- publishable key somente no frontend
- usar RLS obrigatoriamente nas tabelas multi-tenant
- nunca expor credenciais em codigo versionado
- Railway suporta secrets (não expor em arquivo .env)