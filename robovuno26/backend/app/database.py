from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


try:
    import psycopg
    from psycopg import IntegrityError as PsycopgIntegrityError
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - optional dependency in sqlite mode
    psycopg = None
    PsycopgIntegrityError = None
    dict_row = None


BASE_DIR = Path(__file__).resolve().parents[1]
RUNTIME_DIR = BASE_DIR / "runtime"
DB_PATH = RUNTIME_DIR / "vuno_saas.db"


def _normalize_driver(raw_driver: str | None, database_url: str | None) -> str:
    value = (raw_driver or "").strip().lower()
    if value in {"postgres", "postgresql", "supabase"}:
        return "postgres"
    if value == "sqlite":
        return "sqlite"
    if database_url and database_url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    return "sqlite"


def get_database_driver() -> str:
    return _normalize_driver(os.getenv("DB_DRIVER"), os.getenv("DATABASE_URL"))


def is_postgres() -> bool:
    return get_database_driver() == "postgres"


def get_database_url() -> str | None:
    url = (os.getenv("DATABASE_URL", "") or os.getenv("POSTGRES_DSN", "")).strip()
    return url or None


def get_sqlite_db_path() -> Path:
    explicit_path = os.getenv("SQLITE_DB_PATH", "").strip()
    if explicit_path:
        return Path(explicit_path).expanduser()

    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if database_url.startswith("sqlite:///"):
        parsed = urlparse(database_url)
        if parsed.netloc:
            raw_path = f"//{parsed.netloc}{parsed.path}"
        else:
            raw_path = parsed.path
        if raw_path:
            return Path(raw_path).expanduser()

    return DB_PATH


def is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    if PsycopgIntegrityError is not None and isinstance(exc, PsycopgIntegrityError):
        return True
    return False


def _convert_qmark_to_pyformat(sql: str) -> str:
    result: list[str] = []
    in_single_quote = False
    in_double_quote = False
    idx = 0
    length = len(sql)

    while idx < length:
        char = sql[idx]
        next_char = sql[idx + 1] if idx + 1 < length else ""

        if char == "'" and not in_double_quote:
            if in_single_quote and next_char == "'":
                result.append("''")
                idx += 2
                continue
            in_single_quote = not in_single_quote
            result.append(char)
            idx += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            result.append(char)
            idx += 1
            continue

        if char == "?" and not in_single_quote and not in_double_quote:
            result.append("%s")
            idx += 1
            continue

        result.append(char)
        idx += 1

    return "".join(result)


def _extract_lastval(row: Any) -> int | None:
    if row is None:
        return None
    if isinstance(row, Mapping):
        value = row.get("lastval")
        return int(value) if value is not None else None
    if isinstance(row, Iterable):
        values = list(row)
        if values:
            return int(values[0]) if values[0] is not None else None
    return None


class DBCursor:
    def __init__(self, raw_cursor: Any, driver: str):
        self._raw = raw_cursor
        self._driver = driver
        self._lastrowid: int | None = None

    @property
    def lastrowid(self) -> int | None:
        value = getattr(self._raw, "lastrowid", None)
        if value is not None:
            return int(value)
        return self._lastrowid

    def fetchone(self) -> Any:
        return self._raw.fetchone()

    def fetchall(self) -> list[Any]:
        return list(self._raw.fetchall())

    def __iter__(self):
        return iter(self._raw)


class DBConnection:
    def __init__(self, raw_connection: Any, driver: str):
        self._raw = raw_connection
        self.driver = driver

    def __enter__(self) -> "DBConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

    def _adapt_sql(self, sql: str) -> str:
        if self.driver == "postgres":
            return _convert_qmark_to_pyformat(sql)
        return sql

    def execute(self, sql: str, params: tuple | list | None = None) -> DBCursor:
        adapted_sql = self._adapt_sql(sql)
        bindings = tuple(params or ())
        raw_cursor = self._raw.execute(adapted_sql, bindings)
        cursor = DBCursor(raw_cursor, self.driver)

        if self.driver == "postgres":
            normalized = sql.lstrip().upper()
            if normalized.startswith("INSERT") and "RETURNING" not in normalized:
                try:
                    lastval_row = self._raw.execute("SELECT LASTVAL() AS lastval").fetchone()
                    cursor._lastrowid = _extract_lastval(lastval_row)
                except Exception:
                    cursor._lastrowid = None

        return cursor

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        self._raw.close()


def _connect_sqlite() -> DBConnection:
    db_path = get_sqlite_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return DBConnection(connection, "sqlite")


def _connect_postgres() -> DBConnection:
    if psycopg is None or dict_row is None:
        raise RuntimeError(
            "Driver Postgres indisponivel. Instale dependencias com: pip install 'psycopg[binary]'"
        )

    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL/POSTGRES_DSN obrigatorio para DB_DRIVER=postgres")

    connection = psycopg.connect(database_url, row_factory=dict_row)
    connection.autocommit = False
    return DBConnection(connection, "postgres")


def get_connection() -> DBConnection:
    driver = get_database_driver()
    if driver == "postgres":
        return _connect_postgres()
    return _connect_sqlite()


def init_db() -> None:
    from .migrations import run_migrations

    run_migrations()
