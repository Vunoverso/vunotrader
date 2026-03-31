# 2026-03-30 — Sprint 3 completo

## Objetivo

Finalizar o bloco de features acordado no sprint:
- Widget de instâncias de robô no admin
- Simulação completa do ciclo MT5
- Pipeline de retreino autônomo
- Endpoint de score de decisão

---

## Arquivos impactados

| Arquivo | Alteração |
|---|---|
| `web/src/app/app/admin/page.tsx` | Widget "Instâncias de Robô" com tabela mostrando nome/org/modo/atividade/heartbeat, rodapé com legenda e badge de liveness |
| `backend/scripts/simulate_mt5_cycle.py` | Reescrita completa — 5 ciclos de teste com assertivas coloridas: MARKET_DATA, TRADE RESULT WIN, N×LOSS consecutivo, heartbeat, drawdown pause |
| `retrain_pipeline.py` | Novo arquivo — pipeline autônomo de retreino RF+GB a partir de `anonymized_trade_events`, com argparse, dry-run, métricas para Supabase |
| `web/src/app/api/decision-score/route.ts` | Novo endpoint GET autenticado — retorna score histórico de configuração de trade (win_rate, sample_size, confidence_tier, regime_win_rate) |

---

## Decisões técnicas

### Widget de robôs no admin
- `robotActivityStatus()` já existia como função no server component
- Status baseado em `last_seen_at`: ativo < 5 min, dormindo < 60 min, offline > 60 min
- Rodapé mostra contador de robôs real ativos com ping animado (apenas se `real_trading_enabled=true`)
- `nowMs` calculado no server (sem `new Date()` diretamente no JSX para evitar hidratação)

### simulate_mt5_cycle.py
- 5 ciclos independentes, cada um com seção visual e assertivas ok/fail
- Ciclo de drawdown sinaliza como `⚠️` quando não ativado (pode ser normal se parâmetro = 0)
- `_robot_id_resolved` é atualizado automaticamente a partir da resposta do brain no ciclo 1
- ANSI colors com fallback seguro em terminais sem suporte

### retrain_pipeline.py
- Lê `anonymized_trade_events` (sem PII — colunas sensitive são hashes)
- Features disponíveis: confidence, risk_pct, pnl_points, volatility + one-hot de side/regime/timeframe/mode
- Score ponderado com fator Wilson-like simplificado: `score = win_rate * min(1, sqrt(n)/10)`
- Persiste métricas em `model_metrics` se tabela existir (ignora silenciosamente)
- Salva modelos em `brain_model_rf.pkl` / `brain_model_gb.pkl` (mesmos caminhos usados pelo brain)
- Pode ser importado por `RetrainScheduler` chamando `run_pipeline()`

### /api/decision-score
- Autenticação via `getUser()` (não `getSession()` — conforme boas práticas Supabase)
- Defesa em profundidade: `.eq("user_id", user.id)` explícito além do RLS
- Filtra por symbol/timeframe/side/regime passados como query params
- Retorna `null` para `regime_win_rate` se regime não foi fornecido
- Sem dependência de tabela `model_metrics` — query direta em `trade_decisions + trade_outcomes`

---

## Validações

- `py_compile vunotrader_brain.py` → exit=0 ✅
- `py_compile retrain_pipeline.py` → sintaxe OK ✅
- `py_compile simulate_mt5_cycle.py` → sintaxe OK ✅
- TypeScript `admin/page.tsx` → sem erros ✅
- TypeScript `api/decision-score/route.ts` → sem erros ✅

---

## Pendências / próximos passos

- [ ] Aplicar migration `model_metrics` no Supabase se quiser persistir acurácia de retreino
- [ ] Rodar `simulate_mt5_cycle.py` contra brain vivo para validação E2E
- [ ] Adicionar `feature_snapshot jsonb` em `anonymized_trade_events` para futuramente treinar com features técnicas reais
- [ ] Implementar `retrain_pipeline.py` no `RetrainScheduler` do brain (substituindo `generate_sample_data`)
- [ ] Dashboard de score por símbolo/regime na página `/app/dashboard`
