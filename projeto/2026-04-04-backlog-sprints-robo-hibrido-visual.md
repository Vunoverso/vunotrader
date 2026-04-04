# 2026-04-04 - Backlog tecnico por sprint do Robo Hibrido Visual

## Objetivo

Transformar o plano do `Robo Hibrido Visual` em backlog tecnico executavel, com sprints, dependencias, criterios de aceite e gates obrigatorios.

## Regras de execucao

1. O fluxo oficial alvo e `agent-local + bridge`.
2. O fluxo HTTP direto em `backend/app/api/routes/mt5.py` permanece legado em transicao.
3. A leitura estruturada continua autoritativa ate existir RFC especifica para mudar isso.
4. O rollout externo do robo visual depende de feature flags por plano.
5. `computer use` nao entra no caminho critico de ordem no MVP.

## Gate 0 - Alinhamento arquitetural

### Objetivo

Fechar a direcao antes de abrir qualquer frente de implementacao visual.

### Entregas

- alinhar documentacao oficial da instalacao para `agent-local + bridge`
- alinhar dashboard e onboarding com `Robo Integrado` versus `Robo Hibrido Visual`
- congelar contrato de `cycle_id`
- congelar contrato alvo do endpoint `/api/agent/decision`
- aprovar desenho de feature flags SaaS

### Dependencias

- nenhuma

### Critérios de aceite

1. Nao existe mais texto oficial tratando o fluxo HTTP direto como caminho principal.
2. A instalacao fala explicitamente em `Robo Integrado` e `Robo Hibrido Visual`.
3. O contrato de `cycle_id` esta documentado e aprovado.
4. O contrato base do agente e o mapa de entitlements existem em documento versionado.

### Bloqueios

- nenhuma PR de screenshot, shadow mode ou rollout visual sobe para usuario antes desse gate.

## Sprint 1 - Artefatos do ciclo no MT5

### Objetivo

Gerar artefatos visuais e estruturados com correlacao forte no bridge.

### Entregas

- adicionar `cycle_id` no bridge MT5
- gerar `.snapshot.json` com `cycle_id`
- gerar `.png` do chart com o mesmo `cycle_id`
- padronizar nome de arquivo local
- registrar metadados basicos da imagem no snapshot

### Arquivos alvo provaveis

- `vuno-robo/mt5/VunoRemoteBridge.mq5`
- `vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh`
- `vuno-robo/mt5/vuno-bridge/*`

### Dependencias

- Gate 0 aprovado

### Critérios de aceite

1. Cada ciclo gera JSON e PNG com o mesmo `cycle_id`.
2. Falha na captura do PNG nao impede o JSON de ser produzido.
3. O snapshot carrega `cycle_id`, `chart_image_file` e `chart_image_captured_at`.
4. O bridge continua operando sem stream continuo de tela.

## Sprint 2 - Agent-local e persistencia bruta

### Objetivo

Transportar o ciclo visual sem inferencia ainda.

### Entregas

- agent-local correlaciona JSON + PNG por `cycle_id`
- agent-local sobe imagem e metadata com retry
- backend recebe e persiste referencias de imagem
- storage guarda artefato com path derivado de `cycle_id`
- auditoria interna exibe miniatura e vinculacao ao ciclo

### Arquivos alvo provaveis

- `vuno-robo/agent-local/app/main.py`
- `vuno-robo/agent-local/app/bridge.py`
- `vuno-robo/agent-local/app/api_client.py`
- backend principal em nova area `/api/agent/*`

### Dependencias

- Sprint 1 concluido

### Critérios de aceite

1. Um ciclo com screenshot chega ao backend sem perder correlacao.
2. Se o upload falhar, o agent-local retem fila local sem perder o ciclo.
3. O backend salva `chart_image_storage_path` e `chart_image_hash`.
4. O dashboard interno mostra preview da imagem do ciclo.

## Sprint 3 - Feature flags e modelo SaaS

### Objetivo

Criar gating tecnico limpo para os produtos e recursos visuais.

### Entregas

- criar `saas_features`
- criar `saas_plan_features`
- criar leitura consolidada de entitlements no backend
- expor entitlements consumiveis pelo frontend
- adicionar `robot_product_type` em `robot_instances`
- adicionar flags por instancia para visual e `computer use`

### Dependencias

- Gate 0 concluido
- pode rodar em paralelo ao Sprint 2

### Critérios de aceite

1. Starter nao recebe `robot.visual_hybrid`.
2. Pro recebe `robot.visual_hybrid` e `robot.visual_shadow`.
3. Scale recebe os recursos expandidos definidos no contrato.
4. O frontend nao depende de `if planCode === 'pro'` espalhado como regra de negocio principal.
5. `robot_instances` distingue `robo_integrado` e `robo_hibrido_visual`.

## Sprint 4 - Shadow mode interno

### Objetivo

Processar a imagem e comparar com a leitura estruturada sem expor isso ao cliente ainda.

### Entregas

- worker visual shadow
- persistencia de `visual_context`
- persistencia de `visual_alignment`
- fila de revisao para `divergent_high`
- tela ou filtro interno para alinhamento visual

### Dependencias

- Sprint 2 concluido
- Sprint 3 com feature flags e schema aprovado

### Critérios de aceite

1. Um ciclo pode terminar em `aligned`, `divergent_low`, `divergent_high` ou `error`.
2. Divergencia visual nao altera `.command.json`.
3. `divergent_high` entra em fila de revisao.
4. Equipe interna consegue comparar leitura estruturada versus visual para uma amostra relevante de ciclos.

## Sprint 5 - Produto Pro controlado

### Objetivo

Expor o `Robo Hibrido Visual` para clientes autorizados com semantica correta.

### Entregas

- instalacao com escolha entre `Robo Integrado` e `Robo Hibrido Visual`
- dashboard com cards das duas linhas de produto
- auditoria com bloco visual para clientes elegiveis
- status visual por instancia
- badge e semantica de divergencia no painel

### Dependencias

- Sprint 4 concluido
- feature flags operacionais ativas

### Critérios de aceite

1. Cliente Starter nao ve o fluxo visual completo.
2. Cliente Pro e Scale veem o posicionamento correto do produto.
3. O painel mostra estado do bridge e estado visual separadamente.
4. A auditoria mostra rationale oficial e rationale visual no mesmo ciclo.

## Sprint 6 - Computer use assistido

### Objetivo

Adicionar setup, diagnostico e recuperacao assistida sem entrar no caminho principal da ordem.

### Entregas

- worker de `computer use` com lock por instancia
- kill switch global
- aprovacao humana quando aplicavel
- rotinas guiadas de setup e recover
- telemetria de desktop actions

### Dependencias

- Sprint 5 concluido
- governanca aprovada para uso de desktop automation

### Critérios de aceite

1. `computer use` pode ser ligado e desligado por instancia e globalmente.
2. Nenhuma acao de desktop vira rota oficial de ordem no MVP.
3. Logs de mouse, teclado e screenshot ficam auditaveis.
4. Falha no worker de `computer use` nao derruba o fluxo oficial do robo.

## Dependencias cruzadas

### Backend

- contrato `/api/agent/decision`
- storage para screenshots
- persistencia de `trade_visual_contexts` ou equivalente
- entitlements SaaS

### Frontend

- instalacao
- dashboard
- auditoria
- configuracao/assinatura

### MT5 e agent-local

- `cycle_id`
- captura de PNG
- fila local de artefatos
- retries e arquivamento

## Ordem recomendada real

1. Gate 0
2. Sprint 1
3. Sprint 2 e Sprint 3 em paralelo
4. Sprint 4
5. Sprint 5
6. Sprint 6

## Definicao de pronto do rollout Pro

1. O `Robo Hibrido Visual` esta atras de entitlements de plano.
2. Cada ciclo visual tem `cycle_id` unico, imagem e trilha persistida.
3. O dashboard diferencia bridge, visual e execucao.
4. A divergencia visual possui semantica definida e visivel.
5. O fluxo oficial continua funcionando mesmo quando a camada visual falha.
