# Evolucao - Bloco 2 (Producao e Observabilidade)

Data: 2026-04-03

## Objetivo

Aplicar itens do bloco 2:

- configuracao por ambiente (`development`, `staging`, `production`)
- CORS de producao mais restrito
- logs estruturados e rastreio de erros

## Mudancas

1. Config por ambiente
- novo modulo `backend/app/settings.py` com `load_settings()`
- valida `APP_ENV` e variaveis de operacao (`API_HOST`, `API_PORT`, `UVICORN_WORKERS`, etc.)

2. CORS seguro
- parse e validacao de `CORS_ALLOW_ORIGINS`
- bloqueia wildcard `*`
- em `staging/production` bloqueia `localhost/127.0.0.1`
- em `production` exige origens `https`

3. Logging estruturado e rastreabilidade
- novo modulo `backend/app/observability.py`
- logs JSON opcionais (`LOG_JSON`)
- middleware HTTP com:
  - `request_id` por requisicao (`X-Request-ID`)
  - status code e latencia (`duration_ms`)
  - nivel de log por classe de resposta (2xx info, 4xx warn, 5xx error)

4. Tratamento de excecao e alerta
- handler global de `Exception` retorna 500 padrao com `request_id`
- registra stack trace no backend
- envia alerta opcional para `ERROR_ALERT_WEBHOOK_URL` (best effort)

5. Startup e scripts
- `backend/app/main.py` usa settings + observability
- `backend/run-server.ps1`:
  - dev: `--reload`
  - staging/prod: sem reload, com workers

6. Documentacao
- `backend/.env.example` expandido com variaveis de ambiente/log/alerta
- README atualizado com secao de ambientes e observabilidade

## Validacao

- compilacao Python do backend: OK
- smoke test de auth/fluxo por cookie: OK
- validacao de brute-force continuou funcionando apos as mudancas

