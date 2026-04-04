# Implantacao MT5 com visao grafica, shadow mode e dois tipos de robo

## Objetivo

Planejar a adicao de leitura visual do grafico MT5 ao sistema principal, mantendo a trilha auditavel atual e introduzindo dois modos de produto para o usuario:

- robo bridge oficial
- robo visual assistido

O plano considera:

- exportacao de screenshot junto do snapshot JSON
- contexto visual em shadow mode
- gating por plano SaaS
- comportamento do dashboard
- fluxo completo de entrada e saida de dados

## Artefatos derivados

- `projeto/2026-04-04-backlog-sprints-robo-hibrido-visual.md`
- `projeto/2026-04-04-contrato-dados-robo-hibrido-visual.md`

## Diagnostico do estado atual

### Fluxo oficial atual da raiz

Hoje a raiz ainda mistura dois caminhos:

1. fluxo HTTP direto do EA para o backend principal
2. direcao arquitetural mais nova apontando para `agent-local + bridge + token unico`

Arquivos que evidenciam isso:

- `backend/app/api/routes/mt5.py`
- `web/src/app/api/mt5/robot-package/route.ts`
- `web/src/app/app/instalacao/page.tsx`
- `web/src/app/api/mt5/robot-credentials/instances/route.ts`

### Arquitetura de referencia mais aderente

O pacote `vuno-robo` e a base `robovuno26` mostram o caminho mais robusto para evolucao:

- EA gera snapshot por arquivo
- agent-local le snapshot
- backend responde decisao
- EA le comando local
- feedback volta por arquivo

Arquivos de referencia:

- `vuno-robo/mt5/VunoRemoteBridge.mq5`
- `vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh`
- `vuno-robo/agent-local/app/main.py`
- `robovuno26/backend/app/routes/agent.py`
- `robovuno26/backend/app/agent_package.py`

### Divergencia importante ja encontrada

O plano oficial mais recente diz para convergir para `agent-local + bridge`, mas a pagina atual de instalacao da raiz ainda orienta o usuario pelo fluxo antigo com URL direta no MT5.

Esse conflito precisa ser resolvido antes da implantacao final da camada visual.

### Bloqueio formal da Fase 0

Esse item nao pode ser tratado como contexto ou recomendacao leve.

Ele precisa ser um gate real de projeto.

Regra proposta:

- nenhuma entrega de screenshot, shadow mode ou robo visual sobe para ambiente de usuario enquanto a arquitetura oficial nao estiver declarada como `agent-local + bridge`
- nenhuma nova tela de instalacao deve reforcar o fluxo HTTP direto como caminho oficial
- nenhum contrato novo de visual deve nascer diretamente sobre `/api/mt5/signal` como destino final de produto

Critérios minimos para liberar a proxima etapa:

1. documentacao oficial alinhada
2. instalacao com linguagem alinhada
3. contrato alvo do agente definido
4. backlog tecnico assumindo o fluxo bridge como referencia

## Tese principal

A leitura visual deve entrar como segunda fonte de contexto, nao como substituta da camada estruturada.

Em termos praticos:

- a leitura numerica/estruturada continua sendo a fonte autoritativa de execucao
- a leitura visual entra primeiro em shadow mode
- o dashboard mostra as duas leituras lado a lado
- o usuario percebe mais valor visual sem sacrificar auditabilidade

## Modelo de produto proposto

### Tipo 1 - Robo Integrado

Definicao:

- robô operacional principal
- baseado em bridge local por arquivos
- usa snapshot estruturado como fonte principal
- executa ordens de forma oficial

Objetivo:

- operacao previsivel
- trilha forte de auditoria
- melhor resiliência operacional

Disponibilidade sugerida:

- Starter: demo com recursos limitados
- Pro: demo e real
- Scale: demo e real com limites expandidos

### Tipo 2 - Robo Hibrido Visual

Definicao:

- usa a mesma base do bridge oficial
- adiciona screenshot do grafico e contexto visual
- pode mostrar overlays, leitura visual e explicacao enriquecida
- nao deve assumir execucao principal na fase inicial

Objetivo:

- maior impacto visual para o usuario
- mais confianca no que o sistema esta vendo
- base para copiloto de instalacao, diagnostico e suporte

Disponibilidade sugerida:

- Pro: shadow mode visual e leitura enriquecida
- Scale: shadow mode visual + recursos avancados de assistencia e comparativos

## Resposta para a ideia de usar duas leituras ao mesmo tempo

A ideia e boa, com uma restricao essencial:

- as duas leituras nao devem competir pela autoridade de execucao no inicio

Direcao correta:

- leitura A: snapshot estruturado decide
- leitura B: screenshot valida, enriquece e explica

Isso entrega o efeito visual que voce quer:

- usuario ve o robo lendo o grafico real
- ve sinais, indicadores e contexto visual mudando
- ve ordens abrindo e fechando
- tudo continua registrado no painel online com um ID unico por ciclo e por decisao

Direcao errada para a fase inicial:

- deixar a leitura visual mandar ordem diretamente sem shadow mode e sem reconciliacao com a leitura estruturada

### Politica de divergencia visual

O ponto critico nao e apenas detectar divergencia, e definir comportamento.

Contrato proposto para as primeiras entregas:

- `aligned`: leitura visual confirma a leitura estruturada; dashboard mostra badge verde e segue normal
- `divergent_low`: leitura visual discorda ou levanta duvida, mas com baixa confianca; dashboard mostra aviso discreto e auditoria registra
- `divergent_high`: leitura visual diverge com alta confianca; dashboard mostra alerta claro, auditoria marca o ciclo para revisao e o sistema notifica fila interna
- `error`: screenshot ou pipeline visual falhou; o fluxo oficial segue operando e a falha fica registrada apenas como degradacao visual

Regra operacional:

- nas Fases 1 a 3, divergencia visual nunca bloqueia ordem automaticamente
- divergencia visual nunca reescreve `.command.json` no MVP
- divergencias de alta confianca entram em fila de revisao e alimentam calibracao do modelo visual
- qualquer promocao futura da camada visual para influenciar ordem exige RFC propria, dados historicos e kill switch dedicado

## Fluxo ponta a ponta proposto

## Entrada de dados

### Etapa 1 - MT5 gera snapshot estruturado

Origem:

- candles
- EMA
- RSI
- spread
- saldo/equity
- posicoes abertas
- simbolo e timeframe

Destino:

- arquivo `.snapshot.json` na pasta da bridge

Fonte base atual:

- `vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh`

### Etapa 2 - MT5 gera screenshot do chart

Origem:

- grafico real anexado ao EA
- objetos visuais do chart
- indicadores desenhados no terminal
- candles e escala visual reais

Destino:

- arquivo `.png` na pasta da bridge, correlacionado ao snapshot

### Contrato do `cycle_id`

Esse campo precisa ser definido antes da implementacao para evitar quebrar a correlacao entre JSON, PNG, comando, auditoria e dashboard.

Direcao recomendada:

- o `cycle_id` deve ser gerado no MT5, no mesmo ponto em que o bridge cria o snapshot
- o mesmo `cycle_id` deve entrar:
	- no nome do `.snapshot.json`
	- no nome do `.png`
	- dentro do JSON
	- no payload enviado ao agent-local
	- nos registros persistidos no backend

Motivo:

- o MT5 e a origem comum dos dois artefatos
- se o agent-local gerar o ID depois, a correlacao vira heuristica e nao contrato

Formato recomendado para MVP:

- string ASCII, ordenavel e legivel
- composicao sugerida: `bridgeName_symbol_timeframe_unix_tickcount`

Exemplo conceitual:

- `vuno-bridge_EURUSD_M5_1775310000_28451`

Requisitos:

- unicidade por ciclo local
- legibilidade humana para auditoria
- compatibilidade com nome de arquivo e storage path

Campos novos sugeridos no snapshot:

- `cycle_id`
- `chart_image_file`
- `chart_image_captured_at`
- `chart_image_hash`
- `chart_window_symbol`
- `chart_window_timeframe`

### Etapa 3 - Agent-local consolida pacote do ciclo

Responsabilidades:

- correlacionar JSON e PNG
- validar idade do ciclo
- anexar metadata local
- enviar ao backend

Payload proposto:

- bloco `market_snapshot`
- bloco `visual_snapshot`
- bloco `runtime_state`
- bloco `local_memory`

### Etapa 4 - Backend processa duas camadas

Camada A - engine oficial:

- usa snapshot estruturado
- decide `BUY`, `SELL`, `HOLD`, `PROTECT`, `CLOSE`

Camada B - visual shadow:

- analisa screenshot
- produz `visual_context`
- produz `visual_setup_guess`
- produz `visual_quality_score`
- produz `visual_rationale`
- nao muda a ordem na Fase 1

### Etapa 5 - Reconciliacao do ciclo

O backend grava para cada ciclo:

- decisao oficial
- leitura visual shadow
- concordancia ou divergencia entre as duas

Campos sugeridos:

- `decision_source = structured_engine`
- `visual_shadow_status = pending|processed|error`
- `visual_alignment = aligned|divergent|not_applicable`
- `visual_conflict_reason`

### Etapa 6 - Saida operacional para o MT5

Somente a decisao oficial vai para:

- arquivo `.command.json`

A leitura visual vai para:

- auditoria
- dashboard
- explicacao ao usuario
- dataset de treino e calibracao futura

### Etapa 7 - Feedback e fechamento

O MT5 devolve:

- abertura da ordem
- alteracoes de SL/TP
- fechamento
- resultado financeiro

O backend consolida:

- decisao oficial
- resultado executado
- leitura visual daquele mesmo ciclo
- pos-analise

## Fluxo de saida para o dashboard

## Dashboard operacional

O dashboard deve parar de mostrar apenas conectado ou desconectado e passar a refletir quatro camadas:

1. estado do bridge oficial
2. estado da leitura visual
3. estado da execucao
4. estado do plano e dos modulos liberados

### Card de instancia

Campos sugeridos:

- tipo do robo: `robo_integrado` ou `robo_hibrido_visual`
- status do bridge: online, degradado, offline
- status visual: shadow ativo, shadow sem imagem, erro visual, desabilitado
- simbolo principal
- timeframe
- ultimo heartbeat
- ultimo snapshot
- ultimo screenshot

### Timeline do ciclo

Cada ciclo exibido no painel deve mostrar:

- snapshot recebido
- imagem capturada
- decisao oficial
- leitura visual shadow
- comando emitido
- abertura/nao abertura
- fechamento
- resultado

### Tela de auditoria

Cada registro deve permitir ver:

- JSON do ciclo
- screenshot do chart
- rationale oficial
- rationale visual
- alinhamento entre leituras
- ordem executada
- resultado final

### Tela ao vivo

Comportamento sugerido:

- miniatura do chart mais recente
- badge de sombra visual ativa
- comparativo instantaneo entre leitura oficial e leitura visual
- banner quando houver divergencia relevante

### Tela de instalacao

Precisa mudar a semantica atual.

Hoje a pagina mistura:

- EA HTTP legado
- EA simples
- screener multiativos
- bot Python em CMD

Nova organizacao sugerida:

- Robo Integrado
- Robo Hibrido Visual
- Avancado: Bot Python local de laboratorio

## Gating por plano

### Lacuna atual do modelo SaaS

Hoje o sistema ja possui limites como `max_bots`, mas nao possui feature flags formais por plano.

Isso aparece no schema atual:

- `saas_plan_limits` possui `max_bots`
- a leitura de assinatura em `web/src/lib/subscription-access.ts` traz apenas status e identificacao do plano
- `robot_instances` ainda nao distingue oficialmente o tipo do robo

Sem uma camada de feature flags, o gating do robo visual ficaria espalhado por `if planCode === 'pro'` no frontend e no backend.

### Direcao recomendada

Adicionar uma camada formal de entitlements.

Estruturas sugeridas:

- `saas_features`
- `saas_plan_features`

Features candidatas:

- `robot.integrated`
- `robot.visual_hybrid`
- `robot.visual_shadow`
- `robot.visual_storage_extended`
- `robot.visual_compare`
- `ops.desktop_recovery`

Config por feature pode carregar JSON opcional, por exemplo:

- retenção de imagem
- resolução maxima
- numero maximo de instancias visuais
- flags de rollout interno

### Regra de enforcement

- backend e a fonte autoritativa do entitlement
- frontend apenas reflete o que o backend ja autorizou
- instalacao, criacao de instancia, runtime e dashboard devem consultar o mesmo mapa de features

## Starter

- bridge oficial
- 1 instancia
- modo demo
- sem visual shadow
- sem screenshot no painel ou com retenção curta e baixa resolucao

## Pro

- bridge oficial
- visual shadow
- escolha entre robo oficial e robo visual assistido
- screenshot com auditoria visual
- modo real liberado segundo politica atual

## Scale

- tudo do Pro
- mais instancias
- retention maior de imagens
- comparativos entre leituras
- assistente operacional e diagnostico remoto
- trilha visual expandida para time e suporte

## Mudancas de backend

### Locks, kill switch e aprovacao humana

Como a camada visual aumenta o impacto operacional e comercial, o projeto precisa nascer com governanca explicita.

Controles minimos sugeridos:

- `visual_shadow_enabled` por instancia
- `computer_use_enabled` por instancia
- `human_approval_required` por instancia ou tenant
- `visual_kill_switch` global
- `computer_use_kill_switch` global
- `visual_worker_lock_owner` para evitar dois workers no mesmo ciclo

Regras:

- o robo hibrido visual pode existir no produto Pro, mas `computer use` nao entra automaticamente em execucao real
- qualquer acao de mouse/teclado fora de diagnostico precisa de flag e politica especifica
- no MVP, computer use fica limitado a setup, validacao e recuperacao assistida

### Contrato de entrada

Expandir o contrato do endpoint principal do agente para suportar:

- referencias de imagem
- metadata visual
- status do pipeline shadow

Se a raiz seguir o contrato `agent-local + bridge`, o melhor destino e uma rota tipo:

- `/api/agent/decision`

e nao continuar expandindo indefinidamente o fluxo direto em:

- `/api/mt5/signal`

### Persistencia sugerida

Adicionar ou evoluir estruturas para armazenar:

- `chart_image_path`
- `chart_image_storage_path`
- `chart_image_hash`
- `visual_context`
- `visual_rationale`
- `visual_quality_score`
- `visual_alignment`
- `visual_model_version`
- `shadow_processed_at`

Tabelas candidatas:

- `trade_decisions`
- `scanner_cycle_logs`
- tabela nova tipo `trade_visual_contexts`

Melhor direcao:

- manter a imagem e o shadow como entidade de ciclo, nao espalhar campos demais sem necessidade

## Mudancas de storage

O melhor arranjo inicial e:

1. bridge grava PNG local
2. agent-local faz upload assincrono
3. backend grava referencia e hash

Motivo:

- evita depender do MT5 falando direto com storage
- facilita retry e reprocessamento
- reduz risco de perda de auditoria

## Mudancas no agent-local

Responsabilidades novas:

- identificar snapshot + screenshot do mesmo ciclo
- enviar metadata visual junto do payload
- subir arquivo para storage
- reter fila local se upload falhar
- marcar shadow mode ligado ou desligado por instancia

## Mudancas no bridge MT5

Responsabilidades novas:

- capturar screenshot do chart
- padronizar nome do arquivo
- garantir correlacao com o snapshot
- opcionalmente registrar dimensao e hash basico

Observacao importante:

- o bridge nao deve depender de stream continuo no MVP
- a captura deve ser pontual por ciclo ou por evento relevante
- isso reduz custo, privacidade exposta e volume de storage

## Mudancas na pagina de instalacao

## Estado atual observado

A pagina atual de instalacao ja oferece escolhas, mas ainda com semantica antiga e conflituosa.

Arquivos diretamente impactados:

- `web/src/app/app/instalacao/page.tsx`
- `web/src/components/app/mt5-credentials-generator.tsx`
- `web/src/components/app/mt5-robot-instances-panel.tsx`
- `web/src/components/app/mt5-connection-checker.tsx`

## Estado desejado

### Passo 1 - escolher tipo de robo

Opcoes:

- Oficial Bridge
- Visual Assistido
- Laboratorio Python

### Passo 2 - validar plano

Se o plano nao permitir:

- mostrar bloqueio claro
- explicar o que muda ao ativar Pro

### Passo 3 - baixar pacote por instancia

O pacote deve vir com:

- agent-local
- mt5
- config pronto
- tipo do robo ja embutido
- flags de visual shadow conforme o plano

## Fluxo de entrada e saida validado para o projeto

## Entrada

1. MT5 gera snapshot
2. MT5 gera screenshot
3. agent-local agrega
4. backend decide
5. backend grava shadow

## Saida

1. backend gera comando oficial
2. agent-local grava command
3. MT5 executa
4. feedback retorna
5. dashboard atualiza estado operacional e visual

## Ordem correta de implantacao

### Gate 0 - arquitetura bloqueante

- declarar oficialmente que o caminho alvo e `agent-local + bridge`
- rebaixar o fluxo HTTP direto a legado em transicao
- ajustar documentacao da instalacao para nao conflitar
- definir `cycle_id`, contrato do agente e ownership do pipeline visual

Sem esse gate fechado, nenhuma PR de visual segue para entrega externa.

### Entrega 1 - infraestrutura silenciosa

- exportar PNG junto do snapshot JSON
- padronizar `cycle_id`
- agent-local sobe artefatos e metadata
- backend persiste referencia e hash
- dashboard interno mostra miniatura e correlacao do ciclo

Nenhuma analise visual ainda.

### Entrega 2 - shadow fechado interno

- pipeline visual processa imagem
- backend grava `visual_context`, `visual_quality_score` e `visual_alignment`
- equipe interna valida alinhamento entre leitura estruturada e visual
- usuario final ainda nao recebe a promessa comercial completa da feature

### Entrega 3 - produto Pro controlado

- tela de instalacao permite escolher entre `Robo Integrado` e `Robo Hibrido Visual`
- plano Pro+ libera o robo visual
- auditoria e ao vivo passam a mostrar bloco visual para clientes autorizados
- divergencia visual ganha semantica explicita no dashboard

### Entrega 4 - computer use assistido

- modulo separado para setup, diagnostico e recuperacao guiada
- sem dependencia no caminho oficial de execucao
- com lock, kill switch e aprovacao humana quando aplicavel

## Riscos principais

### Risco 1 - misturar duas arquiteturas de conectividade

Se a raiz mantiver por muito tempo o fluxo HTTP direto e o fluxo bridge, a implantacao visual vira retrabalho.

### Risco 2 - tratar leitura visual como motor principal cedo demais

Isso reduz previsibilidade e dificulta teste e auditoria.

### Risco 3 - inflar o dashboard sem semantica clara

Se o painel apenas jogar imagens e eventos sem hierarquia, o usuario perde clareza.

### Risco 4 - liberar o recurso em plano errado

Visual shadow tende a custar mais em processamento, storage e suporte; faz sentido ficar em Pro+.

### Risco 5 - expor o visual antes de medir alinhamento real

Se o produto abrir o robo hibrido visual cedo demais, o usuario pode interpretar a camada visual como autoridade operacional quando ela ainda esta em calibracao.

### Risco 6 - deixar o entitlement espalhado em codigo solto

Sem feature flags formais por plano, o gating vai vazar para frontend, backend, empacotamento e dashboard de forma inconsistente.

## Decisoes recomendadas

1. manter o motor estruturado como autoritativo
2. usar leitura visual primeiro em shadow mode
3. vender o `Robo Hibrido Visual` como upgrade Pro+
4. mostrar dupla leitura no dashboard como diferencial perceptivel
5. usar computer use apenas depois, para setup e suporte assistido
6. tratar a Fase 0 como gate bloqueante, nao como observacao
7. implementar feature flags SaaS antes do rollout comercial amplo

## Definicao de pronto da primeira entrega util

Uma entrega inicial ja valiosa deve permitir:

1. o MT5 exporta JSON e PNG no mesmo ciclo
2. o backend grava ambos com o mesmo `cycle_id`
3. o dashboard mostra preview da imagem no registro da decisao
4. a auditoria mostra leitura oficial e bloco visual shadow
5. o usuario escolhe o tipo de robo na instalacao
6. o recurso visual so aparece para Pro ou Scale
7. a divergencia visual tem semantica definida no dashboard e na auditoria
