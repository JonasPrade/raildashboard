class RoutingUpstreamError(RuntimeError):
    """Raised when the routing service fails with a server error."""


class RoutingNoPathError(RuntimeError):
    """Raised when the routing service cannot find a path."""
