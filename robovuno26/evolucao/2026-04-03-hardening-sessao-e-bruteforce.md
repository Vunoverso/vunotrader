# Evolucao - Hardening de Sessao e Protecao Anti Brute-Force

Data: 2026-04-03

## Objetivo

Aplicar o bloco de seguranca prioritario:

- sessao por cookie HttpOnly
- suporte a logout com limpeza de cookie
- protecao anti brute-force no login

## Mudancas aplicadas

1. Sessao cookie-first
- `POST /api/auth/login` agora seta cookie HttpOnly de sessao.
- `get_session_context` aceita token por cookie e por Bearer (compatibilidade).
- `POST /api/auth/logout` revoga sessao e remove cookie.

2. Brute-force
- tabela `login_attempts` para controle por `email+ip`.
- janela configuravel de tentativas e bloqueio temporario:
  - `LOGIN_MAX_ATTEMPTS`
  - `LOGIN_WINDOW_MINUTES`
  - `LOGIN_BLOCK_MINUTES`
- retorno `429` com `Retry-After` quando bloqueado.

3. Frontend
- requests com `credentials: "include"`.
- frontend deixou de depender de token em `Authorization`.
- sessao restaurada por cookie no bootstrap.

4. CORS
- `allow_credentials=True` habilitado no middleware CORS.

## Arquivos alterados

- `backend/app/deps.py`
- `backend/app/routes/auth.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/static/js/app.js`
- `backend/.env.example`
- `README.md`

## Validacao executada

- compilacao Python do backend sem erros
- login com cookie e `GET /api/auth/me` sem Bearer: OK
- logout invalidando sessao: OK
- bloqueio anti brute-force apos tentativas invalidas: OK (`429` + `Retry-After`)

