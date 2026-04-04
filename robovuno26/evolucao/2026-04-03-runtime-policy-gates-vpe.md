## Data
- 2026-04-03

## Objetivo
- Fechar o lote de runtime e seguranca operacional pendente da revisao VPE v2, ligando pausa de noticias, gate minimo de performance, timeframes explicitos e leitura de estrutura mais rica ao fluxo real do backend e do painel.

## Arquivos impactados
- backend/app/models.py
- backend/app/parameter_store.py
- backend/app/economic_calendar.py
- backend/app/runtime_policy.py
- backend/app/routes/parameters.py
- backend/app/routes/agent.py
- backend/app/routes/monitoring.py
- backend/app/routes/robot_instances.py
- backend/app/price_action.py
- backend/app/price_action_zones.py
- backend/app/price_action_structure.py
- backend/static/index.html
- backend/static/js/app.js
- agent-local/app/runtime_contract.py
- backend/migrations/sqlite/0004_runtime_policy_and_vpe_controls.sql
- backend/migrations/postgres/0004_runtime_policy_and_vpe_controls.sql
- backend/tests/test_runtime_policy.py
- backend/tests/test_price_action_engine.py
- backend/tests/test_operational_flow.py

## Decisao tomada
- O runtime passou a tratar o estado operacional como politica centralizada, nao mais como regra espalhada entre rota, painel e agente.
- O gate de performance virou bloqueio real para criacao de instancia em DEMO e REAL quando os minimos configurados ainda nao foram validados.
- A pausa de noticias foi ligada ao runtime efetivo e ao retorno de decisao, permitindo HOLD defensivo com motivo explicito quando houver evento relevante para o simbolo monitorado.
- O painel e o runtime passaram a expor timeframe operacional e timeframe de confirmacao como parte do contrato visivel da estrategia.
- A estrutura de price action foi endurecida para nao publicar `state = neutral` quando ja houve BOS identificado; nesse caso o contexto minimo sobe para faixa de range em rompimento, o que deixa a auditoria mais coerente.
- O summary de monitoramento foi alinhado ao helper atual de instancias para reutilizar a mesma leitura de runtime, bridge e simbolos selecionados sem bifurcar contrato.
- O upsert dos parametros foi corrigido para persistir todas as colunas novas sem quebra de placeholder no SQLite.

## Alternativas descartadas
- Liberar DEMO apenas com aviso visual no painel: descartado, porque o gate precisava ser executavel no backend para nao depender de disciplina manual do usuario.
- Tratar BOS apenas como campo auxiliar e manter `state` neutro: descartado, porque o payload final ficava contraditorio e piorava a leitura humana no painel e na auditoria.
- Duplicar a transformacao de instancia no endpoint de summary: descartado, porque manteria dois contratos concorrentes para os mesmos dados operacionais.

## Riscos e observacoes
- O calendario economico ainda depende de feed externo; se o feed falhar, o sistema precisa continuar sinalizando a origem da indisponibilidade em vez de mascarar o risco.
- O gate de performance ainda depende do preenchimento honesto das metricas validadas; o proximo passo natural e automatizar ingestao de backtest para reduzir entrada manual.
- A estrutura continua heuristica. BOS, CHOCH e falso rompimento ja entram no score e na auditoria, mas ainda nao representam um VPE final com mapa completo de liquidez.

## Validacao executada
- Suite alvo executada com sucesso:
  - backend/tests/test_runtime_policy.py
  - backend/tests/test_price_action_engine.py
  - backend/tests/test_operational_flow.py
- Resultado: 8 testes aprovados.

## Proximos passos
- Validar manualmente no painel os novos campos de leitura e pausa usando uma instancia real do fluxo MT5.
- Evoluir o gate de performance para receber metricas auditaveis de backtest em vez de depender apenas de input manual.
- Continuar a etapa VPE com reteste, liquidez e zonas mais estruturadas quando o runtime estiver estavel em DEMO.