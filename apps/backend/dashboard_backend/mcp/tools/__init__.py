from mcp.server.mcpserver import MCPServer

from . import (
    bauportal,
    changelog,
    condition,
    data_quality,
    finves,
    fulda,
    geometry,
    groups,
    gvfg,
    haushalt,
    infraplan,
    media,
    parliament,
    planning,
    projects,
    skills,
    system,
    todos,
    vib,
)


def register_all(server: MCPServer) -> None:
    projects.register(server)
    changelog.register(server)
    groups.register(server)
    planning.register(server)
    finves.register(server)
    todos.register(server)
    geometry.register(server)
    data_quality.register(server)
    fulda.register(server)
    gvfg.register(server)
    haushalt.register(server)
    infraplan.register(server)
    condition.register(server)
    vib.register(server)
    bauportal.register(server)
    media.register(server)
    parliament.register(server)
    system.register(server)
    skills.register(server)
