from mcp.server.mcpserver import MCPServer

from . import bauportal, data_quality, finves, fulda, geometry, gvfg, haushalt, infraplan, projects, skills, todos, vib


def register_all(server: MCPServer) -> None:
    projects.register(server)
    finves.register(server)
    todos.register(server)
    geometry.register(server)
    data_quality.register(server)
    fulda.register(server)
    gvfg.register(server)
    haushalt.register(server)
    infraplan.register(server)
    vib.register(server)
    bauportal.register(server)
    skills.register(server)
