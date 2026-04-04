# 2026-04-04 - Runtime do shadow visual e convergencia do Gate 0

## Data

2026-04-04

## Objetivo

Fechar a parte operacional do Gate 0 do plano de implantacao MT5 visual shadow, tornando `agent-local + bridge + token unico` o caminho oficial da integracao e ligando o ciclo real de screenshot, persistencia e exibicao visual no produto.

## Arquivos impactados

- `backend/app/api/router.py`
- `backend/app/api/routes/agent.py`
- `backend/app/api/routes/mt5.py`
- `backend/app/core/config.py`
- `backend/app/services/visual_shadow.py`
- `supabase/migrations/20260404_000019_visual_shadow_runtime.sql`
- `supabase/migrations/20260404_000020_visual_shadow_non_chart_status.sql`
- `vuno-robo/agent-local/app/api_client.py`
- `vuno-robo/agent-local/app/bridge.py`
- `vuno-robo/agent-local/app/config.py`
- `vuno-robo/agent-local/app/legacy_mt5_api.py`
- `vuno-robo/agent-local/app/main.py`
- `vuno-robo/agent-local/config.example.json`
- `vuno-robo/agent-local/runtime/config.json`
- `vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh`
- `vuno-robo/mt5/vuno-bridge/vuno-bridge-paths.mqh`
- `web/src/app/api/mt5/live-trades/route.ts`
- `web/src/app/app/ao-vivo/page.tsx`
- `web/src/app/app/auditoria/page.tsx`
- `web/src/app/app/dashboard/page.tsx`
- `web/src/components/app/auditoria-table.tsx`
- `web/src/components/app/mt5-robot-instances-panel.tsx`
- `web/src/components/app/robot-product-dashboard-lanes.tsx`
- `web/src/lib/mt5/visual-shadow.ts`

## Decisao

- foi criada a rota oficial `backend/app/api/routes/agent.py` com `runtime-config`, `decision`, `trade-feedback`, `trade-opened`, `heartbeat` e `symbol-catalog`
- as rotas `agent` e `mt5` passaram a resolver selects unitarios com `limit(1).execute()`, evitando dependencia do metodo `maybeSingle()` no client Python instalado no ambiente atual
- o `agent-local` passou a consumir `/api/agent/*` em vez de expandir o legado `/api/mt5/*`
- `cycle_id` agora nasce no bridge MT5 e entra no nome do `.snapshot.json`, no PNG e no payload do agente
- o bridge MT5 tenta capturar screenshot do chart anexado ao EA no mesmo ciclo e grava o metadado no snapshot
- o backend passou a persistir `trade_visual_contexts` com upload para bucket privado `mt5-visual-captures`, hash da imagem, status do shadow e alinhamento visual
- o pipeline visual agora le `OPENAI_API_KEY` pelo settings do backend, em vez de depender de `os.getenv` puro; isso destravou a leitura real da chave presente no `.env`
- o pipeline visual continua com fallback honesto quando `OPENAI_API_KEY` nao estiver configurada: a imagem fica persistida, mas o alinhamento vira `not_applicable` em vez de inventar leitura visual
- o dashboard, o ao vivo e a auditoria agora exibem badge do shadow e screenshot quando houver artefato correlacionado
- `human_approval_required`, `VISUAL_SHADOW_KILL_SWITCH` e `COMPUTER_USE_KILL_SWITCH` passaram a influenciar `runtime_pause_new_orders` no contrato remoto do agente
- a cobertura visual multiativos permanece restrita ao chart anexado no Gate 0; a expansao correta para outros simbolos fica reservada para uma fase dedicada com charts por simbolo, e nao por reaproveitamento do mesmo screenshot
- foi formalizado o status `skipped_non_chart_symbol` para ciclos fora do chart anexado, com uso previsto no scanner multiativos

## Alternativas descartadas

- continuar expandindo apenas `/api/mt5/signal`: descartado porque perpetuaria o legado em vez de consolidar o contrato oficial do agente
- gerar `cycle_id` no agent-local: descartado porque quebraria a origem unica de correlacao entre JSON, PNG e auditoria
- anexar o mesmo screenshot do chart atual a todos os simbolos do scanner multiativos: descartado porque produziria correlacao falsa
- tentar declarar cobertura visual multiativos como concluida sem abrir chart dedicado por simbolo: descartado porque esconderia a limitacao real do runtime e contaminaria a trilha de auditoria
- bloquear ordem automaticamente por divergencia visual no MVP: descartado para manter o shadow como trilha de auditoria e calibracao, nao como autoridade de execucao

## Riscos e observacoes

- no estado atual, o screenshot so e capturado para o simbolo/timeframe do grafico onde o EA esta anexado; ciclos multiativos fora desse chart ficam com `not_applicable` ou `skipped_non_chart_symbol`
- a migration do bucket `mt5-visual-captures` e dos campos extras em `trade_visual_contexts` foi aplicada no Supabase remoto via SQL Editor em 2026-04-04
- a migration `20260404_000020_visual_shadow_non_chart_status.sql` foi aplicada no Supabase remoto para aceitar `skipped_non_chart_symbol`
- se `OPENAI_API_KEY` nao estiver configurada, o shadow continua gravando a imagem e os metadados, mas nao faz leitura visual semantica
- o build do frontend validou com `next build --webpack`; o Turbopack do projeto apresentou erro de parsing inconsistente em arquivo nao relacionado (`dashboard-quick-actions.tsx`)
- a falha real do `ChartScreenShot` foi corrigida ao trocar a escrita para caminho relativo em `MQL5\Files` e ao manter busca fallback no `agent-local` para a pasta local do terminal
- a correlacao real agora fecha ponta a ponta para o ciclo validado, incluindo reprocessamento semantico posterior com `gpt-4o-mini`
- o dashboard local exibiu erros 404 em chamadas auxiliares nao relacionadas ao fluxo validado de `trade_visual_contexts`; isso nao impediu a renderizacao correta do screenshot e do `cycle_id`, mas merece limpeza separada

## Validacao operacional executada

- migrations `20260404_000018_visual_robot_entitlements.sql` e `20260404_000019_visual_shadow_runtime.sql` aplicadas com sucesso no projeto Supabase remoto `mztrtovhjododrkzkehk`
- validado no SQL Editor remoto:
	- cadastro de `saas_features`
	- criacao da tabela `trade_visual_contexts`
	- bucket privado `mt5-visual-captures`
- bridge do MT5 sincronizado novamente na pasta `MQL5/Experts` do terminal local
- `VunoRemoteBridge.ex5` recompilado com sucesso no MetaEditor local
- terminal MT5 reiniciado com o EA recompilado e gerando novos snapshots reais no padrao `VunoBridge_<symbol>_<timeframe>_<epoch>_<tickcount>.snapshot.json`
- o bridge passou a gravar screenshots reais em `MQL5/Files/VunoBridge/in`
- validado no ciclo real `VunoBridge_AMD_M5_1775260777_1188171`:
	- `cycle_id` presente no JSON e no nome do PNG
	- `chart_image_file = "VunoBridge\\in\\VunoBridge_AMD_M5_1775260777_1188171.chart.png"`
	- `chart_image_status = captured`
	- PNG real encontrado em `MQL5/Files/VunoBridge/in/VunoBridge_AMD_M5_1775260777_1188171.chart.png`
	- `agent-local` localizou corretamente o PNG do mesmo ciclo via `BridgeFilesystem.find_chart_image(...)`
- provisionado um contexto controlado de teste com assinatura Pro ativa e `robot_instance` visual habilitada para validar o replay oficial do mesmo ciclo no backend remoto
- replay oficial do mesmo ciclo executado em `/api/agent/decision` com retorno `200`, `decision_id = 52da7887-0d7d-471e-9bdf-b52a2cb30ee0`, `visual_shadow_status = processed` e `visual_conflict_reason = vision_api_unconfigured`
- confirmado no Supabase remoto para o mesmo `cycle_id`:
	- `trade_decisions.trade_id = VunoBridge_AMD_M5_1775260777_1188171`
	- `trade_visual_contexts.cycle_id = VunoBridge_AMD_M5_1775260777_1188171`
	- `chart_image_storage_path = d7ae8eb1-f704-4a27-abd8-53c03f9cded4/8d213456-6688-4bb2-a8ef-58a26571c930/2026/04/04/VunoBridge_AMD_M5_1775260777_1188171.chart.png`
	- objeto privado existente em `mt5-visual-captures` com `size = 60044` e `mimetype = image/png`
- corrigida a leitura da chave OpenAI no backend e executado reprocessamento dos ciclos persistidos em `capture-only-v1`
- confirmado no SQL Editor remoto apos o reprocessamento:
	- `capture_only_count = 0`
	- o ciclo `VunoBridge_AMD_M5_1775260777_1188171` passou para `visual_shadow_status = processed`
	- `visual_alignment = aligned`
	- `visual_model_version = gpt-4o-mini`
	- `visual_conflict_reason = null`
- confirmado no frontend local autenticado com o mesmo tenant:
	- dashboard exibiu o mesmo `cycle_id`, o screenshot assinado e badge `Shadow alinhado` na lane do robo hibrido visual
	- auditoria exibiu a decisao `52da7887-0d7d-471e-9bdf-b52a2cb30ee0`, o mesmo screenshot, o mesmo `cycle_id` e badge `Shadow alinhado`

## Proximos passos

1. gerar um ciclo de teste explicito fora do chart anexado para validar operacionalmente o novo status `skipped_non_chart_symbol`
2. transformar o desenho de charts dedicados por simbolo em backlog tecnico com migration, contrato de catalogo e limites por plano
3. decidir se o reprocessamento de ciclos visuais vira rota administrativa, job manual ou worker agendado
4. evoluir a governanca de lock para fluxo distribuido real se houver mais de um worker visual por instancia