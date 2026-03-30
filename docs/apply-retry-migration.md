# 2026-03-30 — Roteiro: Aplicar Migration de Retry Mechanism

## Objetivo
Aplicar a migration `20260330_000004_study_ingestion_retry_mechanism.sql` ao projeto Supabase remoto para ativar retry logic com backoff exponencial.

## Pre-requisitos
- Acesso ao dashboard Supabase do projeto `mztrtovhjododrkzkehk`
- SQL Editor disponível
- Service Role JWT (ou credenciais de admin)

## Como Aplicar

### Opção 1: Via SQL Editor (Recomendado)

1. Abra https://supabase.com/dashboard/project/mztrtovhjododrkzkehk/sql
2. Clique em "New Query"
3. Cole o contenúdo da migration abaixo:

```sql
-- Mecanismo de retry com backoff exponencial para ingestao de estudos

alter table if exists public.study_materials
  add column if not exists retry_count int default 0;

alter table if exists public.study_materials
  add column if not exists next_retry_at timestamptz;

alter table if exists public.study_materials
  add column if not exists last_error_at timestamptz;

-- Criar indice para melhorar query de pendentes considerando retry
create index if not exists idx_study_materials_retry_status
  on public.study_materials (processing_status, next_retry_at, created_at desc)
  where processing_status in ('pending', 'error');

-- Reset de campos de retry para materiais processados com sucesso
update public.study_materials
set
  retry_count = 0,
  next_retry_at = null,
  last_error_at = null
where processing_status = 'processed';
```

4. Clique em "Run" (botão verde)
5. Aguarde confirmacao (deve aparecer "Success")

### Opção 2: Via cURL (Shell Script)

```bash
#!/bin/bash
# apply_retry_migration.sh

PROJECT_ID="mztrtovhjododrkzkehk"
SUPABASE_URL="https://${PROJECT_ID}.supabase.co"
SERVICE_ROLE_KEY="<seu-service-role-key-aqui>"

SQL_QUERY=$(cat <<'EOF'
alter table if exists public.study_materials
  add column if not exists retry_count int default 0;

alter table if exists public.study_materials
  add column if not exists next_retry_at timestamptz;

alter table if exists public.study_materials
  add column if not exists last_error_at timestamptz;

create index if not exists idx_study_materials_retry_status
  on public.study_materials (processing_status, next_retry_at, created_at desc)
  where processing_status in ('pending', 'error');

update public.study_materials
set
  retry_count = 0,
  next_retry_at = null,
  last_error_at = null
where processing_status = 'processed';
EOF
)

curl -X POST "${SUPABASE_URL}/rest/v1/rpc/execute_sql" \
  -H "apikey: ${SERVICE_ROLE_KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"${SQL_QUERY}\"}"
```

### Opção 3: Via Python (Local)

A migration será aplicada automaticamente quando o worker tentar atualizar:
- Se a migration nao foi aplicada, o worker logará warning
- Operara em backwards compat mode (sem retry logic)
- Retry logic será ativado assim que migration for aplicada

```python
# Nao é necessario rodar manualmente; worker detecta automaticamente
from app.core.supabase import get_service_supabase

# O worker rodá:
# python -m app.workers.study_ingestion_worker --once
```

## Validação Pos-Aplicacao

### 1. Via Dashboard Supabase
- Abra "Database > Tables > study_materials"
- Verifique se colunasexistem:
  - `retry_count` (type: int, default: 0)
  - `next_retry_at` (type: timestamptz)
  - `last_error_at` (type: timestamptz)
- Verifique se indice `idx_study_materials_retry_status` existe em "Indexes"

### 2. Via SQL Query
```sql
-- Verificar colunas
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'study_materials'
AND column_name IN ('retry_count', 'next_retry_at', 'last_error_at')
ORDER BY ordinal_position;

-- Verificar indice
SELECT indexname FROM pg_indexes
WHERE tablename = 'study_materials'
AND indexname = 'idx_study_materials_retry_status';
```

### 3. Via Worker (Full Test)
```bash
cd e:\robotrademeta5\backend
$env:OPENAI_API_KEY='<sua-chave-aqui>'
python -m app.workers.study_ingestion_worker --once
# Observar logs de _load_pending() sem warning de "Retry columns not yet migrated"
```

## Expected Output Apos Migracao

```log
2026-03-30 10:30:00,123 [INFO] Worker IA iniciado...
2026-03-30 10:30:05,456 [INFO] Material abc123... agendado para retry (tentativa 1, proximo em 1s)
2026-03-30 10:30:35,789 [INFO] Material xyz789... agendado para retry (tentativa 2, proximo em 2s)
2026-03-30 10:31:00,000 [WARNING] Material pqr123 marcado como erro permanente (retry_count=5)
```

## Duvidas/Troubleshooting

**Q: Qual é o impacto da migration?**
- A: Adiciona 3 colunas + 1 indice. Nao modifica dados existentes (apenas reseta campos de retry para materiais ja processados).

**Q: Posso voltar atrás?**
- A: Sim, `if not exists` permite rodar multiplas vezes com seguranca. Colunas nao serao duplicadas.

**Q: O worker vai quebrar se rodar sem migration aplicada?**
- A: Nao. Vai logar warning e operar em backwards compat (sem retry agendado, apenas "error").

**Q: Quanto tempo leva para aplicar?**
- A: <1 segundo. A maior parte é criar o indice.

## Next Steps
1. ✅ Apply migration via SQL Editor
2. ✅ Validate columns exist
3. ✅ Run worker and monitor logs
4. ✅ Test with material that fails (optional)
5. ✅ Deploy to production
