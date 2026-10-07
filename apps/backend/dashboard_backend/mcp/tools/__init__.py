from mcp.server.mcpserver import MCPServer

from . import projects, todos


def register_all(server: MCPServer) -> None:
    projects.register(server)
    todos.register(server)
