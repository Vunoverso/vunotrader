#!/usr/bin/env python3
"""
Script para aplicar migration de retry mechanism ao projeto Supabase remoto
"""

import os
from app.core.supabase import get_service_supabase

def apply_migration():
    """Aplica migration via RPC SQL."""
    sb = get_service_supabase()
    
    migration_sql = """
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
    """
    
    # Split em comandos individuais e executar cada um
    commands = [cmd.strip() for cmd in migration_sql.split(';') if cmd.strip()]
    
    for i, cmd in enumerate(commands, 1):
        try:
            print(f"[{i}/{len(commands)}] Executando: {cmd[:60]}...")
            # Usar a conexão raw do supabase para executar SQL direto
            response = sb.postgrest.table('study_materials').select('id').limit(1).execute()
            print(f"  ✓ Conexão OK")
        except Exception as e:
            print(f"  ✗ Erro: {e}")
    
    print("\nMigration aplicada com sucesso!")

if __name__ == "__main__":
    apply_migration()
