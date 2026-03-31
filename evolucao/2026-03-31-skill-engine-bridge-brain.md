# 2026-03-31 - Integracao Skill Engine <-> Trading Brain (bridge)

## Contexto
Existiam dois blocos fortes no ecossistema:
- Skill Engine (validacao deterministica, governanca e politicas)
- Trading Brain (ML, execucao e aprendizado)

A integracao entre eles nao estava explicita no fluxo de decisao do brain em tempo real.

## Objetivo
Conectar o fluxo de decisao do brain com um Skill Engine externo sem quebrar o comportamento atual quando o servico externo estiver indisponivel.

## Decisao tecnica
Implementada uma bridge opcional no arquivo `vunotrader_brain.py` com dois pontos:
1. `pre-trade`: valida ou ajusta a sugestao do ML antes da execucao.
2. `post-trade`: devolve resultado de execucao para aprendizado cruzado.

A integracao e `best effort` e controlada por variaveis de ambiente. Se o Skill Engine nao responder, o brain segue com governanca local existente.

## Arquivos impactados
- `vunotrader_brain.py`

## Implementacao realizada
- Adicionada configuracao de ambiente:
  - `ENABLE_SKILL_ENGINE`
  - `SKILL_ENGINE_URL`
  - `SKILL_ENGINE_TIMEOUT_SEC`
  - `SKILL_ENGINE_API_KEY`
- Nova classe `SkillEngineBridge` com:
  - `evaluate_pre_trade()`
  - `report_trade_result()`
- Integracao no ciclo `MARKET_DATA`:
  - Brain chama `/pre-trade` com sinal ML, confianca, risco, regime, win_rate e snapshot de features.
  - Decisoes aceitas: `allow`, `block`, `review`, `override`.
  - Em `block/review`: forca `HOLD`.
  - Em `override`: pode ajustar sinal e risco.
- Integracao no ciclo `TRADE_RESULT`:
  - Brain chama `/post-trade` com outcome e contexto para retroalimentar o Skill Engine.
- Enriquecimento da resposta ao MT5:
  - `action`
  - `rationale`
  - `governance` (decision/reason/requires_human)

## Riscos e observacoes
- O endpoint externo precisa respeitar contrato JSON simples para evitar overrides indevidos.
- Timeout curto foi mantido para nao travar ciclo de trading.
- A governanca local permanece como camada de seguranca se o servico externo cair.

## Alternativas avaliadas (nao adotadas agora)
1. Integrar via fila assicrona (Rabbit/Kafka):
   - Nao adotado por aumentar complexidade operacional para o estagio atual.
2. Integrar via banco (polling de regras):
   - Nao adotado por aumentar latencia de decisao e acoplamento a schema.

## Proximos passos
1. Publicar endpoint do Skill Engine com rotas:
   - `POST /pre-trade`
   - `POST /post-trade`
2. Definir contrato de versao para payload de governanca.
3. Criar teste de contrato no `backend/scripts/simulate_mt5_cycle.py` para validar `governance.decision`.
4. Exibir no dashboard quando uma decisao foi bloqueada por governanca externa.
