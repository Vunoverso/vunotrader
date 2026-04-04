# Evolucao - Bloco 3 (Banco e Continuidade)

Data: 2026-04-03

## Objetivo

- sair de dependencia exclusiva em SQLite local
- habilitar uso de banco gerenciado (Postgres/Supabase)
- criar migracoes versionadas
- adicionar backup automatico com restore-check

## Entregas

1. Camada de banco multi-driver
- `backend/app/database.py` refeito para suportar:
  - `DB_DRIVER=sqlite`
  - `DB_DRIVER=postgres` (com `DATABASE_URL`)
- adaptacao transparente de placeholders SQL (`?` -> `%s`) para Postgres
- suporte a `lastrowid` em inserts sem `RETURNING` via `LASTVAL()`
- deteccao generica de erro de integridade (SQLite/Postgres)

2. Migracoes versionadas
- novo runner: `backend/app/migrations.py`
- tabela de controle: `schema_migrations`
- validacao de checksum por migracao aplicada
- migracoes iniciais:
  - `backend/migrations/sqlite/0001_initial_schema.sql`
  - `backend/migrations/postgres/0001_initial_schema.sql`
- script operacional:
  - `backend/migrate.ps1` (`status` e `up`)

3. Startup com migracoes
- `init_db()` agora executa `run_migrations()`
- backend aplica migracoes pendentes automaticamente no startup

4. Backup + restore-check
- novo utilitario: `backend/tools/backup_and_verify.py`
  - SQLite: copia `.db` + valida restauracao em banco temporario
  - Postgres: `pg_dump` + `pg_restore` em DB temporario + validacao de tabelas/migracoes
  - limpeza de backups antigos por retencao
- novo wrapper PowerShell:
  - `backend/backup-db.ps1` (com `-VerifyRestore`)
- agendamento automatico:
  - `backend/register-backup-task.ps1`

5. Config/documentacao
- `backend/.env.example` com variaveis de banco e backup
- `backend/requirements.txt` inclui `psycopg[binary]`
- README atualizado com fluxo de:
  - Postgres/Supabase
  - migracoes
  - backup/restore-check

## Observacoes operacionais

- para Postgres/Supabase, e necessario ter `pg_dump` e `pg_restore` no PATH para backup/restore-check
- em SQLite local, o fluxo continua funcionando como antes

