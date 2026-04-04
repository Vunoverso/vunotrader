Data: 2026-04-04

# Painel de robos com escopo por instancia, exclusao e smoke real

## Objetivo

Fechar um bloco operacional do painel para uso real com instancias MT5 ativas:

- migrar o startup do FastAPI para lifespan
- permitir parametros exclusivos por robo com fallback para o padrao da conta
- deixar auditoria e historico identificarem claramente qual robo gerou a leitura
- encurtar status visuais e humanizar o tempo exibido no painel
- permitir exclusao de robo sem apagar o historico
- validar tudo com login real em tenant com instancias MT5 existentes

## Arquivos impactados

- backend/app/main.py
- backend/app/models.py
- backend/app/parameter_store.py
- backend/app/routes/parameters.py
- backend/app/routes/agent.py
- backend/app/routes/monitoring.py
- backend/app/routes/robot_instances.py
- backend/migrations/sqlite/0007_robot_instance_parameters.sql
- backend/migrations/postgres/0007_robot_instance_parameters.sql
- backend/static/index.html
- backend/static/js/app.js
- backend/tests/test_robot_instance_parameters.py

## Decisao tomada

- o bootstrap do FastAPI saiu de startup event e foi movido para lifespan, removendo o warning de deprecacao e deixando a inicializacao mais alinhada com a API atual do framework
- a conta continua tendo parametros padrao em user_parameters, mas cada robot_instance pode agora ter override proprio em robot_instance_parameters; a resolucao efetiva passa a usar override da instancia quando existir e fallback da conta quando nao existir
- runtime-config, decisao, resumo operacional, bloqueios de modo e lista de robos passaram a usar o parametro efetivo da instancia, nao mais apenas o parametro global do tenant
- a auditoria ganhou robot_name no backend e o frontend passou a renderizar referencias como #id nome tanto na timeline quanto no historico
- a exclusao de robo foi implementada como soft delete com is_active = 0 e last_status = DELETED, preservando rastreabilidade e invalidando o token da instancia
- a lista de robos passou a filtrar apenas instancias ativas, com chip curto On/Off e tempo de ultimo contato em formato humano
- a tela Protecoes agora mostra claramente quando esta editando o padrao da conta ou um robo especifico, incluindo indicacao de heranca

## Alternativas descartadas

- manter parametros apenas por tenant: descartado porque nao atende o comportamento operacional pedido para moedas e contas com setups diferentes
- hard delete da instancia: descartado porque apagaria rastros de auditoria e dificultaria suporte
- identificar o robo apenas pela coluna numerica do historico: descartado porque nao resolve ambiguidade quando existem multiplas instancias semelhantes na mesma conta

## Validacao executada

- pytest backend/tests/test_robot_instance_parameters.py
- pytest backend/tests/test_runtime_policy.py
- pytest backend/tests/test_operational_flow.py
- smoke test manual no tenant 13 com login real smoke.mt5.tenant13@example.com
- validacao manual do dashboard, Meus robos, Protecoes e Historico em http://127.0.0.1:8000
- confirmacao da exclusao por UI com robo temporario de teste e verificacao posterior no banco e na auditoria

## Riscos e observacoes

- durante a validacao no Windows, havia multiplos uvicorns antigos na porta 8000; isso fez o painel servir frontend novo com backend antigo em alguns endpoints ate a limpeza completa dos processos
- o restart do backend invalida a sessao visual atual do painel durante o smoke test; isso nao bloqueou a entrega, mas ainda merece endurecimento operacional
- o override atual e por instancia; se houver necessidade futura de comportamento diferente por simbolo dentro da mesma instancia, sera preciso uma camada adicional de configuracao

## Proximos passos

1. endurecer a estrategia de sessao do painel para sobreviver melhor a restarts de backend em ambiente local
2. avaliar override por simbolo dentro da instancia caso o uso multiativos evolua alem do escopo atual
3. adicionar testes E2E do fluxo editar setup -> abrir Protecoes -> salvar override -> excluir instancia