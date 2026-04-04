# 2026-04-04 - MT5 com computer use e visao grafica como camada complementar

## Data

2026-04-04

## Objetivo

Registrar a avaliacao tecnica do material encontrado em `n8n-skills-main` sobre:

- `computer-use-agents`
- `computer-vision-expert`
- `browser-automation-mcp`

e definir como isso pode evoluir o Vuno para analise grafica real no MT5 sem quebrar a direcao arquitetural ja escolhida.

## Contexto consolidado

O workspace ja contem dois sinais importantes:

1. a colecao `n8n-skills-main` tem skill explicita para `computer-use-agents`, voltada a controle de desktop por captura de tela, raciocinio visual e acao por mouse/teclado;
2. a arquitetura mais aderente do produto ja esta convergindo para `agent-local + bridge por arquivos + snapshot do MT5`, e nao para automacao de browser nem para HTTP direto saindo do EA.

Isso deixa claro que, para o caso MT5, `computer use` e mais aderente do que browser automation.

Ao mesmo tempo, essa capacidade nao deve substituir o contrato operacional principal do robo.

## Decisao

Adotar `computer use` e `visao computacional` como camada complementar de percepcao, diagnostico e assistencia operacional do MT5.

Nao adotar isso, neste momento, como caminho oficial de execucao de ordens.

Fluxo oficial preservado:

- EA/bridge local gera snapshot estruturado
- agente local envia payload ao backend
- backend decide
- MT5 executa pela ponte oficial

Fluxo complementar proposto:

- MT5 exporta imagem do grafico junto do snapshot JSON
- agente local ou worker dedicado analisa imagem + snapshot estruturado
- o resultado visual enriquece contexto, auditoria, shadow mode e diagnostico
- computer use fica reservado para setup, validacao e recuperacao assistida de interface

## Motivos da decisao

### O que `computer use` resolve bem

- leitura de elementos visuais reais do MT5 que nao aparecem no snapshot numerico
- validacao de estado da interface durante instalacao e suporte
- deteccao de problemas operacionais no desktop do usuario ou VPS
- futura leitura de objetos graficos, marcacoes e contexto visual do chart

### O que `computer use` nao deve virar agora

- motor principal de clique em `Buy` e `Sell` no terminal
- substituto da bridge local por arquivos
- dependencia obrigatoria para o robo operar

### Razoes para nao colocar execucao principal via UI

- fragilidade por resolucao, escala, tema e layout do Windows/MT5
- pior rastreabilidade comparado ao contrato atual por snapshot
- maior superficie de risco operacional e de seguranca
- dificuldade maior de teste deterministico
- necessidade de sandbox obrigatorio, conforme a skill `computer-use-agents`

## Encaixe com a arquitetura atual

Essa direcao reforca, e nao conflita com, o plano de 2026-04-04 baseado em `vuno-robo`.

A ordem correta continua sendo:

1. consolidar pacote por instancia
2. consolidar agente local + bridge
3. estabilizar contrato operacional `/api/agent/*`
4. so depois enriquecer o snapshot com imagem e contexto visual

Ou seja: a visao grafica entra depois da conectividade correta, nao antes.

## Implementacao recomendada por fases

### Fase 1 - Imagem do grafico como extensao do snapshot

Objetivo:

- capturar o chart real do MT5 sem depender ainda de agent clicando na interface

Direcao tecnica:

- usar recurso nativo do MT5 para exportar screenshot do grafico no mesmo ciclo do snapshot
- gravar a imagem na pasta da bridge com nome correlacionado ao snapshot JSON
- incluir no payload metadados como:
  - `chart_image_file`
  - `chart_image_captured_at`
  - `chart_image_hash`

Beneficios:

- auditoria visual por trade
- dataset real para treinar/classificar setups
- comparacao futura entre leitura numerica e leitura visual

### Fase 2 - Shadow mode visual

Objetivo:

- analisar a imagem sem influenciar a execucao real inicialmente

Direcao tecnica:

- criar worker ou etapa opcional no agente para rodar classificacao visual
- gerar `visual_context`, `visual_setup_guess`, `visual_quality_score` e `visual_rationale`
- salvar isso separado da decisao principal

Beneficios:

- valida a utilidade da camada visual sem mexer no fluxo de ordens
- reduz risco de regressao operacional

### Fase 3 - Copiloto de setup e suporte via computer use

Objetivo:

- usar desktop control para instalacao, verificacao e suporte assistido

Casos aderentes:

- conferir se o EA foi anexado ao grafico correto
- validar se AutoTrading esta ativo
- verificar se a pasta da bridge esta sendo atualizada
- detectar mensagens visuais de erro no terminal
- orientar correcoes de setup no VPS ou maquina local

Regra:

- sempre em modo assistido ou sandboxado
- nunca como requisito para o robo operar no caminho principal

### Fase 4 - Uso avancado de visao no motor

Objetivo:

- decidir, com evidencia real, se vale promover parte do contexto visual para o motor oficial

Condicao para isso:

- a camada visual precisa provar ganho consistente em shadow mode
- a explicabilidade precisa continuar melhor, nao pior
- o custo de processamento precisa ficar controlado

## Arquivos e modulos mais provaveis de impacto futuro

- `mt5/VunoRemoteBridge.mq5`
- `mt5/vuno-bridge/*`
- `agent-local/app/main.py`
- `agent-local/app/bridge.py`
- rotas `/api/agent/*` do backend principal
- persistencia de auditoria e storage de imagens

## Alternativas avaliadas

### 1. Usar browser automation como base para MT5

Descartado porque MT5 e aplicacao desktop, e browser automation nao resolve o ponto principal.

### 2. Fazer computer use clicar ordens direto como fluxo oficial

Descartado neste momento porque gera mais fragilidade do que valor no estagio atual do produto.

### 3. Ignorar totalmente a camada visual e seguir so com snapshot numerico

Nao adotado como direcao final porque o proprio `vuno-robo` ja sinaliza valor futuro em anexar imagem do chart ao snapshot.

## Riscos e observacoes

- a skill `computer-use-agents` reforca que sandboxing e obrigatorio; isso vale especialmente se houver qualquer controle real de desktop
- visao computacional boa para MT5 nao exige, no primeiro passo, agente clicando na tela; imagem exportada pelo proprio MT5 ja entrega grande parte do ganho
- o maior salto de valor no curto prazo esta em `chart screenshot + shadow visual`, nao em `desktop clicking`
- se a camada visual entrar cedo demais no caminho de execucao, o sistema corre risco de ficar menos auditavel e menos previsivel

## Proximos passos

1. adicionar ao plano tecnico da raiz uma subtarefa para exportacao de screenshot junto do snapshot
2. definir formato de armazenamento das imagens: local temporario + upload posterior ou upload direto pelo agente
3. desenhar schema de auditoria para `visual_context` e `visual_rationale`
4. implementar primeiro em shadow mode antes de qualquer decisao operacional baseada em imagem
