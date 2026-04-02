# 2026-04-02 - Scanner: contrato de ciclo, painel no EA e loop de aprendizado local

## Objetivo

Fechar o contrato mínimo do ciclo de análise do scanner para que o projeto tenha uma linha única entre:

- análise local do motor
- painel visual no EA MT5
- persistência local/remota dos ciclos
- retreino supervisionado com outcome real

## Arquivos impactados

- `VunoScreener_v3.mq5`
- `backend/app/api/routes/mt5.py`
- `backend/app/core/signal_engine.py`
- `scripts/mt5_cmd_bot.py`
- `vuno_core/cycle_collector.py`
- `vuno_core/__init__.py`
- `retrain_pipeline.py`
- `supabase/migrations/20260402_000016_scanner_cycle_logs.sql`

## Decisão tomada

### 1. Contrato de ciclo orientado a estado

Foi adotado um fluxo simples e rastreável para o ciclo do scanner:

- `analyzed`
- `blocked`
- `picked`
- `executed`
- `closed`

A decisão foi evitar um design mais complexo com múltiplas tabelas e eventos fragmentados antes de provar a utilidade do loop local.

### 2. Coleta local primeiro, Supabase opcional

Foi criado `CycleCollector` para persistir ciclos em:

- CSV local (`scanner_cycle_logs.csv`)
- Supabase (`scanner_cycle_logs`), quando configurado

Isso permite validar o aprendizado em shadow/local mesmo sem depender do ambiente remoto.

## Atualização do mesmo dia - persistência online no fluxo cloud

Foi fechada a lacuna do caminho online:

- `backend/app/api/routes/mt5.py` agora grava `scanner_cycle_logs` no endpoint `/api/mt5/signal`
- o backend atualiza o mesmo ciclo para `executed` em `/api/mt5/trade-opened`
- o backend fecha o ciclo com `result`, `pnl_money` e `pnl_points` em `/api/mt5/trade-outcome`
- `backend/app/core/signal_engine.py` passou a expor `score`, `atr_pct`, `volume_ratio`, `rsi` e `momentum_20` para enriquecer o ciclo no modo cloud
- `VunoScreener_v3.mq5` passou a notificar `trade-opened` e `trade-outcome` nas rotas corretas do backend

Com isso, a tabela `scanner_cycle_logs` deixa de ser exclusiva do fluxo local e passa a receber também o caminho Render + EA.

### 3. Painel do EA baseado em estado real

O `VunoScreener_v3.mq5` ganhou painel `ChartComment()` com dados objetivos:

- status do motor
- modo efetivo
- ciclo e hora
- humor derivado de confiança + risco + PnL
- saldo, equity, pico, PnL diário, drawdown
- posições abertas
- leitura por ativo com sinal, estado, confiança, score, motivo de bloqueio
- contexto líder com `regime`, spread, ATR e rationale

O painel não usa texto fictício; ele reflete dados reais da análise e do backend.

### 4. Treino só com outcome fechado

O `retrain_pipeline.py` passou a consumir:

- `anonymized_trade_events`
- `scanner_cycle_logs` do Supabase
- `scanner_cycle_logs.csv` local

Mas apenas quando o ciclo está:

- `decision_status = closed`
- `executed = true`
- `result` conhecido

Com isso, `blocked` e `analyzed` continuam úteis para auditoria, mas não contaminam o dataset supervisionado.

### 5. Persistência do scaler alinhada ao motor compartilhado

O pipeline agora salva:

- `brain_model_rf.pkl`
- `brain_model_gb.pkl`
- `brain_model_scaler.pkl`

Isso mantém consistência com `vuno_core/decision_engine.py`, evitando mismatch entre treino e inferência.

## Riscos e observações

- O painel atual é funcional e orientado à decisão; ainda não busca a estética ASCII avançada do protótipo de referência.
- O score do painel do EA é calculado localmente a partir de confiança, ATR e spread para manter independência do backend.
- Como houve novas alterações após o push já realizado, será necessário um novo push/deploy para o caminho online começar a persistir ciclos na tabela nova.

## Próximos passos

1. Aplicar a migration `20260402_000016_scanner_cycle_logs.sql` no Supabase remoto.
2. Fazer novo push para publicar a persistência online no backend/EA.
3. Expor os ciclos e motivos de bloqueio na auditoria web.
4. Adicionar métricas de calibração (`analyzed -> executed -> closed`) no dashboard.
5. Se o painel do EA agradar visualmente, evoluir layout ASCII sem mudar o contrato de dados.
