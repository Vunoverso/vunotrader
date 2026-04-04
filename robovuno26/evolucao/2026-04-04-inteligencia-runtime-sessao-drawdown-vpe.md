Data: 2026-04-04

# Sessao por ativo, drawdown hard stop e inteligencia de gestao VPE

## Objetivo

Atender o pedido de elevar a inteligencia operacional do robo sem trocar a arquitetura atual, cobrindo:

- sessao de mercado por ativo
- gestao preditiva da posicao com time stop, estagnacao, breakeven e trailing
- memoria por setup e contexto
- Fibonacci por pivos confirmados
- hard stop por perda diaria fechada e por drawdown percentual da equity
- exibicao explicita do corte no painel

## Arquivos impactados

- backend/app/models.py
- backend/app/deps.py
- backend/app/parameter_store.py
- backend/app/runtime_policy.py
- backend/app/decision_engine.py
- backend/app/price_action.py
- backend/app/price_action_fibonacci.py
- backend/app/routes/agent.py
- backend/app/routes/monitoring.py
- backend/app/migrations.py
- backend/migrations/sqlite/0013_runtime_intelligence_controls.sql
- backend/migrations/postgres/0013_runtime_intelligence_controls.sql
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_runtime_policy.py
- backend/tests/test_price_action_engine.py
- backend/tests/test_price_action_fibonacci.py
- backend/tests/test_operational_flow.py
- agent-local/app/memory.py
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- projeto/vuno-robo/agent-local/app/memory.py
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-market.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh

## Decisao tomada

- a sessao de mercado passou a ser inferida por familia de ativo usando simbolo principal e broker_profile, sem criar um novo servico; crypto segue 24x7, B3 futures usa janela local e forex_like respeita fechamento de fim de semana
- o hard stop foi acoplado ao runtime guard existente, usando PnL fechado do dia e diferenca balance x equity do snapshot para pausar novas entradas com motivos explicitos
- a gestao de posicao foi estendida dentro do position_manager_v1, com breakeven por pontos, trailing estrutural, deteccao de estagnacao e time stop
- quando reversao e time stop aparecem juntos, o fechamento continua ocorrendo, mas o motivo time_stop tambem entra no analysis para ficar explicavel no painel e na auditoria
- a memoria local do agente passou a consolidar estatisticas por setup e por contexto operacional, reaproveitando a base SQLite local sem inventar um banco paralelo
- o backend passou a consumir essa memoria contextual para modular risco e confianca por setup/contexto favoravel ou defensivo
- o Fibonacci deixou de depender apenas da ancora heuristica e agora prioriza pivos confirmados, com fallback para impulso recente quando nao houver swing valido
- o contrato MT5 passou a exportar open_position_opened_at para permitir calculo de idade da posicao no backend
- o painel recebeu novos controles para sessao, drawdown e gestao de posicao e agora traduz os novos motivos de pausa e gestao em texto operacional

## Alternativas descartadas

- criar um novo subsistema dedicado de risk engine: descartado porque o runtime guard existente ja suportava o encaixe com menor custo e menor risco de divergencia
- empurrar hard stop e time stop apenas para o EA MT5: descartado porque isso reduziria auditabilidade e deixaria o painel sem explicacao completa do bloqueio
- exigir fractais dedicados ou swing map complexo para o Fibonacci neste momento: descartado porque pivo confirmado com fallback ja entrega melhora material para o MVP

## Riscos e observacoes

- a heuristica de pareamento memoria feedback x ultima decisao de entrada do mesmo simbolo e sequencial; ela melhora o contexto sem garantir 100% de vinculacao historica por ticket
- o trailing estrutural ainda trabalha em cima da janela recente de candles; parcial de lucro e trailing por ATR continuam fora desta rodada
- o guard de sessao e calculado no backend; se o usuario operar mercados com horarios especiais da corretora, pode ser necessario ajuste fino por broker_profile
- a migracao 0013 e obrigatoria para ambientes ja existentes antes de salvar os novos parametros pelo painel

## Validacao

- pytest backend/tests/test_price_action_engine.py backend/tests/test_price_action_fibonacci.py -> 16 testes aprovados
- pytest backend/tests/test_runtime_policy.py::test_market_session_blocks_b3_future_outside_local_hours -> aprovado
- pytest backend/tests/test_runtime_policy.py::test_drawdown_guard_blocks_decision_after_daily_loss_and_equity_cut -> aprovado
- pytest backend/tests/test_operational_flow.py::test_demo_instance_agent_flow_and_summary -> aprovado em terminal isolado
- durante a validacao em lote do runtime, o terminal compartilhado do ambiente interrompeu o teardown do pytest com KeyboardInterrupt; por isso a confirmacao final dos cenarios novos foi feita por testes isolados e terminal dedicado

## Proximos passos

1. avaliar se a memoria por contexto deve passar a usar ticket ou decision_id explicito no feedback para eliminar o pareamento sequencial
2. considerar ajuste de sessao por perfil de corretora quando houver ativos fora do calendario forex_like padrao
3. estudar parcial de lucro e trailing por ATR como extensao do position_manager_v1