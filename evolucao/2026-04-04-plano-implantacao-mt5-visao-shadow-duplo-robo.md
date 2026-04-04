# 2026-04-04 - Plano de implantacao MT5 com visao shadow e duplo robo

## Data

2026-04-04

## Objetivo

Registrar a consolidacao de um plano detalhado para adicionar ao sistema:

- screenshot do grafico MT5 junto do snapshot JSON
- contexto visual em shadow mode
- dois tipos de robo escolhiveis pelo usuario
- gating do robo visual assistido em planos Pro e Scale
- comportamento novo do dashboard e da auditoria

## Arquivo principal criado

- `projeto/implantacao-mt5-visao-shadow-e-duplo-robo.md`

## Validacao de contexto realizada

Foi revisado o material ja existente em:

- `evolucao/2026-04-04-plano-melhoria-com-base-no-vuno-robo.md`
- `evolucao/2026-04-04-mt5-computer-use-visao-grafica.md`
- `projeto/planotrader.md`
- `projeto/versao-melhorada-simples.md`

Tambem foi conferido o estado atual do fluxo em:

- `backend/app/api/routes/mt5.py`
- `web/src/app/app/instalacao/page.tsx`
- `web/src/app/api/mt5/robot-credentials/route.ts`
- `web/src/app/api/mt5/robot-credentials/instances/route.ts`
- `vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh`
- `vuno-robo/agent-local/app/main.py`
- `robovuno26/backend/app/routes/agent.py`

## Conclusoes importantes

### 1. A ideia de dupla leitura faz sentido

Leitura estruturada + leitura visual podem coexistir com muito valor para o usuario.

### 2. A leitura visual nao deve mandar na execucao primeiro

Foi mantida a decisao de usar a camada visual em shadow mode antes de qualquer promocao para motor oficial.

### 3. O dashboard precisa refletir duas camadas distintas

Nao basta mostrar imagem. O painel precisa mostrar:

- leitura oficial
- leitura visual shadow
- alinhamento ou divergencia entre elas

### 4. Existe uma divergencia atual de produto

A raiz ja aponta para convergencia com `agent-local + bridge`, mas a pagina de instalacao ainda traz orientacao forte do fluxo HTTP direto no MT5.

Essa divergencia foi mantida explicita no plano para evitar implantar a camada visual no caminho legado errado.

## Decisao tomada

Seguir a implantacao nesta ordem:

1. congelar a arquitetura de conectividade alvo
2. exportar screenshot no bridge MT5
3. transportar e persistir contexto visual
4. ativar shadow mode visual
5. expor os dois tipos de robo no produto
6. deixar computer use para setup, diagnostico e recuperacao assistida em etapa posterior

## Alternativas descartadas

### 1. Fazer o robo visual executar por interface logo no inicio

Descartado por risco operacional, fragilidade de automacao UI e pior auditabilidade.

### 2. Esperar computer use antes de adicionar imagens

Descartado porque o maior ganho inicial vem de screenshot exportado pelo proprio MT5, sem precisar automacao de desktop ainda.

### 3. Continuar expandindo o fluxo direto em `backend/app/api/routes/mt5.py` como destino final

Nao recomendado como direcao final, porque o plano mais consistente continua sendo o contrato do agente local com bridge.

## Proximos passos

1. revisar a pagina de instalacao para alinhar texto e fluxo com a arquitetura alvo
2. escolher o schema final para persistencia do contexto visual
3. definir os flags de plano para robo visual assistido
4. iniciar a Fase 1 pelo bridge MT5 com exportacao do screenshot e `cycle_id`
