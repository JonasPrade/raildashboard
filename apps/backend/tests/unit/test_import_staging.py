"""Import PDFs travel to Celery as a staged file name, not as bytes (#149).

Covers the staging helpers in ``utils/file_storage.py``, the dispatch helper
``api.deps.launch_with_staged_pdf`` and the promise every parse task makes:
the staged file is gone afterwards, whether the parse succeeded or failed.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import dashboard_backend.api.deps as deps
import dashboard_backend.utils.file_storage as fs
from dashboard_backend.tasks import fulda as fulda_task
from dashboard_backend.tasks import haushalt as haushalt_task
from dashboard_backend.tasks import vib as vib_task

PDF = b"%PDF-1.4 staged import"


@pytest.fixture(autouse=True)
def staging_dir(tmp_path, monkeypatch) -> Path:
    monkeypatch.setattr(fs, "_staging_root", lambda: tmp_path.resolve())
    return tmp_path


def test_stage_writes_file_and_returns_bare_name(staging_dir):
    name = fs.stage_import_pdf(PDF)

    assert "/" not in name and name.endswith(".pdf")
    assert (staging_dir / name).read_bytes() == PDF


@pytest.mark.parametrize("name", ["../etc/passwd", "sub/x.pdf", "", ".."])
def test_staged_path_rejects_anything_but_a_bare_name(name):
    with pytest.raises(ValueError):
        fs._staged_path(name)


def test_consume_yields_bytes_and_deletes_file(staging_dir):
    name = fs.stage_import_pdf(PDF)

    with fs.consume_staged_import(name) as data:
        assert data == PDF

    assert not (staging_dir / name).exists()


def test_consume_deletes_file_when_the_work_fails(staging_dir):
    name = fs.stage_import_pdf(PDF)

    with pytest.raises(RuntimeError):
        with fs.consume_staged_import(name):
            raise RuntimeError("parse crashed")

    assert not (staging_dir / name).exists()


def test_staging_sweeps_files_no_task_picked_up(staging_dir):
    stale = staging_dir / "stale.pdf"
    stale.write_bytes(PDF)
    old = time.time() - fs.STAGED_IMPORT_MAX_AGE_SECONDS - 60
    os.utime(stale, (old, old))
    fresh = staging_dir / "fresh.pdf"
    fresh.write_bytes(PDF)

    fs.stage_import_pdf(PDF)

    assert not stale.exists()
    assert fresh.exists()


def test_launch_passes_only_the_file_name_to_the_task(staging_dir):
    calls = []

    class _Task:
        def delay(self, *args):
            calls.append(args)
            return "result"

    assert deps.launch_with_staged_pdf(_Task(), PDF, 2027, "b.pdf") == "result"

    (staged_name, *rest), = calls
    assert isinstance(staged_name, str)
    assert rest == [2027, "b.pdf"]
    assert (staging_dir / staged_name).read_bytes() == PDF


def test_launch_removes_the_file_when_dispatch_fails(staging_dir):
    class _Task:
        def delay(self, *args):
            raise ConnectionError("broker down")

    with pytest.raises(ConnectionError):
        deps.launch_with_staged_pdf(_Task(), PDF, 2027)

    assert list(staging_dir.iterdir()) == []


@pytest.mark.parametrize(
    "task, module, body_name",
    [
        (haushalt_task.parse_haushalt_pdf, haushalt_task, "run_haushalt_parse"),
        (vib_task.parse_vib_pdf, vib_task, "run_vib_parse"),
        (fulda_task.parse_fulda_pdf, fulda_task, "run_fulda_parse"),
    ],
)
@pytest.mark.parametrize("fails", [False, True])
def test_parse_tasks_read_the_staged_file_and_clean_up(
    staging_dir, monkeypatch, task, module, body_name, fails
):
    seen = []

    def _body(*args, **kwargs):
        seen.append(next(a for a in args if isinstance(a, bytes)))
        if fails:
            raise RuntimeError("parse crashed")
        return {"ok": True}

    monkeypatch.setattr(module, body_name, _body)
    name = fs.stage_import_pdf(PDF)

    if fails:
        with pytest.raises(RuntimeError):
            task.apply(args=(name, 2027, "x.pdf", {"id": 1, "username": "u"}), throw=True)
    else:
        result = task.apply(args=(name, 2027, "x.pdf", {"id": 1, "username": "u"}), throw=True)
        assert result.get() == {"ok": True}

    assert seen == [PDF]
    assert not (staging_dir / name).exists()
