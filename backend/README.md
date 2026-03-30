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

## Observacoes de seguranca

- service role key somente no backend
- publishable key somente no frontend
- usar RLS obrigatoriamente nas tabelas multi-tenant
- nunca expor credenciais em codigo versionado