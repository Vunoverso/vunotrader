# 2026-04-04 - Fase 1 com pacote por instancia e bridge local

## Data

2026-04-04

## Objetivo

Executar a Fase 1 do plano de migracao inspirado no vuno-robo:

- trocar a instalacao manual por download de pacote pronto
- reduzir a dependencia de copiar IDs e token no MT5
- remover a necessidade de URL permitida no MetaTrader 5
- reaproveitar o backend atual sem antecipar ainda a fase de rotas /api/agent

## Arquivos impactados

- web/package.json
- web/package-lock.json
- web/src/app/api/mt5/robot-package/route.ts
- web/src/lib/mt5/package-template.ts
- web/src/lib/mt5/package-archive.ts
- web/src/components/app/mt5-credentials-generator.tsx
- web/src/components/app/mt5-robot-instances-panel.tsx
- web/src/app/app/instalacao/page.tsx
- backend/app/api/routes/mt5.py
- vuno-robo/agent-local/app/api_client.py
- vuno-robo/agent-local/app/bridge.py
- vuno-robo/agent-local/app/config.py
- vuno-robo/agent-local/app/legacy_mt5_api.py
- vuno-robo/agent-local/app/main.py
- vuno-robo/agent-local/app/memory.py
- vuno-robo/agent-local/config.example.json
- vuno-robo/agent-local/runtime/config.json
- vuno-robo/mt5/vuno-bridge/vuno-bridge-io.mqh

## Decisao

Foi escolhido um caminho intermediario e pragmatico para a Fase 1:

- gerar o pacote pronto por instancia no app web atual
- embutir no pacote os identificadores que o backend atual ainda exige
- adaptar o agent-local do template para traduzir bridge local -> /api/mt5/*
- manter o fluxo /api/agent como proxima fase, nao como pre-requisito desta entrega

Com isso, o usuario passa a baixar um zip com:

- agent-local
- bridge local do MT5
- runtime/config.json preenchido
- LEIA-PRIMEIRO com instrucoes do fluxo novo

## O que mudou tecnicamente

### 1. Pacote por instancia

Foi adicionada a rota web que:

- cria uma nova instancia do robo
- gera token unico
- monta zip a partir do template vuno-robo
- injeta config e instrucoes da instancia
- pausa instancias ativas anteriores do mesmo usuario

### 2. Adaptacao do agent-local ao backend atual

O template do agent-local deixou de depender do contrato /api/agent para esta fase e passou a:

- enviar snapshots para /api/mt5/signal
- enviar heartbeat para /api/mt5/heartbeat
- reportar trade-opened para /api/mt5/trade-opened
- reportar outcome para /api/mt5/trade-outcome

Foi criada memoria local para vincular:

- decisao pendente por simbolo
- ticket aberto
- decisao ativa ate o feedback

### 3. Bridge local com mais consistencia

Foi ajustado o template para:

- escrever command.json e runtime.settings.json de forma atomica
- aceitar SL/TP em preco no comando de abertura
- carregar comentario com decision_id no comando enviado ao EA

### 4. Backend atual reaproveitado

O endpoint /api/mt5/signal passou a expor:

- stop_loss
- take_profit

Isso permite que a bridge local execute usando os mesmos niveis calculados pelo motor atual.

### 5. UI de instalacao

A pagina de instalacao foi atualizada para:

- promover o fluxo por pacote pronto
- remover instrucoes antigas de URL permitida
- parar de expor a copia manual de UserID e OrganizationID como caminho principal

## Alternativas descartadas

1. Portar ja nesta fase todo o contrato /api/agent do robovuno26.
Motivo: aumentaria escopo e risco antes de validar a melhora principal de onboarding e conectividade.

2. Gerar somente um zip estetico, sem adaptar o agent-local ao backend atual.
Motivo: entregaria UX melhor, mas manteria o pacote sem funcionalidade real na base atual.

3. Continuar usando apenas o EA HTTP direto e esconder os IDs manualmente.
Motivo: nao resolveria o problema central de friccao e instabilidade do fluxo atual.

## Riscos e observacoes

- A Fase 1 ainda depende do contrato legado /api/mt5 do backend atual.
- O fluxo novo reduz o atrito de instalacao, mas a consolidacao arquitetural final ainda depende da Fase 2.
- O template do vuno-robo foi alinhado ao pacote oficial para evitar divergencia entre fonte e artefato gerado.
- O fluxo EA HTTP direto continua existindo como legado durante a transicao.

## Proximos passos

1. Criar as rotas /api/agent na raiz para eliminar a traducao temporaria do agent-local.
2. Migrar o painel operacional para status explicitos de bridge, agente e simbolos detectados.
3. Deprecar a instalacao antiga baseada em RobotID/RobotToken no EA HTTP direto.