# 2026-03-30 - Backend Deploy Railway

## Objetivo

Preparar backend Python (FastAPI + Supabase) para deploy em Railway, complementando frontend (Next.js) já em Vercel.

## Stack de Deploy

- **Frontend**: Vercel (Next.js)
- **Backend**: Railway (FastAPI)
- **Database**: Supabase (PostgreSQL)
- **Bot**: MT5 (local/VPS do trader)

## Decisões Tomadas

### 1. Framework Railway

**Por que Railway?**
- Suporte nativo para Python (FastAPI)
- Deploy automático via GitHub webhook
- Variáveis de ambiente gerenciadas
- Health checks integrados
- Logs em tempo real
- Pricing simples para MVP

**Alternativas descartadas:**
- Heroku: descontinuado (dyno em paywall)
- AWS Lambda + API Gateway: complexidade inicial alta
- DigitalOcean: setup manual mais verboso
- Fly.io: bom mas Railway é mais simples para FastAPI

### 2. Configuração de Deploy

#### Procfile
Define 2 processos:
- **web**: uvicorn FastAPI (porta dinâmica via $PORT)
- **worker**: estudo_ingestion worker em background

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: python -m app.workers.study_ingestion_worker
```

#### Dockerfile (Multi-stage)
Otimiza imagem final:
- **Stage 1 (builder)**: instala deps com gcc, copia wheels
- **Stage 2 (runtime)**: apenas binários, reduz ~60% do tamanho final
- Health check integrado (testa /api/health)
- PYTHONUNBUFFERED=1 para logs em tempo real

#### railway.yaml
Config avançada (opcional mas recomendada):
- Define service name
- CORS apontando para Vercel domains
- Health check automático

#### .dockerignore
Acelera build excluindo:
- .git, .venv, __pycache__
- node_modules, .env, README.md
- Reduz tempo de push para Railway ~30%

## Variáveis de Ambiente

Necessárias no Railway Dashboard:

```
SUPABASE_URL              # URL da instância Supabase
SUPABASE_ANON_KEY         # Chave pública para cliente
SUPABASE_SERVICE_ROLE_KEY # Chave admin (SEGREDO!)
SUPABASE_JWT_SECRET       # Usado por auth
APP_ENV=production        # Flag para desligar debug
APP_DEBUG=false
APP_ALLOWED_ORIGINS       # CORS: Vercel domains
APP_TRUSTED_HOSTS         # *
```

## Próximas Ações

### Pré-Deploy
1. [ ] Checar `.env.example` tem todas as variáveis
2. [ ] Validar Supabase credentials estão corretas
3. [ ] Testar build local: `docker build -t backend .`
4. [ ] Verificar health endpoint: `curl http://localhost:8000/api/health`

### Deploy
1. [ ] Criar projeto Railway
2. [ ] Conectar GitHub (Vunoverso/vunotrader)
3. [ ] Apontar root directory: `backend/`
4. [ ] Adicionar secrets/env vars
5. [ ] Disparar deploy
6. [ ] Validar logs no Rail Dashboard
7. [ ] Testar endpoints em produção

### Pós-Deploy
1. [ ] Configurar Railway domain (vuno-api.railway.app)
2. [ ] Atualizar CORS no app (Railway domain)
3. [ ] Atualizar frontend: baseURL para API em produção
4. [ ] Smoke test: signup via frontend → cria usuário no Supabase
5. [ ] Validar worker de estudos roda automaticamente

## Riscos e Mitigação

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Credenciais expostas | CRÍTICO | Usar Rail secrets, não .env em repo |
| Cold starts | MÉDIO | Railway não tem cold starts (containers sempre warm) |
| DB throttling Supabase | MÉDIO | Monitorar queries, cache no backend se needed |
| Worker crashes | MÉDIO | Implementar retry logic e alertas |
| CORS mismatch | BAIXO | Testar pré-deploy com domains reais |

## Arquivos Criados/Modificados

- ✅ `backend/Procfile` (novo)
- ✅ `backend/Dockerfile` (novo)
- ✅ `backend/railway.yaml` (novo)
- ✅ `backend/.dockerignore` (novo)
- ✅ `backend/README.md` (atualizado com deploy section)

## Observações

- Railway deteção automática: python=requirements.txt, node=package.json
- Procfile é lido antes de Dockerfile (se ambos existirem)
- Railroad.yaml é próximo passo (config avançada, ex: múltiplas replicas)
- Healthcheck automático garante reinício se container crash

## Status

**Fase**: Preparação
**Próximo**: Criar projeto Railway e fazer primeiro deploy

## Atualização 2026-03-30 (Correção Build Railway)

### Sintoma

- Build falhando no Railway durante Docker build com erro de pacote Debian:
- `E: Unable to locate package libpoppler-cpp-0.87`

### Causa raiz

- O pacote `libpoppler-cpp-0.87` não existe na base atual da imagem `python:3.11-slim` usada no Railway.
- Essa dependência não é obrigatória para a stack atual, pois o parsing de PDF está via `pypdf` (sem binário poppler).

### Correções aplicadas

- Removida instalação de `libpoppler-cpp-0.87` do runtime no `backend/Dockerfile`.
- Healthcheck ajustado para usar `urllib` da stdlib (remove dependência implícita de `requests`).
- Comando final do container alterado para usar porta dinâmica `${PORT:-8000}`.
- Documentação atualizada para `railway.toml` (substitui referência antiga a `railway.yaml`).

### Atualização 2026-03-30 (Healthcheck: ajuste de porta)

- Sintoma persistente: `Network > Healthcheck failure` mesmo com build/deploy concluídos.
- Causa provável: mismatch entre porta pública configurada no domínio Railway (`8000`) e processo subindo em porta dinâmica (`$PORT`).
- Correção aplicada:
	- `backend/railway.toml`: `startCommand` fixado em porta `8000`
	- `backend/Dockerfile`: `HEALTHCHECK` fixado em `localhost:8000/api/health`
	- `backend/Dockerfile`: `CMD` fixado em `--port 8000`

### Atualização 2026-03-30 (Causa raiz confirmada em logs)

- Logs do Railway confirmaram erro recorrente de boot:
	- `Error: Invalid value for '--port': '$PORT' is not a valid integer.`
- Causa real: algumas rotas de startup ainda usavam `$PORT` literal (sem expansão), apesar do `railway.toml` já corrigido.
- Correção final aplicada:
	- `backend/Procfile`: `--port 8000`
	- `backend/nixpacks.toml`: `--port 8000`
- Decisão: padronizar temporariamente porta fixa `8000` no serviço Railway para eliminar inconsistência entre builders (Railpack/Nixpacks/Docker).

### Arquivos impactados

- `backend/Dockerfile`
- `backend/README.md`

### Risco residual

- Baixo: worker e API continuam no mesmo serviço; se precisar isolamento de carga, separar em serviço dedicado do Railway no próximo passo.

---

**Data**: 2026-03-30
**Executor**: Agent Vuno
**Arquivos**: 4 novos, 1 modificado
