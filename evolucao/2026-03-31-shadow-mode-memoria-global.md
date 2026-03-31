# 2026-03-31 - Shadow mode: comparacao local vs memoria global

## Objetivo
Implementar comparacao em tempo real entre decisao local do brain e recomendacao da memoria global, sem alterar a execucao do trade.

## Arquivo impactado
- `vunotrader_brain.py`

## Implementacao
- Novas configuracoes de ambiente:
  - `ENABLE_GLOBAL_MEMORY_SHADOW` (default ligado)
  - `GLOBAL_MEMORY_MIN_SAMPLES` (default 20)
- Nova funcao `SupabaseLogger.get_global_memory_best(...)`:
  - consulta `global_memory_signals` por contexto (`symbol`, `timeframe`, `regime`, `mode`)
  - considera apenas `buy/sell`
  - exige amostra minima
  - seleciona melhor candidato por score de win rate ponderado por amostra
- Em `_handle_market_data`:
  - adicionada coleta `shadow_global`
  - compara `local_signal` vs `global_recommendation.side`
  - retorna `agreement` e `execution_changed=false`

## Garantia de seguranca
- Nenhuma alteracao foi feita no sinal final executado.
- O modo shadow e somente observabilidade/comparacao.

## Proximos passos
1. Exibir `shadow_global.agreement` no dashboard de auditoria.
2. Rodar 7-14 dias em shadow para medir divergencia e impacto potencial.
3. Se valido, evoluir para ajuste de risco em modo assistido (nao autonomo).
