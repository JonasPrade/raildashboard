from mcp.server.mcpserver import MCPServer

from . import geometry, projects, todos


def register_all(server: MCPServer) -> None:
    projects.register(server)
    todos.register(server)
    geometry.register(server)
