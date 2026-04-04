from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .database import get_connection, get_database_driver


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
VERSION_PATTERN = re.compile(r"^(?P<version>\d+)_(?P<name>[a-zA-Z0-9_]+)\.sql$")


@dataclass(frozen=True, slots=True)
class MigrationFile:
    version: str
    name: str
    filename: str
    path: Path
    checksum: str
    content: str


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_sql_statements(script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_single_quote = False
    in_double_quote = False
    idx = 0
    length = len(script)

    while idx < length:
        char = script[idx]
        next_char = script[idx + 1] if idx + 1 < length else ""

        if char == "'" and not in_double_quote:
            if in_single_quote and next_char == "'":
                buffer.append("''")
                idx += 2
                continue
            in_single_quote = not in_single_quote
            buffer.append(char)
            idx += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            buffer.append(char)
            idx += 1
            continue

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            idx += 1
            continue

        buffer.append(char)
        idx += 1

    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def ensure_schema_migrations_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )


def list_migration_files(driver: str) -> list[MigrationFile]:
    folder = MIGRATIONS_DIR / driver
    if not folder.exists():
        return []

    files: list[MigrationFile] = []
    for path in sorted(folder.glob("*.sql")):
        match = VERSION_PATTERN.match(path.name)
        if not match:
            continue
        content = path.read_text(encoding="utf-8")
        files.append(
            MigrationFile(
                version=match.group("version"),
                name=match.group("name"),
                filename=path.name,
                path=path,
                checksum=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                content=content,
            )
        )
    return files


def load_applied_migrations(connection) -> dict[str, dict[str, str]]:
    rows = connection.execute(
        "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    applied: dict[str, dict[str, str]] = {}
    for row in rows:
        applied[str(row["version"])] = {
            "name": str(row["name"]),
            "checksum": str(row["checksum"]),
            "applied_at": str(row["applied_at"]),
        }
    return applied


def get_table_columns(connection, driver: str, table_name: str) -> set[str]:
    if driver == "postgres":
        rows = connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchall()
        return {str(row["column_name"]) for row in rows}

    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def migration_already_reflected_in_schema(connection, driver: str, migration: MigrationFile) -> bool:
    if migration.name == "runtime_policy_and_vpe_controls":
        required_columns = {
            "operational_timeframe",
            "confirmation_timeframe",
            "news_pause_enabled",
            "news_pause_symbols",
            "news_pause_countries",
            "news_pause_before_minutes",
            "news_pause_after_minutes",
            "news_pause_impact",
            "performance_gate_enabled",
            "performance_gate_min_profit_factor",
            "performance_gate_min_trades",
            "validated_backtest_profit_factor",
            "validated_backtest_trades",
        }
        return required_columns.issubset(get_table_columns(connection, driver, "user_parameters"))

    if migration.name == "robot_instances_bridge_and_symbols":
        required_columns = {"broker_profile", "selected_symbols_json", "bridge_name"}
        return required_columns.issubset(get_table_columns(connection, driver, "robot_instances"))

    if migration.name == "robot_instances_mt5_metadata_and_setup":
        required_columns = {
            "primary_symbol",
            "chart_timeframe",
            "discovered_symbols_json",
            "symbols_detected_at",
        }
        return required_columns.issubset(get_table_columns(connection, driver, "robot_instances"))

    if migration.name == "decision_engine_mode":
        user_columns = get_table_columns(connection, driver, "user_parameters")
        robot_columns = get_table_columns(connection, driver, "robot_instance_parameters")
        return "decision_engine_mode" in user_columns and "decision_engine_mode" in robot_columns

    if migration.name == "runtime_intelligence_controls":
        required_columns = {
            "market_session_guard_enabled",
            "daily_loss_limit",
            "max_equity_drawdown_pct",
            "break_even_trigger_points",
            "trailing_trigger_points",
            "position_time_stop_minutes",
            "position_stagnation_window_candles",
        }
        user_columns = get_table_columns(connection, driver, "user_parameters")
        robot_columns = get_table_columns(connection, driver, "robot_instance_parameters")
        return required_columns.issubset(user_columns) and required_columns.issubset(robot_columns)

    return False


def record_existing_migration(connection, migration: MigrationFile) -> None:
    connection.execute(
        """
        INSERT INTO schema_migrations (version, name, checksum, applied_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            migration.version,
            migration.name,
            migration.checksum,
            now_utc_iso(),
        ),
    )


def apply_migration(connection, migration: MigrationFile) -> None:
    for statement in split_sql_statements(migration.content):
        connection.execute(statement)
    connection.execute(
        """
        INSERT INTO schema_migrations (version, name, checksum, applied_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            migration.version,
            migration.name,
            migration.checksum,
            now_utc_iso(),
        ),
    )


def run_migrations() -> list[str]:
    driver = get_database_driver()
    migration_files = list_migration_files(driver)
    if not migration_files:
        return []

    applied_now: list[str] = []
    with get_connection() as connection:
        ensure_schema_migrations_table(connection)
        applied = load_applied_migrations(connection)

        for migration in migration_files:
            existing = applied.get(migration.version)
            if existing:
                if existing["checksum"] != migration.checksum:
                    raise RuntimeError(
                        f"Checksum divergente para migracao {migration.version} ({migration.filename})"
                    )
                continue

            if migration_already_reflected_in_schema(connection, driver, migration):
                record_existing_migration(connection, migration)
                applied_now.append(f"{migration.filename} (schema-reconciled)")
                applied[migration.version] = {
                    "name": migration.name,
                    "checksum": migration.checksum,
                    "applied_at": now_utc_iso(),
                }
                continue

            apply_migration(connection, migration)
            applied_now.append(migration.filename)

    return applied_now


def migration_status() -> list[dict[str, str]]:
    driver = get_database_driver()
    files = list_migration_files(driver)
    if not files:
        return []

    with get_connection() as connection:
        ensure_schema_migrations_table(connection)
        applied = load_applied_migrations(connection)

    payload: list[dict[str, str]] = []
    for file in files:
        record = applied.get(file.version)
        payload.append(
            {
                "version": file.version,
                "name": file.name,
                "filename": file.filename,
                "status": "applied" if record else "pending",
                "applied_at": record["applied_at"] if record else "",
            }
        )
    return payload


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Migration runner do Vuno Trader")
    parser.add_argument("command", nargs="?", default="up", choices=["up", "status"])
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(migration_status(), indent=2, ensure_ascii=False))
        return

    applied = run_migrations()
    output = {"applied": applied, "count": len(applied)}
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
