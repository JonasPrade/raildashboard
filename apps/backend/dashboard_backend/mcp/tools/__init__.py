from mcp.server.mcpserver import MCPServer

from . import data_quality, finves, fulda, geometry, projects, skills, todos


def register_all(server: MCPServer) -> None:
    projects.register(server)
    finves.register(server)
    todos.register(server)
    geometry.register(server)
    data_quality.register(server)
    fulda.register(server)
    skills.register(server)
