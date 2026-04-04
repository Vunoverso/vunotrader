# Evolucao - Bloco 4 (Qualidade e CI)

Data: 2026-04-03

## Objetivo

- implantar testes automatizados no backend
- padronizar execucao local de qualidade
- ativar pipeline CI para evitar regressao

## Entregas

1. Suite de testes (pytest)
- `backend/tests/conftest.py`: fixture com ambiente isolado SQLite por teste
- `backend/tests/test_auth.py`:
  - ciclo auth (register/login/me/logout)
  - validacao de cookie HttpOnly
  - bloqueio por brute-force (`429`)
- `backend/tests/test_operational_flow.py`:
  - fluxo demo de instancia + heartbeat + decisao + feedback + summary
- `backend/tests/test_migrations.py`:
  - idempotencia das migracoes

2. Ferramental local
- `backend/requirements-dev.txt` com `pytest`
- `backend/pytest.ini`
- `backend/run-tests.ps1` para install + compile + pytest

3. CI GitHub Actions
- `/.github/workflows/backend-ci.yml`
- gatilhos: `push` em `main/master` e `pull_request`
- pipeline: setup python -> install deps -> compileall -> pytest

4. Documentacao
- README atualizado com instrucoes de execucao dos testes e CI

## Validacao

- testes executados localmente com sucesso
- compileall do backend e tools sem erros

