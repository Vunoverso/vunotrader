Data: 2026-04-04

## Objetivo

Concluir a etapa seguinte da integracao SaaS iniciada a partir do sistema importado `robotrademeta5`, expondo a leitura de assinatura no painel estatico atual, aplicando gate visual para modulos ainda nao liberados e entregando um painel admin SaaS funcional sem mexer no motor Price Action / VPE.

## Arquivos impactados

- `backend/app/admin_saas_store.py`
- `backend/app/admin_saas_activity_store.py`
- `backend/app/routes/admin_saas.py`
- `backend/app/routes/auth.py`
- `backend/app/deps.py`
- `backend/app/models.py`
- `backend/app/main.py`
- `backend/migrations/sqlite/0011_platform_admin_and_plan_limits.sql`
- `backend/migrations/postgres/0011_platform_admin_and_plan_limits.sql`
- `backend/migrations/sqlite/0012_plan_changes_and_billing_events.sql`
- `backend/migrations/postgres/0012_plan_changes_and_billing_events.sql`
- `backend/tests/test_admin_saas.py`
- `backend/static/index.html`
- `backend/static/js/saas-admin.js`

## Decisao tomada

Foi escolhida a rota de extensao incremental do painel estatico atual:

- manter `backend/static/js/app.js` como nucleo do painel operacional
- acoplar a camada SaaS por fora com um arquivo dedicado `saas-admin.js`
- expor o estado da assinatura no cabecalho e no dashboard
- bloquear visualmente o Historico enquanto o tenant estiver apenas em trial
- criar um admin SaaS inicial com bootstrap controlado em desenvolvimento, metricas e catalogo de planos
- expor faturamento e historico de mudancas de plano no mesmo admin estatico
- endurecer o gating da sidebar para travar modulo pago antes da navegacao

Motivo da escolha:

- reduz risco de regressao numa SPA ja em uso
- preserva o fluxo operacional do robo e das protecoes
- evita migracao prematura para outro frontend agora
- entrega o valor SaaS visivel imediatamente sem tocar no motor de decisao

## Alternativas descartadas

- editar profundamente `backend/static/js/app.js`: descartado porque aumentaria o risco de regressao no painel operacional
- portar agora o admin em Next.js do projeto importado: descartado porque a base atual ainda entrega o painel estatico pelo backend FastAPI
- liberar o Historico no trial por enquanto: descartado porque o gate visual e parte central da validacao do modelo SaaS nesta etapa

## Implementacao executada

### Backend admin SaaS

- adicionado suporte a `is_platform_admin` no contexto autenticado e na resposta de sessao
- criado bootstrap local de admin SaaS, restrito ao ambiente de desenvolvimento e bloqueado quando ja existe admin na base
- criado catalogo admin de planos com leitura, criacao e atualizacao
- criada visao resumida com metricas de tenants, planos, trials, assinaturas e MRR estimado
- adicionada tabela `saas_plan_limits` com seed inicial para starter, pro e scale
- adicionada tabela `plan_changes` com registro estruturado de criacao e alteracao de planos
- adicionada tabela `billing_events` para formar a trilha inicial de faturamento
- o onboarding de trial agora grava evento `subscription_created` em `billing_events`
- criados endpoints admin para:
  - leitura do historico de mudancas de plano
  - leitura do feed de faturamento com filtros por status e provedor

### Frontend estatico

- incluido resumo de assinatura no topo da sessao e no dashboard
- incluido gate visual por plano para o modulo Historico
- incluido menu `Admin SaaS` com exibicao condicional
- o botao `Historico` na sidebar agora fica travado antes do clique quando o plano ainda nao libera o modulo
- criado painel admin com:
  - bootstrap local do primeiro admin
  - metricas da camada SaaS
  - formulario de criacao de plano
  - catalogo editavel de planos
  - lista recente de assinaturas
- expandido o painel admin com:
  - secao de faturamento
  - metricas de eventos, receita confirmada, falhas, reembolsos e provedores
  - secao de historico de planos com contagem por tipo de mudanca
- adicionada regra global `[hidden] { display: none !important; }` para corrigir o conflito entre o atributo `hidden` e componentes com `display: grid`, que estava deixando o conteudo bloqueado visivel por baixo do gate

## Riscos e observacoes

- o gate reforcado cobre a sidebar do Historico e a view interna, mas outras areas pagas ainda precisam da mesma politica
- o bootstrap admin foi mantido apenas para desenvolvimento; a elevacao em producao precisa de fluxo proprio e auditavel
- o painel admin agora cobre o feed interno de faturamento e o historico de alteracoes de plano, mas ainda nao cobre cobranca real, upgrade, downgrade ou conciliacao com gateway
- o faturamento atual e interno e orientado a rastreabilidade; integracao com gateway comercial continua fora deste escopo

## Validacao executada

- verificacao estatica sem erros em:
  - `backend/static/index.html`
  - `backend/static/js/saas-admin.js`
- testes automatizados aprovados:
  - `backend/tests/test_admin_saas.py`
  - `backend/tests/test_subscription_saas.py`
  - `backend/tests/test_operational_flow.py`
- validacao manual em navegador com servidor local limpo na porta `8010`:
  - login restaurou leitura de assinatura
  - trial `Starter` apareceu no topo e no card do dashboard
  - modulo Historico exibiu gate visual e ocultou o conteudo bloqueado
  - bootstrap admin SaaS promoveu a conta local
  - painel admin carregou metricas e catalogo
  - criacao manual de um plano `enterprise-test` apareceu no catalogo
- validacao manual adicional em navegador com servidor limpo na porta `8011`:
  - sidebar passou a sinalizar `Historico` como modulo travado ainda no menu
  - admin exibiu feed de faturamento com eventos `subscription_created`
  - criacao real de plano no painel atualizou a secao `Historico de planos`
  - metricas do historico passaram a contar mudancas imediatamente apos a criacao

## Proximos passos

1. aplicar limites de plano tambem no backend operacional, nao apenas no painel visual
2. definir gating por recurso para Protecoes avancadas, IA e modulos administrativos adicionais
3. abrir a nova superficie publica do produto com Home, Login, Cadastro, Planos e Trial, deixando o painel atual como area interna de operacao
4. planejar migracao futura do painel estatico para app web dedicada apenas depois de estabilizar assinaturas, limites e administracao