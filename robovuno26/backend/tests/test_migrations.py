from __future__ import annotations

import importlib


def test_migrations_are_idempotent(test_env):
    migrations = importlib.import_module("app.migrations")

    first_run = migrations.run_migrations()
    second_run = migrations.run_migrations()
    status = migrations.migration_status()

    assert any(item["status"] == "applied" for item in status)
    assert second_run == []
    assert len(first_run) >= 1
