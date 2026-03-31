# 2026-03-31 - Recommendation Engine MVP orientado a objetivo

## Objetivo
Criar um motor de recomendacao enxuto, com impacto financeiro mensuravel, sem chat opinativo e sem tool selector.

## Decisao
A arquitetura foi reduzida para dois blocos:
1. Recommendation Engine: ranqueia perfis por objetivo.
2. Interface consultiva: traduz a recomendacao para o usuario aprovar.

## Arquivos impactados
- `web/src/app/api/recommendation/config/route.ts`
- `web/src/components/app/recommendation-advisor.tsx`
- `web/src/components/app/parametros-form.tsx`

## Implementacao
### 1. Endpoint `POST /api/recommendation/config`
- Requer usuario autenticado.
- Input:
  - `symbol`
  - `timeframe`
  - `goal` (`max_profit | consistency | low_drawdown`)
- Busca historico real do usuario nos ultimos 90 dias.
- Usa apenas trades com outcome real.
- Exige minimo de 50 pontos para recomendar.

### 2. Presets operacionais
Foram definidos 3 perfis:
- `conservative`
- `balanced`
- `aggressive`

Cada preset gera um patch aplicavel ao formulario com:
- `risk_per_trade_pct`
- `max_drawdown_pct`
- `drawdown_pause_pct`
- `max_consecutive_losses`
- `max_trades_per_day`
- `auto_reduce_risk`
- `per_trade_stop_loss_mode`
- `per_trade_stop_loss_value`
- `per_trade_take_profit_rr`

### 3. Ranking quantitativo
- O motor simula cada perfil sobre o historico real.
- Limita trades por dia conforme o preset.
- Escala PnL conforme risco do preset.
- Calcula:
  - `expected_pnl`
  - `total_pnl`
  - `drawdown_pct`
  - `win_rate`
  - `consistency_score`
- Ranqueia de forma diferente para cada objetivo.

### 4. Memoria global como bonus, nao narrativa
- Se `global_memory_signals` estiver disponivel, entra como viés leve no score.
- Se a migration global ainda nao estiver aplicada, o endpoint continua operando com historico local apenas.

### 5. Interface consultiva
- Novo card no formulario de parametros.
- Usuario escolhe ativo, timeframe e objetivo.
- O sistema retorna:
  - perfil recomendado
  - explicacao simples
  - alternativas comparaveis
  - botao `Aplicar sugestao ao formulario`
- Aplicacao nao salva automaticamente.

## Garantias
- Sem LLM opinativo.
- Sem alteracao automatica de configuracao.
- Usuario continua decidindo e salvando manualmente.

## Proximos passos
1. Adicionar filtro por `Global divergente` e estatistica de agreement na auditoria.
2. Exibir recomendacao historica por objetivo no dashboard.
3. Evoluir para recomendacao baseada em mais features reais (quando threshold/regime forem parametros persistidos do usuario).
