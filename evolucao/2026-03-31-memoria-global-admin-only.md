# 2026-03-31 - Memoria global agregada (admin-only)

## Objetivo
Incrementar a inteligencia global com cruzamento de configuracoes sem abrir acesso para usuarios comuns.

## Decisao
Implementar memoria global anonima agregada, com rebuild manual exclusivo para platform admin.

## Arquivos impactados
- `supabase/migrations/20260331_000010_global_memory_admin.sql`
- `backend/scripts/rebuild_global_memory.py`
- `web/src/app/api/admin/global-memory/rebuild/route.ts`
- `web/src/components/app/admin-global-memory-button.tsx`
- `web/src/app/app/admin/modelo/page.tsx`

## Implementacao
1. **Tabela global** `global_memory_signals`:
- agrega por `symbol/timeframe/regime/side/mode/config_fingerprint`
- armazena `sample_size`, `wins`, `losses`, `win_rate`, medias e metadados

2. **Controle de acesso**:
- criada funcao `public.is_platform_admin()`
- RLS da tabela permite `SELECT` apenas para admin autenticado
- escrita reservada ao service role (scripts internos)

3. **Script de rebuild**:
- `rebuild_global_memory.py` lê `anonymized_trade_events`
- gera fingerprint por buckets de confianca/risco/volatilidade + contexto
- faz agregacao e repopula `global_memory_signals`
- suporta `--dry-run`, `--days` e `--min-samples`

4. **API admin-only**:
- endpoint `POST /api/admin/global-memory/rebuild`
- valida sessao + `is_platform_admin`
- executa script Python no servidor e retorna output

5. **UI admin**:
- novo botao `Rebuild Memória Global` na tela de modelo
- cards com visao do estado da memoria global
- aviso de amostra minima para rebuild mais confiavel

## Riscos e observacoes
- Rebuild atual usa estrategia de limpar e repopular para simplicidade operacional.
- O uso da memoria global no sinal em tempo real do brain ainda fica para proximo passo (shadow mode recomendado).

## Proximos passos
1. Usar `global_memory_signals` no brain em modo observacao (sem alterar sinal).
2. Promover para ajuste de risco/sinal apenas com amostra minima e guardrails.
3. Exibir comparativo local vs global no dashboard de auditoria.
