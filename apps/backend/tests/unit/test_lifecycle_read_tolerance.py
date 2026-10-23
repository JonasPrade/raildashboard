"""Response schemas read lifecycle values they do not know as AKTIV (rollback safety,
docs/features/feature-project-replacement.md → W4)."""

import pytest
from pydantic import ValidationError

from dashboard_backend.schemas.projects.progress_schema import (
    ProgressChildSchema,
    ProjectProgressUpdate,
)


def _child(lifecycle: str) -> ProgressChildSchema:
    return ProgressChildSchema(
        project_id=1, name="X", effective_phase="BAU", lifecycle_status=lifecycle
    )


def test_known_value_passes_through():
    assert _child("PAUSIERT").lifecycle_status == "PAUSIERT"


def test_unknown_value_reads_as_aktiv():
    assert _child("SPAETER_NEU").lifecycle_status == "AKTIV"


def test_input_still_rejects_unknown_value():
    with pytest.raises(ValidationError):
        ProjectProgressUpdate(lifecycle_status="SPAETER_NEU")
