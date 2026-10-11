"""Is the database on a revision this code does not know?

Called by ``docker-entrypoint.sh`` before ``alembic upgrade head``. Exit code 0
means the database is *ahead* of this code and the migration is skipped. Any
other exit code, including an error in this script, means: migrate as usual.

This happens on a rollback. A new release has already run its migration and
then does not become healthy; ``deploy/prod.sh`` starts the previous image.
That image's Alembic does not know the new revision, ``upgrade head`` aborts,
the entrypoint with it, and the rollback that exists for exactly this case
never comes up. Because migrations must stay backward-compatible
(expand/contract, DEPLOY.md), the older code can run against the newer schema;
it just must not touch it.

Deliberately narrow: the migration is skipped only when *every* recorded
revision is unknown. A missing or empty ``alembic_version`` table, a known
revision, or an unreachable database all take the normal path.

Counterpart of ``scripts/db_voraus.py`` in JonasPrade/dtakt_mitglied, written
against SQLAlchemy instead of sqlite3 because this database is Postgres.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def known_revisions(alembic_ini: Path = ALEMBIC_INI) -> set[str]:
    config = Config(str(alembic_ini))
    # script_location in alembic.ini is relative; anchor it next to the ini so
    # the result does not depend on the current working directory.
    config.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    return {s.revision for s in ScriptDirectory.from_config(config).walk_revisions()}


def database_is_ahead(url: str, alembic_ini: Path = ALEMBIC_INI) -> bool:
    try:
        engine = create_engine(url)
    except (SQLAlchemyError, ValueError):
        return False
    try:
        with engine.connect() as conn:
            if not inspect(conn).has_table("alembic_version"):
                return False
            revisions = [r for (r,) in conn.execute(text("SELECT version_num FROM alembic_version"))]
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()
    if not revisions:
        return False

    unknown = [r for r in revisions if r not in known_revisions(alembic_ini)]
    if unknown and len(unknown) == len(revisions):
        print(
            f"[entrypoint] Database is on {', '.join(unknown)}, which this code does not "
            "know, so it is newer (rollback?). Skipping the migration."
        )
        return True
    return False


if __name__ == "__main__":
    sys.exit(0 if database_is_ahead(os.environ["DATABASE_URL"]) else 1)
