from __future__ import annotations

import inspect
from typing import Any, Callable, Sequence

from fastapi import APIRouter, Depends
from fastapi.params import Depends as DependsParam

from dashboard_backend.core.security import ensure_authenticated_dependency, has_role_dependency, require_roles


class AuthRouter(APIRouter):
    """APIRouter enforcing authentication for all non-GET endpoints."""

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        dependencies: Sequence[DependsParam] | None = None,
        methods: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        dependencies = list(dependencies or [])
        methods = methods or ["GET"]

        if not ensure_authenticated_dependency(dependencies) and not self._endpoint_requires_roles(endpoint):
            if any(method.upper() != "GET" for method in methods):
                dependencies.append(Depends(require_roles()))

        super().add_api_route(
            path,
            endpoint,
            dependencies=dependencies,
            methods=methods,
            **kwargs,
        )

    @staticmethod
    def _endpoint_requires_roles(endpoint: Callable[..., Any]) -> bool:
        signature = inspect.signature(endpoint)
        for parameter in signature.parameters.values():
            default = parameter.default
            if isinstance(default, DependsParam) and has_role_dependency(default.dependency):
                return True
        return False

