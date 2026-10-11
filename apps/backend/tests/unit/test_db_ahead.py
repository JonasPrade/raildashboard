"""scripts/db_ahead.py decides whether the entrypoint skips `alembic upgrade head`.

Skipping wrongly would leave a database unmigrated; not skipping when it should
would keep a rollback after a migration from ever starting (DEPLOY.md).
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "db_ahead.py"
_spec = importlib.util.spec_from_file_location("db_ahead", _SCRIPT)
db_ahead = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(db_ahead)


@pytest.fixture
def make_db(tmp_path):
    def _make(*revisions: str, table: bool = True) -> str:
        path = tmp_path / "db.sqlite"
        conn = sqlite3.connect(path)
        if table:
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            conn.executemany("INSERT INTO alembic_version VALUES (?)", [(r,) for r in revisions])
        conn.commit()
        conn.close()
        return f"sqlite:///{path}"

    return _make


def _a_known_revision() -> str:
    return sorted(db_ahead.known_revisions())[0]


def test_unknown_revision_means_ahead(make_db):
    assert db_ahead.database_is_ahead(make_db("ffffffffffff")) is True


def test_known_revision_migrates(make_db):
    assert db_ahead.database_is_ahead(make_db(_a_known_revision())) is False


def test_mixed_known_and_unknown_migrates(make_db):
    assert db_ahead.database_is_ahead(make_db(_a_known_revision(), "ffffffffffff")) is False


def test_empty_version_table_migrates(make_db):
    assert db_ahead.database_is_ahead(make_db()) is False


def test_missing_version_table_migrates(make_db):
    assert db_ahead.database_is_ahead(make_db(table=False)) is False


def test_unreachable_database_migrates(tmp_path):
    url = f"sqlite:///{tmp_path / 'missing-dir' / 'db.sqlite'}"
    assert db_ahead.database_is_ahead(url) is False


def test_known_revisions_do_not_depend_on_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert db_ahead.known_revisions()  # non-empty from any working directory


def test_head_of_this_code_is_known():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(db_ahead.ALEMBIC_INI))
    config.set_main_option("script_location", str(db_ahead.ALEMBIC_INI.parent / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    assert set(heads) <= db_ahead.known_revisions()
