class RoutingUpstreamError(RuntimeError):
    """Raised when the routing service fails with a server error."""


class RoutingNoPathError(RuntimeError):
    """Raised when the routing service cannot find a path."""


class TransientFetchError(RuntimeError):
    """A network failure against an external source (timeout, refused, 5xx).

    Routine jobs retry these up to three times (feature-routine-abrufe.md, E4);
    any other error — an unexpected answer, a data error — fails at once.
    """
