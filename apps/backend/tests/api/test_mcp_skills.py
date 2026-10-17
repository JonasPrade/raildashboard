"""MCP skills: list_skills / get_skill serve the marked skills from .claude/skills."""

from __future__ import annotations

import pytest

from dashboard_backend.mcp.tools import skills
from tests.api.test_mcp_server import (  # noqa: F401 - fixtures
    _call,
    _payload,
    admin_token,
    mcp_client,
)

SERVED = """---
name: import-run
description: "Führt einen Import bis zur Bestätigung."
metadata:
  mcp: true
---

# Import

Schritt 1.
"""

REPO_ONLY = """---
name: repo-check
description: Needs the code.
---

Body.
"""


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    served = tmp_path / "import-run"
    (served / "references").mkdir(parents=True)
    (served / "SKILL.md").write_text(SERVED, encoding="utf-8")
    (served / "references" / "mapping.md").write_text("Zuordnung", encoding="utf-8")
    (tmp_path / "repo-check").mkdir()
    (tmp_path / "repo-check" / "SKILL.md").write_text(REPO_ONLY, encoding="utf-8")
    (tmp_path / "README.md").write_text("not a skill", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside", encoding="utf-8")
    monkeypatch.setattr(skills, "SKILLS_DIR", tmp_path)
    return tmp_path


def test_parse_skill_frontmatter():
    meta, body = skills.parse_skill(SERVED)
    assert meta == {
        "name": "import-run",
        "description": "Führt einen Import bis zur Bestätigung.",
        "metadata": {"mcp": "true"},
    }
    assert body.startswith("# Import")


def test_list_skills_only_marked(mcp_client, admin_token, skills_dir):
    payload = _payload(_call(mcp_client, admin_token, "list_skills"))
    assert payload == {
        "skills": [
            {"name": "import-run", "description": "Führt einen Import bis zur Bestätigung."}
        ]
    }


def test_get_skill_content_and_file(mcp_client, admin_token, skills_dir):
    payload = _payload(_call(mcp_client, admin_token, "get_skill", {"name": "import-run"}))
    assert payload["content"].startswith("# Import")
    assert "mcp: true" not in payload["content"]
    assert payload["files"] == ["references/mapping.md"]

    ref = _payload(
        _call(
            mcp_client,
            admin_token,
            "get_skill",
            {"name": "import-run", "file": "references/mapping.md"},
        )
    )
    assert ref["file"] == "references/mapping.md"
    assert ref["content"] == "Zuordnung"


@pytest.mark.parametrize(
    "arguments",
    [
        {"name": "repo-check"},
        {"name": "missing"},
        {"name": "import-run", "file": "../secret.txt"},
        {"name": "import-run", "file": "nope.md"},
    ],
)
def test_get_skill_rejects(mcp_client, admin_token, skills_dir, arguments):
    result = _call(mcp_client, admin_token, "get_skill", arguments)
    assert result["isError"] is True


def test_repo_skills_are_valid():
    """Every skill in the real folder parses — a broken one must fail the build,
    not silently vanish from list_skills."""
    skill_files = sorted(skills.SKILLS_DIR.glob("*/SKILL.md"))
    assert skill_files, f"no skills found in {skills.SKILLS_DIR}"
    for skill_file in skill_files:
        meta, body = skills.parse_skill(skill_file.read_text(encoding="utf-8"))
        assert meta.get("name") == skill_file.parent.name, skill_file
        # Folded/literal YAML strings (">", "|") are not supported by parse_skill.
        assert meta.get("description", "").rstrip("-") not in ("", ">", "|"), skill_file
        assert body.strip(), skill_file
