from typing import Literal

from pydantic import BaseModel


class RoutingHealthSchema(BaseModel):
    """The routing service (GraphHopper) at one moment."""

    status: Literal["ok", "error", "unreachable"]
    # Host only; credentials, if any, are never handed out.
    base_url: str
    http_status: int | None = None
    latency_ms: int | None = None
    # German, and it names the next step rather than only the state.
    message: str
    detail: str | None = None
    checked_at: float
