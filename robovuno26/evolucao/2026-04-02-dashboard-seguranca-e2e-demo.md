# Evolucao - Dashboard Gerencial, Seguranca de Sessao e Validacao Demo E2E

Data: 2026-04-02

## Objetivo

Executar os proximos passos operacionais do sistema principal:

- validar fluxo ponta a ponta em demo
- fechar metricas reais de dashboard
- endurecer sessao (expiracao curta + logout com revogacao)
- melhorar UX com filtros operacionais
- preparar bootstrap para producao (backup e empacotamento)

## Arquivos impactados

- backend/app/models.py
- backend/app/deps.py
- backend/app/database.py
- backend/app/routes/auth.py
- backend/app/routes/monitoring.py
- backend/static/index.html
- backend/static/js/app.js
- backend/backup-db.ps1
- backend/.env.example
- agent-local/app/config.py
- agent-local/build-agent.ps1
- README.md

## Decisao

### 1) Backend de monitoramento e metricas

Foi adicionado `GET /api/summary` com agregacao por tenant (e filtro opcional por robot/date range):

- total de decisoes + distribuicao BUY/SELL/HOLD
- total de resultados + wins/losses
- win rate, pnl total, pnl medio e profit factor
- total de instancias e quantas estao online
- ultimos timestamps de decisao e resultado

`GET /api/robot-instances` passou a aceitar filtros:

- `search`
- `mode` (DEMO/REAL)
- `status` (all/online/offline)
- `online_window_seconds`

`GET /api/audit-events` passou a aceitar filtros:

- `event_type`
- `robot_instance_id`
- `date_from`
- `date_to`

### 2) Sessao mais segura

Foi adotado baseline de seguranca sem cookie HttpOnly (fase atual):

- expiracao curta de sessao (`SESSION_HOURS`, default 8)
- limpeza de sessoes expiradas no login
- revogacao de sessoes antigas do mesmo usuario no login
- novo endpoint `POST /api/auth/logout` para revogar token atual
- remocao de sessao expirada durante validacao de token

No frontend, o token saiu de `localStorage` para `sessionStorage` e o logout chama revogacao no backend.

### 3) UX operacional

Frontend bootstrap atualizado com:

- cards gerenciais no dashboard (decisoes, resultados, win rate, pnl, profit factor, online)
- filtros de instancias por nome/modo/conectividade
- status online/offline com idade do heartbeat (ha X min)
- filtros de auditoria por tipo, robo e janela de tempo

### 4) Producao bootstrap

- script de backup SQLite: `backend/backup-db.ps1`
- script de build do agente local com PyInstaller: `agent-local/build-agent.ps1`
- README atualizado com endpoints e operacao

### 5) Robustez de config do agente

`AgentConfig.load` agora aceita arquivo com BOM (`utf-8-sig`), evitando falha por encoding no `runtime/config.json`.

## Alternativas descartadas

- migrar imediatamente para cookie HttpOnly sem backend dedicado de sessao web: descartado nesta fase por custo de refatoracao do frontend estatico.
- manter dashboard sem endpoint consolidado: descartado por limitar visao gerencial.
- manter filtros so no cliente: descartado para nao transferir carga e para permitir paginacao/filtro server-side no futuro.

## Validacao executada

### Compilacao

- `python -m compileall -f backend/app agent-local/app`

### Fluxo ponta a ponta (demo)

1. cadastro e login via API
2. criacao de robot instance DEMO
3. escrita do token em `agent-local/runtime/config.json`
4. execucao do agente local por alguns segundos
5. confirmacao de heartbeat/status em `/api/robot-instances`
6. confirmacao de resumo em `/api/summary`
7. envio de decisao e feedback de trade para validar metricas reais

Resultados confirmados:

- instancia com `last_status=ACTIVE`
- `is_online=true` e `heartbeat_age_seconds` preenchido
- `summary` com `decisions_total=1`, `results_total=1`, `win_rate_pct=100.0`, `pnl_total=12.34`
- `POST /api/auth/logout` revogando token com sucesso

## Riscos e observacoes

- frontend bootstrap continua estatico; para sessao HttpOnly completa sera necessario fluxo server-rendered ou BFF.
- `trade_decisions` atual guarda sinal em JSON (`decision_payload`), por isso o resumo calcula BUY/SELL/HOLD via parse no backend.

## Proximos passos

1. adicionar endpoint de historico temporal de metricas (serie diaria)
2. mover token para cookie HttpOnly em frontend dedicado
3. preparar migracao de SQLite para banco gerenciado em producao
