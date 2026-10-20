from mcp.server.mcpserver import MCPServer

from . import data_quality, finves, fulda, geometry, gvfg, infraplan, projects, skills, todos


def register_all(server: MCPServer) -> None:
    projects.register(server)
    finves.register(server)
    todos.register(server)
    geometry.register(server)
    data_quality.register(server)
    fulda.register(server)
    gvfg.register(server)
    infraplan.register(server)
    skills.register(server)
