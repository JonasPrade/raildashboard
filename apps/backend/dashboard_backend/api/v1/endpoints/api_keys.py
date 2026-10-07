"""Personal API keys (Bearer auth for scripts and the MCP endpoint).

Mounted under ``/api-keys``. Every route requires a session cookie or HTTP
Basic — a key request cannot manage keys (no self-escalation path). Creating a
key requires ``mcp.access`` (admin-only for now); listing and revoking your own
keys only requires a login, so a key stays revocable after the capability is
withdrawn. Other users' keys need ``user.manage``.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from dashboard_backend.core.api_keys import MCP_PERMISSION
from dashboard_backend.core.permissions import is_valid_permission
from dashboard_backend.core.security import require_auth, require_permission
from dashboard_backend.crud import api_keys as api_keys_crud
from dashboard_backend.database import get_db
from dashboard_backend.models.users import User
from dashboard_backend.routing.auth_router import AuthRouter
from dashboard_backend.schemas.api_keys import ApiKeyCreate, ApiKeyCreated, ApiKeyRead

router = AuthRouter()


@router.get("/", response_model=list[ApiKeyRead])
def list_own_api_keys(
    current_user: User = Depends(require_auth(allow_api_key=False)),
    db: Session = Depends(get_db),
):
    """The caller's own keys (metadata only), newest first."""
    return [ApiKeyRead.from_key(k) for k in api_keys_crud.list_api_keys(db, current_user.id)]


@router.get("/all", response_model=list[ApiKeyRead])
def list_all_api_keys(
    current_user: User = Depends(require_permission("user.manage", allow_api_key=False)),
    db: Session = Depends(get_db),
):
    """Every user's keys, for the admin overview."""
    return [ApiKeyRead.from_key(k) for k in api_keys_crud.list_api_keys(db)]


@router.post("/", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(require_permission(MCP_PERMISSION, allow_api_key=False)),
    db: Session = Depends(get_db),
):
    """Create a key that expires after 90 days. The token is returned only here."""
    scopes = None
    if body.scopes is not None:
        unknown = sorted({s for s in body.scopes if not is_valid_permission(s)})
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission keys: {', '.join(unknown)}",
            )
        scopes = sorted(set(body.scopes))
    api_key, token = api_keys_crud.create_api_key(db, current_user, body.name.strip(), scopes)
    return ApiKeyCreated(**ApiKeyRead.from_key(api_key).model_dump(), token=token)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(require_auth(allow_api_key=False)),
    db: Session = Depends(get_db),
):
    """Revoke a key immediately. Own keys always; other users' keys with ``user.manage``."""
    api_key = api_keys_crud.get_api_key(db, key_id)
    if api_key is None or (
        api_key.user_id != current_user.id and not current_user.has_permission("user.manage")
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    api_keys_crud.revoke_api_key(db, api_key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
