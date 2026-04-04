# 2026-04-04 - Contrato de dados do Robo Hibrido Visual

## Objetivo

Definir o contrato final de dados para:

- `cycle_id`
- `visual_context`
- `visual_alignment`
- feature flags SaaS

Esse contrato deve ser a base unica para MT5, agent-local, backend, storage, auditoria e dashboard.

## 1. `cycle_id`

### Responsavel por gerar

- o bridge MT5

### Momento de geracao

- no mesmo ponto em que o bridge cria o snapshot do ciclo

### Formato

- string ASCII segura para arquivo e storage
- padrao recomendado: `bridge_symbol_timeframe_unix_tickcount`

Exemplo:

- `vuno_bridge_EURUSD_M5_1775310000_28451`

### Regras

1. Um unico `cycle_id` por ciclo local.
2. O mesmo `cycle_id` deve existir em JSON, PNG, payload do agente e persistencia do backend.
3. O `cycle_id` nao pode ser recalculado no agent-local nem no backend.

### Campos minimos no snapshot

```json
{
  "cycle_id": "vuno_bridge_EURUSD_M5_1775310000_28451",
  "symbol": "EURUSD",
  "timeframe": "M5",
  "chart_symbol": "EURUSD",
  "chart_timeframe": "M5",
  "captured_at": "2026-04-04T20:33:18Z",
  "chart_image_file": "vuno_bridge_EURUSD_M5_1775310000_28451.chart.png",
  "chart_image_captured_at": "2026-04-04T20:33:18Z",
  "chart_image_hash": "sha256:..."
}
```

## 2. `visual_context`

### Responsavel por gerar

- worker visual shadow

### Tipo

- `jsonb`

### Estrutura recomendada

```json
{
  "schema_version": "1.0",
  "status": "processed",
  "engine": "visual_shadow_v1",
  "summary": "Leitura visual confirma contexto de tendencia e pullback.",
  "setup_guess": "trend_pullback",
  "signal_bias": "buy",
  "quality": {
    "score": 0.84,
    "image_clarity": 0.91,
    "chart_visibility": 0.88,
    "overlay_density": 0.34
  },
  "market_read": {
    "trend": "bullish",
    "volatility": "normal",
    "structure": "continuation"
  },
  "evidence": [
    {
      "label": "ema_fast_above_ema_slow",
      "confidence": 0.87,
      "source": "screen"
    },
    {
      "label": "recent_pullback_near_mean",
      "confidence": 0.71,
      "source": "screen"
    }
  ],
  "warnings": [],
  "rationale": "A imagem mostra continuidade de tendencia com recuo controlado e sem ruido visual relevante.",
  "model_version": "visual-shadow-2026-04-v1"
}
```

### Regras

1. `visual_context` descreve a leitura visual; nao descreve a ordem final.
2. Campos de qualidade devem ficar normalizados entre `0` e `1`.
3. `rationale` deve ser texto curto e legivel no dashboard.
4. `warnings` deve listar problemas como imagem ruim, chart poluido ou captura parcial.

## 3. `visual_alignment`

### Papel

- representar a relacao entre a leitura estruturada e a leitura visual

### Enum final

- `aligned`
- `divergent_low`
- `divergent_high`
- `not_applicable`
- `error`

### Semantica

- `aligned`: leitura visual confirma a estruturada
- `divergent_low`: divergencia fraca ou duvida sem alta confianca
- `divergent_high`: divergencia forte, entra em fila de revisao
- `not_applicable`: shadow nao rodou ou nao havia imagem valida para comparar
- `error`: pipeline visual falhou

### Estrutura recomendada

```json
{
  "status": "divergent_high",
  "structured_signal": "BUY",
  "visual_signal": "HOLD",
  "structured_confidence": 0.79,
  "visual_confidence": 0.86,
  "reason": "Leitura visual encontrou lateralizacao e baixa limpeza estrutural no chart.",
  "review_required": true
}
```

### Regra operacional

- no MVP, `visual_alignment` nunca bloqueia nem reescreve a ordem oficial

## 4. Feature flags SaaS

## Tabelas recomendadas

### `saas_features`

```sql
create table saas_features (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  description text,
  scope text not null check (scope in ('product', 'ops', 'visual', 'admin')),
  default_enabled boolean not null default false,
  config_schema jsonb,
  created_at timestamptz not null default now()
);
```

### `saas_plan_features`

```sql
create table saas_plan_features (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references saas_plans(id) on delete cascade,
  feature_id uuid not null references saas_features(id) on delete cascade,
  is_enabled boolean not null default true,
  config jsonb,
  created_at timestamptz not null default now(),
  unique (plan_id, feature_id)
);
```

### Indices recomendados

```sql
create index idx_saas_plan_features_plan_id on saas_plan_features(plan_id);
create index idx_saas_plan_features_feature_id on saas_plan_features(feature_id);
```

## Features iniciais

- `robot.integrated`
- `robot.visual_hybrid`
- `robot.visual_shadow`
- `robot.visual_storage_extended`
- `robot.visual_compare`
- `ops.desktop_recovery`

## Distribuicao inicial por plano

### Starter

- `robot.integrated`

### Pro

- `robot.integrated`
- `robot.visual_hybrid`
- `robot.visual_shadow`

### Scale

- todas do Pro
- `robot.visual_storage_extended`
- `robot.visual_compare`
- `ops.desktop_recovery`

## 5. Modelo de instancia do robo

### Evolucao recomendada em `robot_instances`

Adicionar campos:

```sql
alter table robot_instances
  add column robot_product_type text not null default 'robo_integrado'
    check (robot_product_type in ('robo_integrado', 'robo_hibrido_visual', 'python_laboratorio')),
  add column visual_shadow_enabled boolean not null default false,
  add column computer_use_enabled boolean not null default false,
  add column human_approval_required boolean not null default false;
```

### Regra

- o backend deve ser a fonte autoritativa do tipo da instancia

## 6. Persistencia recomendada do ciclo visual

### Tabela sugerida: `trade_visual_contexts`

```sql
create table trade_visual_contexts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id) on delete cascade,
  robot_instance_id uuid not null references robot_instances(id) on delete cascade,
  trade_decision_id uuid references trade_decisions(id) on delete set null,
  cycle_id text not null,
  chart_image_storage_path text,
  chart_image_hash text,
  visual_shadow_status text not null check (visual_shadow_status in ('pending', 'processed', 'error', 'skipped', 'skipped_non_chart_symbol')),
  visual_context jsonb,
  visual_alignment text not null check (visual_alignment in ('aligned', 'divergent_low', 'divergent_high', 'not_applicable', 'error')),
  visual_conflict_reason text,
  visual_model_version text,
  processed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (robot_instance_id, cycle_id)
);
```

### Semantica recomendada de `visual_shadow_status`

- `pending`: ciclo aguardando worker visual
- `processed`: screenshot analisado ou registrado em modo capture-only
- `error`: falha operacional no pipeline visual
- `skipped`: shadow desligado ou screenshot ausente por motivo generico
- `skipped_non_chart_symbol`: ciclo multiativo fora do chart anexado; nao deve receber o screenshot do grafico corrente

### Indices recomendados

```sql
create index idx_trade_visual_contexts_org_cycle on trade_visual_contexts(organization_id, created_at desc);
create index idx_trade_visual_contexts_robot_cycle on trade_visual_contexts(robot_instance_id, created_at desc);
create index idx_trade_visual_contexts_decision on trade_visual_contexts(trade_decision_id);
```

## 7. Regras finais de contrato

1. `cycle_id` nasce no MT5 e nunca muda.
2. `visual_context` e sempre shadow no MVP.
3. `visual_alignment` nunca altera ordem automaticamente no MVP.
4. Feature flag vem do backend; frontend apenas reflete.
5. `robot_product_type` deve existir antes do rollout comercial do `Robo Hibrido Visual`.
