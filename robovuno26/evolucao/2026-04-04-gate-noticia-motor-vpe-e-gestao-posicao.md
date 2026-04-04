Data: 2026-04-04

# Gate geral de noticia, selecao de motor e gestao de posicao VPE

## Objetivo

Fechar tres lacunas do plano de Price Action VPE antes de ampliar o uso em DEMO/REAL:

- generalizar o gate obrigatorio de noticia para qualquer ativo monitorado pela instancia
- permitir selecao de motor de decisao por conta ou por instancia
- impedir nova entrada com posicao aberta e passar a gerir lucro/protecao via contrato backend + MT5

## Arquivos impactados

- backend/app/models.py
- backend/app/parameter_store.py
- backend/app/runtime_policy.py
- backend/app/decision_engine.py
- backend/app/price_action.py
- backend/app/price_action_fibonacci.py
- backend/app/routes/agent.py
- backend/app/routes/robot_instances.py
- backend/app/migrations.py
- backend/migrations/sqlite/0009_decision_engine_mode.sql
- backend/migrations/postgres/0009_decision_engine_mode.sql
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_price_action_engine.py
- backend/tests/test_runtime_policy.py
- backend/tests/test_robot_instance_parameters.py
- backend/tests/test_operational_flow.py
- backend/tests/test_price_action_fibonacci.py
- agent-local/app/bridge.py
- mt5/vuno-bridge/vuno-bridge-market.mqh
- mt5/vuno-bridge/vuno-bridge-execution.mqh
- mt5/vuno-bridge/vuno-bridge-io.mqh
- projeto/vuno-robo/agent-local/app/bridge.py
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-market.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-execution.mqh
- projeto/vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh

## Decisao tomada

- o gate de noticia deixou de ser tratado como protecao focada em XAUUSD e passou a validar cobertura dos simbolos monitorados pela instancia; o usuario pode usar lista explicita ou '*' para cobertura geral, com derivacao automatica de paises por simbolo quando o campo ficar vazio
- o modo do motor foi formalizado como parametro persistido com tres estados: HYBRID, PRICE_ACTION_ONLY e LEGACY_ONLY
- quando existe posicao aberta, o backend nao gera nova entrada; ele devolve HOLD com acao de gestao NONE, PROTECT ou CLOSE
- o snapshot MT5 passou a exportar ticket, direcao, preco de entrada, SL/TP, lucro e lucro em pontos da posicao aberta
- o comando MT5 passou a aceitar position_action, position_ticket, position_stop_loss e position_take_profit
- o motor de Price Action passou a devolver auditoria mais estruturada com zona, invalidacao, checklist e stop/take por estrutura
- a auditoria passou a separar decisao de entrada e gestao de posicao, usando position_management_recorded para eventos conduzidos pelo position_manager_v1
- o historico do painel passou a aceitar filtro por position_action sem criar novos event_type; o filtro opera sobre eventos conduzidos pelo position_manager_v1 e permite isolar NONE, PROTECT e CLOSE
- o painel passou a destacar quando a decisao era gestao de posicao, com tags e narrativa especifica para CLOSE, PROTECT e monitoramento sem nova entrada
- o backend passou a barrar snapshot com mercado morto ou feed congelado, segurando novas entradas e gestao agressiva quando a janela recente vier com candles repetidos ou ativo sem movimento confiavel
- o agente local deixou de descartar position_action e campos de gestao ao normalizar a resposta do backend; com isso CLOSE e PROTECT chegam de fato ao comando do MT5
- Fibonacci passou a entrar como camada de confluencia no motor, com zona de retracao 38.2%-61.8%, score proprio e alvos de extensao expostos no analysis

## Alternativas descartadas

- manter o gate obrigatorio apenas para XAUUSD: descartado porque nao escala para multiativos e conflita com o pedido operacional atual
- criar uma segunda camada de configuracao separada para o modo do motor: descartado porque o projeto ja tinha suporte a parametro por instancia
- permitir novas entradas mesmo com posicao aberta e deixar a gestao so no MT5: descartado porque manteria risco de empilhamento e pouca explicabilidade

## Riscos e observacoes

- para usar CLOSE/PROTECT no terminal do usuario, o EA precisa ser recompilado com os arquivos novos do pacote/mt5
- a protecao de lucro usa regra simples baseada em pontos positivos e contexto estrutural; trailing mais fino por parcial/ATR ainda nao foi implantado
- o guard de mercado parado foi calibrado para preferir falso negativo a falso positivo; se algum simbolo legitimo operar com range muito comprimido por muito tempo, os thresholds podem precisar ajuste fino por classe de ativo
- contas antigas com news_pause_symbols restrito continuam exigindo ajuste manual se a cobertura nao casar com os simbolos da instancia
- a leitura de Fibonacci ainda usa ancora heuristica por impulso recente; pode evoluir depois para swing map mais formal com fractais dedicados

## Validacao

- pytest backend/tests/test_price_action_engine.py backend/tests/test_price_action_fibonacci.py backend/tests/test_runtime_policy.py backend/tests/test_robot_instance_parameters.py backend/tests/test_operational_flow.py
- resultado: 16 testes aprovados quando executados por arquivo
- validacao ao vivo no tenant smoke.mt5.tenant13@example.com: o robo 6 gerou eventos position_management_recorded com position_action PROTECT, engine position_manager_v1 e fib_in_retracement_zone ativo; o painel exibiu Ultima analise e timeline com Proteger lucro, lucro protegido e Fib 38.2%-61.8%
- melhoria de MVP aplicada no historico: o mesmo endpoint /api/audit-events agora aceita position_action e filtra a trilha de gestao sem exigir novos tipos de evento
- melhoria de inteligencia operacional aplicada: snapshots com candles repetidos ou ativo parado agora caem em HOLD explicavel, e o agente local preserva CLOSE/PROTECT ao escrever o comando final para o MT5

## Proximos passos

1. considerar trailing estrutural incremental e parcial de lucro no contrato do EA
2. avaliar se CLOSE e PROTECT merecem subtipos proprios alem de position_management_recorded para filtros mais finos no historico
3. evoluir a ancora de Fibonacci para swing highs/lows mais formais e possiveis extensoes por contexto HTF
