"""Start check for the maintenance scripts in the runtime image.

Run by the `scripts-check` stage of the Dockerfile (part of `make test`), never in
production. Every ``scripts/*.py`` is loaded the way ``python scripts/<name>.py`` loads
it inside the container: working directory ``/app``, ``sys.path[0]`` is ``scripts/``,
and whatever ``PYTHONPATH`` the image sets. The module runs under a name other than
``__main__``, so its imports run but ``main()`` does not: no database, no side effects.

Why: ``docker compose exec backend python scripts/recompute_progress.py`` failed with
``ModuleNotFoundError: dashboard_backend`` because the image set no ``PYTHONPATH`` and
nothing started the scripts there (entrypoint and Alembic do not need the package).

A script without an ``if __name__ == "__main__":`` guard would start its job on import,
so it is reported as an error instead of being loaded.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"

# Placeholders for the required Settings, only so that importing the package works.
# Same idea as tests/conftest.py, which cannot be imported here: it puts the project
# root on sys.path and would hide exactly the failure this check looks for.
DUMMY_ENV = {
    "DATABASE_URL": "sqlite:///:memory:",
    "SESSION_SECRET_KEY": "script-check-not-a-secret",
    "RINF_API_URL": "https://example.invalid",
    "RINF_USERNAME": "check",
    "RINF_PASSWORD": "check",
    "ROUTING_BASE_URL": "http://routing.invalid",
    "ROUTING_TIMEOUT_SECONDS": "1.0",
    "GRAPH_VERSION": "check",
    "CELERY_BROKER_URL": "memory://",
    "CELERY_RESULT_BACKEND": "cache+memory://",
    "START_BACKGROUND_JOBS": "false",
    "ROUTINE_JOBS_ENABLED": "false",
}

# Loads a script like `python <path>` would, without running it as __main__.
LOAD = (
    "import os, runpy, sys\n"
    "path = os.path.abspath(sys.argv[1])\n"
    "sys.path[0] = os.path.dirname(path)\n"
    "sys.argv = [path]\n"
    "runpy.run_path(path, run_name='script_check')\n"
)

# alembic/ (the migrations) has no __init__.py and sits on sys.path once /app does;
# the installed package must still win.
ALEMBIC = (
    "import alembic, sys\n"
    "assert 'site-packages' in alembic.__file__, alembic.__file__\n"
)


def has_main_guard(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        left = node.test.left
        if isinstance(left, ast.Name) and left.id == "__name__":
            return True
    return False


def run(code: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**DUMMY_ENV, **os.environ}
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    failures: list[str] = []

    result = run(ALEMBIC)
    if result.returncode:
        failures.append(f"alembic: {result.stderr.strip().splitlines()[-1:]}")

    for script in sorted(SCRIPTS.glob("*.py")):
        name = f"scripts/{script.name}"
        if not has_main_guard(script):
            failures.append(f"{name}: no `if __name__ == \"__main__\":` guard")
            continue
        result = run(LOAD, str(script))
        if result.returncode:
            tail = result.stderr.strip().splitlines()[-1:] or ["(no output)"]
            failures.append(f"{name}: {tail[0]}")
        else:
            print(f"ok  {name}")

    if failures:
        print("\nScripts that do not start in this image:", file=sys.stderr)
        for line in failures:
            print(f"  FAIL {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
