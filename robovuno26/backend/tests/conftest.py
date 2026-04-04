from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _set_test_env(monkeypatch: pytest.MonkeyPatch, db_path: Path) -> None:
    monkeypatch.setenv("DB_DRIVER", "sqlite")
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "http://127.0.0.1:8000")
    monkeypatch.setenv("LOG_JSON", "false")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "lax")
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("LOGIN_WINDOW_MINUTES", "15")
    monkeypatch.setenv("LOGIN_BLOCK_MINUTES", "20")


def _purge_app_modules() -> None:
    to_remove = [name for name in sys.modules if name == "app" or name.startswith("app.")]
    for name in to_remove:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()


@pytest.fixture
def test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "test.db"
    _set_test_env(monkeypatch, db_path)
    _purge_app_modules()
    return db_path


@pytest.fixture
def client(test_env: Path) -> TestClient:
    main = importlib.import_module("app.main")
    with TestClient(main.app) as test_client:
        yield test_client
