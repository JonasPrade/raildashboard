"""Every migration has its own revision id and the chain has one head.

Alembic only warns about a duplicate id and keeps one of the files; the others
never run. Two branches that both picked the next free date id (as 20261022001
did twice) therefore break a deploy silently.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

_VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
_REVISION = re.compile(r"^revision(?:: str)? = ['\"]([^'\"]+)['\"]", re.MULTILINE)


def test_revision_ids_are_unique():
    ids = []
    for path in _VERSIONS.glob("*.py"):
        match = _REVISION.search(path.read_text(encoding="utf-8"))
        assert match, f"no revision id in {path.name}"
        ids.append(match.group(1))
    duplicates = [rev for rev, count in Counter(ids).items() if count > 1]
    assert duplicates == []


def test_single_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(_VERSIONS.parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(_VERSIONS.parent))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1
