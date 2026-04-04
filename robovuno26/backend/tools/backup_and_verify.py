from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import ParseResult, urlparse, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import get_database_driver, get_database_url, get_sqlite_db_path


try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency in sqlite mode
    psycopg = None


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backup e restore-check do banco Vuno Trader")
    parser.add_argument("--output-dir", default="./runtime/backups")
    parser.add_argument("--retention-days", type=int, default=int(os.getenv("BACKUP_RETENTION_DAYS", "14")))
    parser.add_argument("--verify-restore", action="store_true", default=True)
    parser.add_argument("--no-verify-restore", dest="verify_restore", action="store_false")
    return parser.parse_args()


def cleanup_old_backups(output_dir: Path, retention_days: int) -> list[str]:
    if retention_days <= 0:
        return []
    removed: list[str] = []
    cutoff = datetime.now(timezone.utc).timestamp() - (retention_days * 86400)
    for file in output_dir.glob("*"):
        if not file.is_file():
            continue
        try:
            if file.stat().st_mtime < cutoff:
                file.unlink()
                removed.append(file.name)
        except OSError:
            continue
    return removed


def verify_sqlite_restore(backup_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="vuno-restore-check-") as temp_dir:
        restore_copy = Path(temp_dir) / "restore-check.db"
        shutil.copy2(backup_path, restore_copy)
        connection = sqlite3.connect(restore_copy)
        try:
            tables = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
            ).fetchone()[0]
            if int(tables or 0) <= 0:
                raise RuntimeError("Restore-check SQLite falhou: sem tabelas")
            migrations = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()[0]
            if int(migrations or 0) <= 0:
                raise RuntimeError("Restore-check SQLite falhou: schema_migrations ausente")
        finally:
            connection.close()


def backup_sqlite(output_dir: Path, verify_restore: bool) -> dict[str, object]:
    source = get_sqlite_db_path()
    if not source.exists():
        raise FileNotFoundError(f"Banco SQLite nao encontrado: {source}")

    target = output_dir / f"vuno-sqlite-{now_stamp()}.db"
    source_conn = sqlite3.connect(source)
    target_conn = sqlite3.connect(target)
    try:
        source_conn.backup(target_conn)
        target_conn.commit()
    finally:
        target_conn.close()
        source_conn.close()
    if verify_restore:
        verify_sqlite_restore(target)

    return {
        "driver": "sqlite",
        "source": str(source),
        "backup_file": str(target),
        "verify_restore": verify_restore,
    }


def _replace_db_name(url: str, db_name: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("DATABASE_URL invalida")
    safe_name = db_name.lstrip("/")
    new_path = f"/{safe_name}"
    replaced = ParseResult(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=new_path,
        params=parsed.params,
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunparse(replaced)


def _safe_restore_db_name() -> str:
    stamp = now_stamp().replace("-", "_")
    candidate = f"vuno_restore_check_{stamp}".lower()
    return candidate[:60]


def _run_subprocess(command: list[str]) -> None:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Falha ao executar comando: {' '.join(command)}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )


def verify_postgres_restore(database_url: str, backup_file: Path) -> str:
    if psycopg is None:
        raise RuntimeError("psycopg nao disponivel para restore-check Postgres")

    maintenance_db = os.getenv("PG_MAINTENANCE_DB", "postgres").strip() or "postgres"
    admin_url = _replace_db_name(database_url, maintenance_db)
    restore_db = _safe_restore_db_name()
    restore_url = _replace_db_name(database_url, restore_db)
    pg_restore_bin = os.getenv("PG_RESTORE_BIN", "pg_restore").strip() or "pg_restore"

    with psycopg.connect(admin_url, autocommit=True) as admin_conn:
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (restore_db,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{restore_db}"')
            cur.execute(f'CREATE DATABASE "{restore_db}"')

    _run_subprocess(
        [
            pg_restore_bin,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            restore_url,
            str(backup_file),
        ]
    )

    with psycopg.connect(restore_url, autocommit=True) as restore_conn:
        with restore_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            )
            table_count = int(cur.fetchone()[0] or 0)
            if table_count <= 0:
                raise RuntimeError("Restore-check Postgres falhou: sem tabelas em public")
            cur.execute("SELECT COUNT(*) FROM schema_migrations")
            migration_count = int(cur.fetchone()[0] or 0)
            if migration_count <= 0:
                raise RuntimeError("Restore-check Postgres falhou: schema_migrations vazia")

    with psycopg.connect(admin_url, autocommit=True) as admin_conn:
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (restore_db,),
            )
            cur.execute(f'DROP DATABASE IF EXISTS "{restore_db}"')

    return restore_db


def backup_postgres(output_dir: Path, verify_restore: bool) -> dict[str, object]:
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL obrigatoria para backup Postgres")

    pg_dump_bin = os.getenv("PG_DUMP_BIN", "pg_dump").strip() or "pg_dump"
    backup_file = output_dir / f"vuno-postgres-{now_stamp()}.dump"
    _run_subprocess(
        [
            pg_dump_bin,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(backup_file),
            database_url,
        ]
    )

    restore_check_db = None
    if verify_restore:
        restore_check_db = verify_postgres_restore(database_url, backup_file)

    return {
        "driver": "postgres",
        "backup_file": str(backup_file),
        "verify_restore": verify_restore,
        "restore_check_db": restore_check_db,
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    driver = get_database_driver()
    if driver == "postgres":
        result = backup_postgres(output_dir, args.verify_restore)
    else:
        result = backup_sqlite(output_dir, args.verify_restore)

    removed_files = cleanup_old_backups(output_dir, max(0, args.retention_days))
    result["output_dir"] = str(output_dir)
    result["retention_days"] = max(0, args.retention_days)
    result["removed_files"] = removed_files
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
