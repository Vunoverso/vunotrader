# 2026-04-04 - Robo Hibrido Visual MT5 no plano Pro

## Data

2026-04-04

## Objetivo

Registrar o refinamento do plano do robo visual para o Vuno com foco em:

- produto Pro e Scale
- leitura hibrida estruturada + screenshot
- governanca operacional
- dashboard e auditoria
- ordem correta de implantacao

## Arquivo principal refinado

- `projeto/implantacao-mt5-visao-shadow-e-duplo-robo.md`

## Ajustes decisivos feitos no plano

### 1. Fase 0 passou a ser gate bloqueante

O plano anterior reconhecia a divergencia entre o fluxo HTTP direto e a direcao `agent-local + bridge`, mas isso ainda podia ser lido como contexto.

Agora ficou explicito:

- nenhuma entrega visual para usuario segue antes da arquitetura oficial estar congelada

### 2. `cycle_id` foi promovido a contrato tecnico obrigatorio

Foi definida a necessidade de:

- gerar o `cycle_id` no MT5
- usar o mesmo identificador em JSON, PNG, payload do agente, backend e auditoria

### 3. Divergencia visual ganhou politica operacional

O plano passou a definir estados e comportamento para:

- `aligned`
- `divergent_low`
- `divergent_high`
- `error`

Com a regra central:

- a camada visual nao bloqueia nem reescreve ordem no MVP

### 4. O nome do produto foi reorientado

Foi consolidada a nomenclatura mais comercial e clara:

- `Robo Integrado`
- `Robo Hibrido Visual`

### 5. A principal lacuna de SaaS foi explicitada

Ficou registrado que a base atual tem limites por plano como `max_bots`, mas ainda nao possui feature flags formais para liberar corretamente:

- robo visual
- shadow mode
- storage visual expandido
- assistencia de desktop

## Alternativas descartadas

- expor o robo visual cedo demais ao usuario final antes de medir alinhamento real
- tratar divergencia visual apenas como dado decorativo sem semantica operacional
- deixar entitlement do robo visual espalhado em condicionais soltas por plano no frontend

## Riscos e observacoes

- o maior risco nao e a captura de screenshot em si, e sim implantar o produto visual antes de fechar a arquitetura de conectividade
- o segundo maior risco e a interpretacao errada do usuario, achando que a leitura visual ja manda na ordem quando ela ainda esta em shadow mode
- sem feature flags formais, o gating comercial do novo robo fica fraco e inconsistente

## Proximos passos

1. transformar o plano refinado em backlog tecnico com criterios de aceite por entrega
2. decidir schema de feature flags SaaS
3. iniciar a infraestrutura silenciosa do screenshot somente apos o gate arquitetural
4. ajustar a UX da instalacao para `Robo Integrado` vs `Robo Hibrido Visual`

## Atualizacao da sessao - backlog, contrato e revisao inicial de UI

### Entregas realizadas

- criado backlog tecnico por sprint em `projeto/2026-04-04-backlog-sprints-robo-hibrido-visual.md`
- criado contrato final de dados em `projeto/2026-04-04-contrato-dados-robo-hibrido-visual.md`
- iniciada a revisao de UX em:
	- `web/src/app/app/instalacao/page.tsx`
	- `web/src/components/app/robot-installation-lanes.tsx`
	- `web/src/app/app/dashboard/page.tsx`
	- `web/src/components/app/robot-product-dashboard-lanes.tsx`
	- `web/src/components/app/mt5-connection-checker.tsx`

### Decisao aplicada

- a UI ja passa a refletir a organizacao de produto em `Robo Integrado` e `Robo Hibrido Visual`
- sem fingir que o backend ja possui `robot_product_type` ou feature flags completos
- o painel mostra a linha visual como rollout controlado, nao como funcionalidade pronta
