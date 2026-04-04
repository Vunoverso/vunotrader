# Vuno Trader MVP

Base inicial para um sistema de trader com:

- login SaaS via site
- tenant e instÃ¢ncia do robÃ´
- parÃ¢metros operacionais por tenant
- agente local em Windows
- ponte por arquivos com MT5
- decisÃ£o remota por snapshot de mercado
- heartbeat operacional do robÃ´
- auditoria e status das instÃ¢ncias
- memÃ³ria local e memÃ³ria central para ajustes futuros

## Arquitetura resumida

1. O usuÃ¡rio acessa o site SaaS, cria conta em um tenant e gera um token da instÃ¢ncia do robÃ´.
2. O agente local roda na mÃ¡quina do usuÃ¡rio e usa esse token para autenticar.
3. O EA no MT5 gera snapshots de mercado em JSON numa pasta local comum.
4. O agente local envia heartbeat, lÃª os snapshots, envia ao backend e recebe um comando.
5. O agente local sincroniza runtime.settings.json para o MT5.
6. O EA aplica filtros locais de execuÃ§Ã£o e sÃ³ entÃ£o envia a ordem.

O snapshot do MT5 agora carrega tambem serie de candles fechados do timeframe operacional e do timeframe de confirmacao, preparando a migracao do motor para Price Action estruturado.

## Estrutura

- backend: API FastAPI + site de login SaaS
- agent-local: agente Python para instalaÃ§Ã£o local
- mt5: Expert Advisor MQL5 base
- projeto: documentaÃ§Ã£o arquitetural
- evolucao: registro tÃ©cnico de decisÃµes e prÃ³ximos passos

## Subir o backend

```powershell
cd backend
.\install.ps1
.\run-server.ps1
```

Abrir no navegador:

- http://127.0.0.1:8000

## Instalar o agente local

Fluxo recomendado no painel SaaS:

1. criar a instância em `Instancias`
2. clicar em `Baixar robo pronto` no card da última instância ou na linha da instância desejada
3. extrair o zip baixado
4. abrir `agent-local/iniciar-vuno-robo.cmd` com duplo clique

O pacote ja inclui:

- `runtime/config.json` preenchido com a chave da instância
- script para configurar a bridge automaticamente
- atalho para iniciar o agente sem terminal manual
- pasta `mt5/` com o EA e os modulos auxiliares
- `agent-local/dist/vuno-agent.exe` quando o build binario tiver sido gerado antes do deploy

Fluxo manual para desenvolvimento local:

```powershell
cd agent-local
.\install.ps1
```

Depois edite o arquivo `agent-local/runtime/config.json` com o campo `robot_token` gerado no site e execute:

```powershell
cd agent-local
.\run-agent.ps1
```

Para apontar a bridge para o MT5 real na pasta Common Files:

```powershell
cd agent-local
.\configure-mt5-bridge.ps1 -BridgeName VunoBridge
```

O script agora também prepara a pasta `metadata`, usada pelo EA para enviar ao painel o catálogo automático de símbolos do MT5.

## Fluxo MT5

1. Copiar `mt5/VunoRemoteBridge.mq5` e a pasta `mt5/vuno-bridge` para a pasta Experts do MT5.
2. Compilar o EA no MetaEditor.
3. Ajustar `InpBridgeRoot` para o mesmo nome configurado na bridge.
4. O timeframe operacional do snapshot e o timeframe do grafico onde o EA foi anexado.
5. Se quiser operar varios ativos a partir do mesmo EA, preencher `InpAdditionalSymbols` com os simbolos extras separados por virgula. Exemplo: `GBPUSD,XAUUSD,US30`.
6. Manter `InpAllowRealTrading = false` atÃ© homologar a instÃ¢ncia.
7. Anexar o EA ao grÃ¡fico principal desejado.
8. Garantir que o MT5 tenha permissÃ£o para escrita em arquivos comuns.
9. Depois do primeiro ciclo do EA, o painel passa a mostrar automaticamente o ativo principal, o timeframe do gráfico e os símbolos detectados no MT5 para aquela instância.

Observacao: os ativos extras usam o mesmo timeframe do grafico onde o EA foi anexado. Se quiser o mesmo ativo em timeframes diferentes, continue usando um grafico separado para cada timeframe.

Contrato atual do snapshot:

- `candles` e `htf_candles` contem apenas candles fechados
- os arrays seguem em ordem cronologica, do mais antigo para o mais recente
- o ultimo item do array e o candle fechado mais recente
- `close`, `ema_fast`, `ema_slow` e `rsi` representam o ultimo candle fechado

Guia detalhado para instÃ¢ncia real em [mt5/ligacao-mt5-real.md](mt5/ligacao-mt5-real.md).

## Controle operacional

Endpoints internos jÃ¡ disponÃ­veis:

- /api/parameters: leitura e atualizaÃ§Ã£o dos parÃ¢metros operacionais do tenant
- /api/robot-instances: criaÃ§Ã£o e consulta de status das instÃ¢ncias
- /api/audit-events: trilha recente de auditoria por tenant
- /api/agent/runtime-config: contrato operacional consumido pelo agente local

O agente local sincroniza para a pasta out do bridge:

- runtime.settings.json

Esse arquivo Ã© consumido pelo EA para aplicar:

- spread mÃ¡ximo
- lote base
- stop e take padrÃ£o
- limite de posiÃ§Ãµes por sÃ­mbolo
- respiro entre uma entrada e a prÃ³xima no mesmo ativo
- idade mÃ¡xima do comando
- desvio e retries de execuÃ§Ã£o
- pausa de novas ordens
- fallback local
- modo da instÃ¢ncia

## Limites atuais do MVP

- o motor remoto usa heurÃ­stica simples, nÃ£o IA pesada
- o aprendizado Ã© uma base inicial de memÃ³ria e feedback, nÃ£o treino automatizado
- o EA usa ponte por arquivo para reduzir complexidade e dependÃªncia externa
- a persistÃªncia central ainda usa SQLite local como bootstrap tÃ©cnico

## PrÃ³ximo incremento natural

- empacotar o agente local com PyInstaller
- adicionar painel SaaS de contas e planos
- incluir imagem de chart junto do snapshot JSON
- plugar um agente LLM remoto por MCP sobre o mesmo endpoint de decisÃ£o

## Frontend operacional (bootstrap local)

O painel em `http://127.0.0.1:8000` agora inclui:

- dashboard gerencial com decisoes, resultados, win rate, pnl e profit factor
- filtros de instancias por nome, modo e conectividade
- filtros de auditoria por tipo, robo e janela de tempo
- sessao com expiracao curta e logout com revogacao de token

## Endpoints adicionados/expandidos

- `POST /api/auth/logout`: revoga a sessao atual
- `GET /api/summary`: resumo operacional consolidado do tenant
- `GET /api/robot-instances`: aceita filtros `search`, `mode`, `status`, `online_window_seconds`
- `GET /api/audit-events`: aceita filtros `event_type`, `robot_instance_id`, `date_from`, `date_to`

## Seguranca de sessao

- login agora tambem seta cookie HttpOnly de sessao (`SESSION_COOKIE_NAME`)
- backend aceita sessao por cookie e tambem Bearer para compatibilidade
- protecao anti brute-force no login por IP+email com bloqueio temporario

## Producao e operacao

### Ambientes (dev/staging/prod)

Variaveis recomendadas no `backend/.env`:

```env
APP_ENV=production
SERVICE_NAME=vuno-trader-saas
SERVICE_VERSION=0.3.0
API_HOST=0.0.0.0
API_PORT=8000
UVICORN_WORKERS=2
```

`run-server.ps1` agora sobe:

- `development`: com `--reload`
- `staging/production`: sem `reload` e com `workers`

### Banco gerenciado (Postgres/Supabase)

O backend agora suporta dois drivers:

- `DB_DRIVER=sqlite` (padrao local)
- `DB_DRIVER=postgres` (gerenciado, ex: Supabase)

Exemplo para Postgres/Supabase:

```env
DB_DRIVER=postgres
DATABASE_URL=postgresql://postgres:senha@db.seu-projeto.supabase.co:5432/postgres
```

Para SQLite local:

```env
DB_DRIVER=sqlite
# SQLITE_DB_PATH=./runtime/vuno_saas.db
```

### Migracoes versionadas

As migracoes ficam em:

- `backend/migrations/sqlite/*.sql`
- `backend/migrations/postgres/*.sql`

Comandos:

```powershell
cd backend
.\migrate.ps1 status
.\migrate.ps1 up
```

O startup do backend tambem executa migracoes pendentes automaticamente.

### CORS

Defina `CORS_ALLOW_ORIGINS` no arquivo `backend/.env`, por exemplo:

```env
CORS_ALLOW_ORIGINS=https://painel.seudominio.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_MINUTES=15
LOGIN_BLOCK_MINUTES=20
```

Regras aplicadas:

- `staging/production` nao aceita `localhost`/`127.0.0.1` em CORS
- `production` aceita apenas origens `https://...`

### Logs e alertas

```env
LOG_LEVEL=INFO
LOG_JSON=true
REQUEST_LOG_EXCLUDE_PATHS=/api/health
ERROR_ALERT_WEBHOOK_URL=https://hooks.seu-alerta.com/...
ERROR_ALERT_TIMEOUT_SECONDS=2.5
```

- logs estruturados JSON com `request_id`, `path`, `status_code`, `duration_ms`
- header `X-Request-ID` em respostas
- excecoes 500 sao registradas no backend e podem disparar webhook de alerta

### Backup do SQLite

```powershell
cd backend
.\backup-db.ps1 -VerifyRestore
```

O mesmo comando funciona para Postgres/Supabase (usa `pg_dump`/`pg_restore` quando `DB_DRIVER=postgres`).

Para rodar backup automatico diario no Windows:

```powershell
cd backend
.\register-backup-task.ps1 -TaskName VunoTraderBackup -DailyAt 03:00 -RetentionDays 14 -VerifyRestore
```

### Empacotamento do agente local

```powershell
cd agent-local
.\build-agent.ps1
```

Quando `agent-local/dist/vuno-agent.exe` existir, o pacote baixado pelo painel vai anexar esse executavel automaticamente e `iniciar-vuno-robo.cmd` passara a usa-lo sem depender de Python na maquina do usuario.

## Qualidade (Bloco 4)

Testes automatizados do backend:

```powershell
cd backend
.\run-tests.ps1
```

Ou manual:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Cobertura atual de testes:

- auth/sessao por cookie + logout
- protecao anti brute-force
- fluxo demo (instancia, heartbeat, decisao, feedback, summary)
- migracoes (idempotencia)

CI no GitHub Actions:

- arquivo: `.github/workflows/backend-ci.yml`
- roda em `push` e `pull_request`
- etapas: install -> compileall -> pytest

