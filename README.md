# Vuno Trader

Plataforma SaaS de robo trader com execucao no MT5, cerebro externo em Python, backend FastAPI, frontend Next.js e persistencia no Supabase.

## Estrutura

- `web/`: app web (Next.js)
- `backend/`: API e workers (FastAPI)
- `supabase/`: migrations e estrutura de banco
- `scripts/`: automacoes locais (CDP, setup, utilitarios)
- `projeto/`: documentos de arquitetura e planejamento
- `evolucao/`: historico tecnico das decisoes e mudancas
- `vunotrader_brain.py`: servico de decisao do robo

## Requisitos

- Python 3.11+
- Node.js 20+
- Conta Supabase
- Terminal MetaTrader 5 instalado no Windows para integracao local

## Setup rapido

### Backend

1. Entrar em `backend/`
2. Criar e ativar ambiente virtual
3. Instalar dependencias de `backend/requirements.txt`
4. Configurar `backend/.env`
5. Rodar API

### Frontend

1. Entrar em `web/`
2. Instalar dependencias
3. Rodar app de desenvolvimento

### Brain Python

1. Configurar `brain.env` a partir de `brain.env.example`
2. Instalar dependencias de `brain-requirements.txt`
3. Executar `vunotrader_brain.py`

### Bot Python direto no MT5

O projeto agora inclui `scripts/mt5_cmd_bot.py`, um CLI para rodar no CMD e controlar o terminal MetaTrader 5 direto pelo Python.

Fluxo:
- conecta no MT5 local via pacote `MetaTrader5`
- consulta status, cotacao e posicoes
- envia ordens a mercado
- fecha posicoes
- pode rodar uma estrategia simples em loop

Observacao importante:
- esse script e paralelo ao fluxo principal `EA MQ5 -> Python Brain -> Supabase`
- ele nao substitui a rastreabilidade do Vuno e nao grava decisoes no backend

Exemplos de uso:

```bash
python scripts/mt5_cmd_bot.py status
python scripts/mt5_cmd_bot.py quote --symbol EURUSD
python scripts/mt5_cmd_bot.py buy --symbol EURUSD --volume 0.10 --sl-points 200 --tp-points 400
python scripts/mt5_cmd_bot.py positions --symbol EURUSD
python scripts/mt5_cmd_bot.py close --ticket 123456789
python scripts/mt5_cmd_bot.py run-strategy --symbol EURUSD --volume 0.10 --timeframe M5 --dry-run
python scripts/mt5_cmd_bot.py scan-markets --symbols EURUSD,GBPUSD,USDJPY,XAUUSD --timeframe M5 --top 3
python scripts/mt5_cmd_bot.py run-autonomy --symbols EURUSD,GBPUSD,USDJPY,XAUUSD --timeframe M5 --volume 0.01 --dry-run
```

Comandos avancados para autonomia:
- `scan-markets`: varre ativos, classifica contexto (tendencia/lateral/volatil), filtra baixo volume e ranqueia melhor entrada.
- `run-autonomy`: roda em loop, escolhe o melhor ativo por ciclo e executa ordem (ou simula com `--dry-run`).
- aprendizado local por ativo/timeframe em `autonomy_symbol_memory.json` para priorizacao adaptativa.

Variaveis opcionais em `brain.env`:
- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`
- `MT5_PATH`
- `MT5_TIMEOUT_MS`
- `MT5_MAGIC`
- `MT5_DEVIATION`
- `MT5_TIMEFRAME`

## Publicacao no GitHub

Este repositorio ja inclui regras de ignore para evitar envio de credenciais locais (`*.env`) e artefatos de build/venv.