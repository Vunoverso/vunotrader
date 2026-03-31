# Migrations aplicadas ao Supabase remoto

**Data:** 2026-03-30  
**Status:** ✅ Aplicadas e validadas

## Objetivo

Ativar as estruturas de banco de dados que suportam os diferenciais implementados na
sprint anterior (robot_instances, controles de risco, índices de auditoria).

## Migrations executadas (ordem)

### 000005 — `20260330_000005_robot_instances_isolation.sql`

Criou/configurou:
- **Tabela `robot_instances`**: isolamento por instância de robô com campos `organization_id`, `profile_id`, `name`, `robot_token_hash`, `status`, `allowed_modes`, `real_trading_enabled`, `max_risk_real`, `last_seen_at`
- **Índices**: `idx_robot_instances_token_hash` (unique), `idx_robot_instances_org_profile`
- **Colunas `robot_instance_id`** adicionadas em: `trade_decisions`, `executed_trades`, `trade_outcomes`, `ai_usage_logs`
- **Índices** nas 4 tabelas para consultas por instância
- **RLS** habilitado com policy `robot_instances_org_policy`

### 000006 — `20260330_000006_risk_controls_consistency.sql`

Criou/configurou:
- **3 novas colunas em `user_parameters`**:
  - `max_consecutive_losses int default 3`
  - `drawdown_pause_pct numeric(7,3) default 5.0`
  - `auto_reduce_risk boolean default true`
- **Índice `idx_user_parameters_user_id`** para cache eficiente no brain
- **Comment** em `market_snapshots.regime` documentando valores esperados
- **Índice GIN `idx_trade_decisions_rationale_pattern`** para busca textual em rationale

## Validação pós-aplicação

Query de validação executada com resultado `1 | 3 | 1 | 1`:
- `robot_instances_exists = 1` ✅
- `new_cols_count = 3` ✅ (3 colunas em user_parameters)  
- `token_hash_idx = 1` ✅
- `rationale_idx = 1` ✅

## Impacto imediato

- Dashboard topbar → `robot_instances.last_seen_at` agora existe para consulta real
- Brain → `get_risk_params()` pode ler `max_consecutive_losses` da tabela real
- Parametros form → campos `max_consecutive_losses`, `drawdown_pause_pct`, `auto_reduce_risk` têm colunas no banco
- Auditoria → índice GIN acelera busca em rationale

## Pendências restantes

- [ ] Brain: implementar verificação `drawdown_pause_pct` (PnL diário via `trade_outcomes`)
- [ ] Admin: widget de instâncias de robô por org
- [ ] Sprint 3: pipeline de retrain, `lessons_learned`, endpoint `/api/decision-score`
- [ ] Testar ciclo MT5 completo com `simulate_mt5_cycle.py`
