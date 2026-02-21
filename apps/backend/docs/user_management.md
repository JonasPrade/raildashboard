# User management

The API uses HTTP Basic Authentication. All HTTP methods except `GET` require a
valid login. Additional permission checks depend on the role of the authenticated
account.

---

## Roles

| Role   | Description | Access |
|--------|-------------|--------|
| `viewer` | Read-only access to published data. | All `GET` endpoints. |
| `editor` | Extended access for editorial changes. | Additional write endpoints (e.g. project data). |
| `admin`  | Full access including user management. | All endpoints; may create users, assign roles, delete users. |

Non-`GET` endpoints automatically verify that authentication is present.
Specific endpoints (e.g. user management) additionally require a particular role.

---

## CLI commands (via `make`)

All user management operations are available as Make targets from the **repo root**.
The backend `.venv` must exist (`make install` if not).

### List all users

```bash
make list-users
```

Output example:

```
Username  Role
--------  ----
admin     admin
alice     editor
bob       viewer
```

### Create a new user

```bash
make create-user USERNAME=alice ROLE=editor
```

Valid roles: `viewer`, `editor`, `admin`.

The script prompts for a password interactively (twice for confirmation).
It exits with an error if a user with that username already exists.

### Change a user's password

```bash
make change-password USERNAME=alice
```

The script prompts for the new password interactively (twice for confirmation).
It exits with an error if the user does not exist.

---

## Initial setup

When deploying for the first time, create the first admin account:

```bash
make create-user USERNAME=admin ROLE=admin
```

Because no admin exists yet, no authenticated session is required — the script
connects directly to the database.

---

## API endpoints (admin only)

After logging in as an admin, users can also be managed via the REST API:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/users/` | List all users |
| `POST` | `/api/v1/users/` | Create a new user |

These endpoints require the `admin` role. Use the CLI scripts above for
password changes, as no update endpoint exists yet.

---

## Authentication in requests

Use HTTP Basic Auth with every write request:

```
Authorization: Basic <base64(username:password)>
```

API clients should store credentials securely and only use TLS-secured
connections in production.

For tests, `tests/api/conftest.py` provides the `basic_auth_header()` helper.
