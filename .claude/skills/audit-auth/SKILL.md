---
name: audit-auth
description: Use this skill when the user asks to audit API authentication, check which endpoints require auth, review endpoint security, list public vs protected routes, or verify frontend auth handling. Trigger phrases include "audit auth", "check endpoint security", "which endpoints need auth", "are endpoints protected", "review API auth".
version: 1.0.0
---

# API Auth Audit Skill

Audits all backend API endpoints for authentication requirements and verifies the frontend handles auth correctly.

## Steps

Always use the Explore subagent for this task to keep the main context clean. Pass it these instructions:

### 1. Discover auth dependencies

Read `apps/backend/dashboard_backend/core/security.py` and `apps/backend/dashboard_backend/routing/auth_router.py` to understand:
- All auth guard functions (name, role(s) required, behaviour on failure)
- Any automatic auth enforcement (e.g. AuthRouter adding auth to non-GET routes)

### 2. Enumerate all endpoints

Read every file in `apps/backend/dashboard_backend/api/v1/endpoints/` and `apps/backend/dashboard_backend/api/v1/api.py`. For each route decorator found, record:
- HTTP method
- Full path (combine router prefix + route path)
- Auth dependency in the function signature, if any
- Whether AuthRouter auto-auth would apply

### 3. Inspect frontend auth

Read `apps/frontend/src/shared/api/client.ts` (or `client.gen.ts`) and `apps/frontend/src/shared/api/queries.ts`:
- How are credentials stored and sent?
- Are mutations/queries for protected endpoints guarded by `user !== null` or role checks before being called?

Scan key feature components (Header, admin pages, import pages) for UI-level auth guards.

## Output format

Produce a report with four sections:

**Section 1 — Auth dependencies**
List each auth function: name, role(s), failure behaviour.

**Section 2 — Endpoint table**
| Method | Path | Auth Required | Role | Notes |

**Section 3 — Frontend auth handling**
- Credential storage and transmission mechanism
- Components with explicit auth guards and whether they match the backend requirement

**Section 4 — Issues & observations**
Flag anything worth reviewing:
- Public GETs exposing sensitive data (usernames, change history, etc.)
- Write endpoints without auth
- Frontend calling a protected endpoint without a corresponding UI guard
- Inconsistencies between similar endpoints
