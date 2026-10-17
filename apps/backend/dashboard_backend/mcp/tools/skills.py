"""Skill tools: the server hands out the skills in ``.claude/skills/`` itself.

Only skills marked with ``metadata: mcp: true`` in their frontmatter are served —
repo skills such as ``widerspruchs-check`` need the code and are useless here.
The image carries the folder as ``/app/skills`` (named build context ``skills``),
so a client always gets the text that matches the deployed tools; a plain
checkout falls back to the repo folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from dashboard_backend.mcp.context import get_principal
from dashboard_backend.mcp.tools.projects import READ_ONLY

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _default_skills_dir() -> Path:
    bundled = _BACKEND_ROOT / "skills"
    if bundled.is_dir():
        return bundled
    return _BACKEND_ROOT.parent.parent / ".claude" / "skills"


SKILLS_DIR = _default_skills_dir()


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_skill(text: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md into frontmatter and body.

    Understands the simple form the skills use: one ``key: value`` per line and
    one level of indented sub-keys (``metadata:``). Anything fancier (folded
    strings, lists) is out of scope — the repo test catches such a skill.
    """
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    header = text[4:end]
    # Whatever follows the closing "---" on its line is dropped with it.
    body = text[end + 4 :].partition("\n")[2]
    meta: dict[str, Any] = {}
    section: str | None = None
    for line in header.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.strip().partition(":")
        if not sep:
            continue
        value = _unquote(value.strip())
        if line[0].isspace():
            if section is not None:
                meta[section][key] = value
        elif value:
            meta[key] = value
            section = None
        else:
            meta[key] = {}
            section = key
    return meta, body.lstrip("\n")


def _is_served(meta: dict[str, Any]) -> bool:
    metadata = meta.get("metadata")
    return isinstance(metadata, dict) and str(metadata.get("mcp", "")).lower() == "true"


def served_skills(skills_dir: Path | None = None) -> dict[str, tuple[Path, dict[str, Any], str]]:
    """Marked skills by name: (folder, frontmatter, body)."""
    root = skills_dir or SKILLS_DIR
    skills: dict[str, tuple[Path, dict[str, Any], str]] = {}
    if not root.is_dir():
        return skills
    for skill_file in sorted(root.glob("*/SKILL.md")):
        meta, body = parse_skill(skill_file.read_text(encoding="utf-8"))
        if _is_served(meta):
            skills[meta.get("name") or skill_file.parent.name] = (skill_file.parent, meta, body)
    return skills


def list_skills(*, ctx: Context) -> dict[str, Any]:
    """Skills (step-by-step guides) for multi-step work through this server, e.g. an
    import run end to end. Call this before such a task and load the matching one
    with get_skill — the text always matches the deployed tools."""
    get_principal(ctx)
    return {
        "skills": [
            {"name": name, "description": meta.get("description", "")}
            for name, (_, meta, _) in served_skills().items()
        ]
    }


def get_skill(name: str, file: str | None = None, *, ctx: Context) -> dict[str, Any]:
    """The guide of one skill from list_skills: ``content`` is its SKILL.md text
    (follow it), ``files`` its supporting files. Pass ``file`` (a path from
    ``files``) to read one supporting file instead."""
    get_principal(ctx)
    skill = served_skills().get(name)
    if skill is None:
        raise ToolError(f"Skill {name!r} nicht gefunden — list_skills zeigt die verfügbaren.")
    folder, meta, body = skill
    root = folder.resolve()
    files = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != "SKILL.md"
    )
    result: dict[str, Any] = {
        "name": name,
        "description": meta.get("description", ""),
        "files": files,
    }
    if file is None:
        result["content"] = body
        return result
    target = (root / file).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ToolError(f"Datei {file!r} gehört nicht zum Skill {name!r}.")
    try:
        result["file"] = target.relative_to(root).as_posix()
        result["content"] = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError(f"Datei {file!r} ist keine Textdatei.") from exc
    return result


def register(server: MCPServer) -> None:
    for fn in (list_skills, get_skill):
        server.add_tool(fn, annotations=READ_ONLY)
