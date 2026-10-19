"""MCP server instance and its ASGI mount.

Streamable HTTP, stateless and with plain JSON responses: the backend may run
several Uvicorn workers, and a session held in one process would break as soon
as a follow-up request lands on another one.

The SDK's session manager can only be started once per instance, so
:class:`McpEndpoint` builds a fresh server inside every application lifespan
(production starts it once; the test suite enters the lifespan repeatedly).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from dashboard_backend.mcp.auth import McpAuthMiddleware
from dashboard_backend.mcp.context import RouteServiceProvider, SessionProvider
from dashboard_backend.mcp.tools import register_all

MCP_PATH = "/mcp"

INSTRUCTIONS = (
    "Schienendashboard: Eisenbahn-Infrastrukturprojekte in Deutschland mit "
    "Finanzierung (FinVe, Haushalt), Planungsstand und Aufgaben. Projekte zuerst "
    "mit list_projects suchen, dann per id mit den get_*-Tools vertiefen. "
    "FinVe frei nach Nummer, Name oder Bedarfsplannummer mit list_finves suchen "
    "(auch ohne Projektzuordnung), Details mit get_finve. "
    "GVFG-Bundesprogramm: Ausgaben mit list_gvfg_programs, Vorhaben mit "
    "list_gvfg_entries (Schlüssel, Name, ohne Projekt), Förderung eines Projekts mit "
    "list_project_gvfg, Verlauf über die Ausgaben mit get_gvfg_entry. "
    "Schreibende Tools wirken sofort und stehen im Änderungsprotokoll. "
    "Projektlängen kommen aus der Geometrie (compute_project_length mit apply), "
    "nicht aus veröffentlichten Angaben. Geometrie: Bahnstrecken mit "
    "route_project_geometry über das Schienennetz routen (Betriebsstellen mit "
    "search_operational_points finden, erst ohne apply prüfen); Neubaustrecken, "
    "Punkte und Korrekturen mit edit_project_geometry; Bestand mit "
    "get_project_geometry ansehen. Datenpflege über viele Projekte: "
    "list_data_gaps (fehlende Daten) und check_geometry (auffällige Geometrien) "
    "statt jedes Projekt einzeln abzurufen. "
    "Für mehrstufige Abläufe (z. B. Importe) zuerst list_skills aufrufen und die "
    "passende Anleitung mit get_skill laden; sie passt immer zu den laufenden Tools."
)


def build_server() -> MCPServer:
    server = MCPServer(name="raildashboard", instructions=INSTRUCTIONS)
    register_all(server)
    return server


class McpEndpoint:
    """ASGI app for ``/mcp``: bearer auth in front of the SDK transport."""

    def __init__(
        self,
        session_provider: SessionProvider,
        route_service_provider: RouteServiceProvider | None = None,
    ) -> None:
        self._session_provider = session_provider
        self._route_service_provider = route_service_provider
        self._app: ASGIApp | None = None

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        server = build_server()
        transport = server.streamable_http_app(
            streamable_http_path=MCP_PATH,
            json_response=True,
            stateless_http=True,
            # Only bearer keys are accepted (no cookies), so DNS rebinding gains
            # an attacker nothing; the SDK default would reject every non-local Host.
            transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        )
        async with server.session_manager.run():
            self._app = McpAuthMiddleware(
                transport, self._session_provider, self._route_service_provider
            )
            try:
                yield
            finally:
                self._app = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._app is None:
            await JSONResponse({"detail": "MCP server not running"}, status_code=503)(
                scope, receive, send
            )
            return
        await self._app(scope, receive, send)
