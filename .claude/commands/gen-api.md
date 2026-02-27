---
description: Regenerate frontend API client from OpenAPI schema
allowed-tools: Bash, Read, Glob
---

## Your task

Regenerate the frontend API client from the running backend's OpenAPI schema.

**Step 1 — Verify backend is running**

Run a health check against the backend:

```
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health
```

If the response is not `200`, also try `http://localhost:8000/docs` (FastAPI serves the OpenAPI UI there). If the backend is not reachable, stop and inform the user with a clear message:

> Backend is not running at http://localhost:8000. Please start it with `make backend` or `make dev` and try again.

Do not proceed past this step if the backend is unavailable.

**Step 2 — Capture pre-run state**

Record the current state of the generated client files so you can report what changed:

```
git diff --name-only apps/frontend/src/client/
```

Also note the commit hash of the last change to those files:

```
git log --oneline -1 -- apps/frontend/src/client/
```

**Step 3 — Run `make gen-api`**

Execute:

```
make gen-api
```

Report the full output to the user. If the command fails, show the error and stop.

**Step 4 — Report changed files**

After the command succeeds, run:

```
git diff --name-only apps/frontend/src/client/
```

List all changed files. If nothing changed, say so explicitly — this means the OpenAPI contract is already in sync.

If files changed, briefly summarise the nature of the changes (e.g., "2 new endpoints added", "response type of `ProjectRead` changed") based on the diff output:

```
git diff apps/frontend/src/client/
```

Keep the summary concise — one line per changed file is enough.
