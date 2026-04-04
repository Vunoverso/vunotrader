# 2026-04-03 - Etapa 2 - modulos Price Action no backend

## Data
- 2026-04-03

## Objetivo
- Implementar a Etapa 2 do VPE no backend, usando o snapshot expandido com candles para detectar setup, zona e estrutura antes de cair no motor legado.

## Arquivos impactados
- backend/app/price_action_patterns.py
- backend/app/price_action_zones.py
- backend/app/price_action_structure.py
- backend/app/price_action.py
- backend/app/decision_engine.py
- backend/app/models.py
- backend/app/routes/agent.py
- backend/tests/test_price_action_engine.py
- backend/tests/test_operational_flow.py

## Decisao tomada
- Foi implementada uma camada Price Action V1 com integracao leve no decision_engine.
- O fluxo agora segue esta ordem:
  1. bloqueio por spread alto
  2. tentativa de decisao por Price Action quando houver candles suficientes
  3. fallback para o motor legado EMA + RSI quando nao houver confluencia valida
- O contrato de decisao passou a expor analysis opcional com:
  - engine usado
  - setup detectado
  - zona
  - estrutura
  - score
  - memoria recente

## Regras implementadas nesta etapa
- Patterns:
  - pin bar
  - engulfing
  - inside bar
- Zones:
  - support
  - resistance
  - range_low
  - range_high
  - mid_range
- Structure:
  - bullish
  - bearish
  - range
  - neutral
  - breakout_bias local

## Validacao
- Testes executados com sucesso:
  - tests/test_price_action_engine.py
  - tests/test_operational_flow.py
- Casos cobertos:
  - compra por pin bar bullish em suporte
  - venda por pin bar bearish em resistencia
  - fallback legado quando nao existe setup Price Action

## Riscos e observacoes
- Esta versao ainda e heuristica. Ela nao cobre ordem de blocos, liquidez, BOS/CHOCH formal, nem score multi-fator completo do VPE final.
- O motor ainda nao persiste nem exibe no painel uma leitura visual detalhada de setup/zone/structure, embora o campo analysis ja deixe isso pronto no payload.
- Inside bar ainda esta com regra conservadora e depende do contexto de estrutura para nao gerar falso positivo cedo demais.

## Proximos passos
- Persistir e exibir setup, zona e score no painel operacional.
- Evoluir estrutura para BOS, CHOCH, swing map e confirmacao HTF mais forte.
- Adicionar zonas derivadas de toques repetidos e rejeicao, em vez de apenas extremos recentes.
- Expandir os testes com cenarios de lateralizacao e falso rompimento.