# 2026-04-04 - Plano de melhoria do sistema atual com base no vuno-robo

## Data

2026-04-04

## Objetivo

Definir um plano pragmático para melhorar o sistema atual da raiz do projeto usando como referência o que ficou melhor resolvido em `robovuno26` e no pacote extraído `vuno-robo`, principalmente em:

- instalação do robô
- comunicação com o MT5
- gestão de instâncias
- sincronismo operacional entre painel, backend e executor
- redução de pontos frágeis na autenticação e no handshake

O objetivo não é substituir a base atual por um drop-in do `robovuno26`, e sim portar os blocos certos na ordem correta.

## Diagnóstico consolidado

### O que está melhor no `vuno-robo`

- o usuário baixa um pacote já pronto por instância
- o token já vai embutido em `runtime/config.json`
- o MT5 não precisa falar HTTP direto com o backend
- o agente local faz a ponte entre arquivos locais e API
- o backend resolve a identidade do robô por token único no header
- a bridge local reduz fricção de setup no MT5
- a instalação deixa de depender de copiar múltiplos IDs manualmente no EA

### O que está pior no sistema atual da raiz

- o onboarding ainda exige `RobotID`, `RobotToken`, `UserID` e `OrganizationID`
- o EA depende de URL remota nas permissões do MT5
- o fluxo atual mistura dois modelos de integração:
  - EA HTTP direto para backend
  - brain Python separado por socket
- a inteligência está fragmentada entre:
  - `backend/app/core/signal_engine.py`
  - `vuno_core/decision_engine.py`
  - `vunotrader_brain.py`
- a jornada de instalação ainda é mais frágil que a do pacote por instância

### Decisão arquitetural

O caminho recomendado é adotar no sistema atual a arquitetura de acesso do `vuno-robo`, mantendo a evolução do produto principal na raiz.

Em termos práticos:

- portar o modelo de pacote por instância
- portar o agente local e a bridge por arquivos
- portar o EA `VunoRemoteBridge.mq5` como conector principal
- unificar o contrato backend <-> agente <-> MT5
- reduzir o fluxo antigo baseado em HTTP direto do EA

Nao adotar agora:

- substituição completa do backend atual pela base do `robovuno26`
- convivência longa entre dois motores de decisão principais
- manutenção indefinida do handshake com `user_id` e `organization_id` no payload do MT5

## Plano por fases

### Fase 0 - Congelar a direção técnica

Objetivo:

- parar de expandir dois caminhos concorrentes de comunicação com MT5

Entregas:

- declarar `vuno-robo` como arquitetura de referência para instalação e conectividade MT5
- declarar o fluxo HTTP direto do EA atual como legado em transição
- documentar que a raiz do projeto passa a convergir para `agent-local + bridge + token único`

Arquivos principais envolvidos:

- `evolucao/*`
- `projeto/versao-melhorada-simples.md`
- `README.md`

Critério de pronto:

- documentação do projeto deixa explícito qual é o fluxo oficial e qual é o fluxo legado

### Fase 1 - Portar a camada de instalação sem trocar ainda o motor

Objetivo:

- melhorar a experiência de instalação imediatamente, sem depender da troca completa da inteligência

Entregas:

- adicionar na base atual um empacotador por instância equivalente ao `agent_package.py`
- gerar zip com:
  - `agent-local/`
  - `mt5/`
  - `runtime/config.json` já preenchido
  - `LEIA-PRIMEIRO.txt`
- substituir na UI atual a etapa de copiar múltiplas credenciais por um fluxo de download de pacote pronto

Arquivos de referência:

- `robovuno26/backend/app/agent_package.py`
- `vuno-robo/LEIA-PRIMEIRO.txt`
- `vuno-robo/agent-local/runtime/config.json`

Arquivos prováveis de destino:

- `backend/app/...` ou rota equivalente no backend atual
- `web/src/app/app/instalacao/page.tsx`
- `web/src/components/app/mt5-credentials-generator.tsx`
- `web/src/components/app/mt5-robot-instances-panel.tsx`

Critério de pronto:

- o usuário baixa um pacote pronto da instância e não precisa copiar `UserID` e `OrganizationID` no MT5

### Fase 2 - Portar a ponte local com agente e bridge por arquivos

Objetivo:

- remover a dependência do EA falar HTTP direto com o backend

Entregas:

- incorporar `agent-local` como componente oficial da raiz do projeto
- criar contrato backend para:
  - `GET /api/agent/runtime-config`
  - `POST /api/agent/decision`
  - `POST /api/agent/trade-feedback`
  - `POST /api/agent/symbol-catalog`
  - `POST /api/agent/heartbeat`
- adotar `X-Robot-Token` como principal identificador do robô
- manter o fluxo HTTP direto apenas como fallback temporário até a migração terminar

Arquivos de referência:

- `vuno-robo/agent-local/app/*`
- `robovuno26/backend/app/routes/agent.py`
- `robovuno26/backend/app/deps.py`
- `vuno-robo/mt5/VunoRemoteBridge.mq5`

Arquivos prováveis de destino:

- `backend/app/api/routes/*` ou nova área `backend/app/routes/agent.py`
- `web/public/downloads/*`
- `agent-local/*`
- `mt5/VunoRemoteBridge.mq5`

Critério de pronto:

- o executor MT5 opera via bridge local e o backend recebe apenas o tráfego do agente

### Fase 3 - Unificar a inteligência oficial

Objetivo:

- eliminar a fragmentação atual entre motor cloud, brain separado e núcleo ML compartilhado

Decisão recomendada:

- escolher um motor oficial para o fluxo MT5 do produto
- manter os demais apenas como laboratório ou utilitário técnico

Direção proposta:

- usar a linha `runtime_policy + price_action + position_manager` do `robovuno26` como motor oficial para o fluxo novo com agente
- manter `vuno_core/decision_engine.py` apenas se houver decisão explícita de continuar oferecendo modo ML separado
- remover do caminho principal o acoplamento atual entre o EA HTTP e `backend/app/core/signal_engine.py`

Critério de pronto:

- existe um único contrato oficial de decisão para o robô conectado ao MT5

### Fase 4 - Migrar o painel para o novo contrato operacional

Objetivo:

- fazer o painel refletir a arquitetura nova e reduzir falso negativo de conexão

Entregas:

- trocar a UI de instalação para o conceito de pacote por instância
- exibir bridge, heartbeat, símbolos detectados e status do agente
- separar o que é:
  - instalação do conector
  - estado operacional do robô
  - parâmetros de risco
- manter o dashboard atual, mas alinhado ao novo fluxo de heartbeat por agente

Referências úteis:

- `robovuno26/backend/static/js/app.js`
- `robovuno26/backend/app/routes/monitoring.py`
- `web/src/app/app/instalacao/page.tsx`

Critério de pronto:

- o painel deixa de depender de interpretação do usuário sobre URLs, IDs e permissões do MT5

## Ordem recomendada de implementação

1. Pacote por instância
2. Agente local e rotas `/api/agent`
3. EA bridge local como fluxo oficial
4. Depreciação do EA HTTP direto
5. Unificação do motor de decisão
6. Ajuste final do painel e da instalação

## Blocos que podem ser reaproveitados quase diretamente

- `vuno-robo/agent-local/*`
- `vuno-robo/mt5/*`
- `robovuno26/backend/app/agent_package.py`
- `robovuno26/backend/app/routes/agent.py`
- `robovuno26/backend/app/deps.py` na parte de token por header

## Blocos que exigem adaptação antes de portar

- `robovuno26/backend/app/routes/monitoring.py`
  - precisa alinhar com o modelo de assinatura do produto principal
- `robovuno26/backend/static/*`
  - o produto principal usa Next.js, não painel estático servido por FastAPI
- `robovuno26/backend/app/decision_engine.py` e `price_action.py`
  - precisam ser avaliados contra a estratégia oficial do produto antes de virarem o motor final

## Blocos que não devem ser levados como estão

- payload antigo do sistema atual com `user_id` e `organization_id` vindos do MT5
- dependência de URL remota configurada manualmente no MT5 como fluxo principal
- manutenção paralela indefinida de `signal_engine.py`, `vunotrader_brain.py` e do fluxo EA HTTP direto como caminhos equivalentes

## Riscos e observações

- o pacote `vuno-robo` encontrado no workspace está apontando para `http://127.0.0.1:8000`; ele serve como referência de arquitetura e empacotamento, não como pacote final de produção
- a migração não deve copiar o `robovuno26` inteiro para a raiz; isso aumentaria duplicação e risco de regressão
- a troca da comunicação com MT5 deve vir antes da troca completa da inteligência, porque hoje o gargalo mais visível está na conectividade e no onboarding
- a UI atual de geração de credenciais pode continuar existindo apenas como etapa interna de criação do pacote, não como experiência final do usuário

## Próximos passos imediatos

1. criar um plano técnico de extração da Fase 1 com lista de arquivos fonte e destino
2. definir em qual backend da raiz entrarão as rotas `/api/agent`
3. escolher se o primeiro pacote da raiz será servido pelo backend FastAPI atual ou por rota no Next.js
4. decidir formalmente qual motor permanecerá como oficial no fluxo MT5 após a migração da conectividade
