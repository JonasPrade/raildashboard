# Feature: Passwort zurücksetzen per E-Mail

## Ziel

Nutzer können ihr Passwort über einen per E-Mail gesendeten Reset-Link zurücksetzen. Admins können die E-Mail-Adresse eines Nutzers in der Benutzerverwaltung hinterlegen.

## Scope

- "Passwort vergessen?"-Link im Login-Modal
- Backend: Token-Generierung, E-Mail-Versand, Passwort-Reset
- Frontend: E-Mail-Formular im Login-Modal + `/reset-password`-Route
- Admin: E-Mail-Feld in Benutzerverwaltung

## Nicht im Scope

- Rate-Limiting (nachrüstbar via `slowapi`)
- Self-Service-Registrierung

## Verhalten

- "Passwort vergessen?" öffnet E-Mail-Eingabe im Login-Modal
- Backend antwortet immer mit 200 (kein E-Mail-Enumeration-Leak)
- Reset-Link ist 1 Stunde gültig und nur einmal verwendbar
- Nach erfolgreichem Reset: Redirect zu `/` + Login-Modal öffnet sich

## Akzeptanzkriterien

- Reset-Mail wird versendet wenn E-Mail bekannt
- Gültiger Token setzt Passwort zurück (204)
- Abgelaufener / bereits verwendeter Token gibt 400
- Unbekannte E-Mail gibt trotzdem 200

## Technische Hinweise

### Flow

```
User klickt "Passwort vergessen?"
  → gibt E-Mail ein
  → Backend erstellt Token (UUID4, 1h), sendet Mail
  → User klickt Link: /reset-password?token=<UUID>
  → Frontend zeigt Passwort-Formular
  → Backend validiert Token, setzt Passwort, invalidiert Token
```

### Datenbank

```python
# users-Tabelle: neues Feld
email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: int
    token: str        # UUID4, unique, indexed
    user_id: int      # FK → users.id, ON DELETE CASCADE
    expires_at: datetime
    used_at: datetime | None
```

2 Alembic-Migrationen erforderlich.

### Backend-Dateien

| Datei | Inhalt |
|---|---|
| `models/password_reset_token.py` | ORM-Modell |
| `crud/password_reset.py` | `create_token()`, `get_token()`, `mark_used()` |
| `schemas/auth.py` | `PasswordResetRequest(email)`, `PasswordResetConfirm(token, password)` |
| `core/email.py` | `send_reset_email(to, reset_url)` via `fastapi-mail` |
| `api/v1/endpoints/auth.py` | 2 neue Endpoints (kein Auth) |
| `models/users.py` | `email`-Feld ergänzen |
| `schemas/users.py` | `UserRead` + `UserCreate` um `email` erweitern |

### Endpoints

```
POST /api/v1/auth/request-reset
  Body: { "email": "user@example.com" }
  Response: 200 (immer)

POST /api/v1/auth/reset-password
  Body: { "token": "<UUID>", "password": "neues_passwort" }
  Response: 204 | 400 | 404
```

### Umgebungsvariablen

```
SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
SMTP_FROM_EMAIL, SMTP_FROM_NAME, SMTP_TLS
APP_BASE_URL
```

### Frontend

- `LoginModal.tsx`: "Passwort vergessen?"-Link → Step 2 (E-Mail-Formular)
- Bestätigung: "Falls ein Konto mit dieser Adresse existiert, wurde ein Link versendet."
- Route `/reset-password`: liest `?token=`, zwei PasswordInput-Felder, Client-Validierung (≥ 8 Zeichen, Übereinstimmung)
- Admin `UsersPage`: E-Mail-Spalte + Feld in `CreateUserModal`

## Implementierungsreihenfolge

1. [ ] `email`-Feld in User-Modell + Migration
2. [ ] `password_reset_tokens`-Tabelle + Migration
3. [ ] SMTP-Config in Settings + `send_reset_email()`
4. [ ] CRUD für Tokens
5. [ ] Endpoints + Tests
6. [ ] Admin-UI: E-Mail-Feld in `CreateUserModal` + `UsersPage`
7. [ ] Frontend: "Passwort vergessen?" in `LoginModal`
8. [ ] Frontend: `/reset-password`-Route
