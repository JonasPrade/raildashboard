# Plan: Passwort-Reset per E-Mail (Schritt 3 Benutzerverwaltung)

Entspricht Schritt 3 in der [Roadmap](roadmap.md).

---

## Flow

```
[User] "Passwort vergessen?" im Login-Modal
    → gibt E-Mail ein
    → Backend sucht User, erstellt Token (UUID4, 1h gültig), sendet Mail
    → User klickt Link: https://dashboard.example.com/reset-password?token=<UUID>
    → Frontend zeigt Formular für neues Passwort
    → Backend validiert Token, setzt Passwort, invalidiert Token
```

---

## 1. Datenbank

### `users`-Tabelle — neues Feld

```python
email: Mapped[str | None] = mapped_column(String(254), unique=True, nullable=True)
```

Nullable, weil bestehende User noch keine E-Mail haben. Admins tragen sie über die
Benutzerverwaltung ein.

### Neue Tabelle `password_reset_tokens`

```python
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: int                  # PK
    token: str               # UUID4, unique, indexed
    user_id: int             # FK → users.id, ON DELETE CASCADE
    expires_at: datetime     # jetzt + 1h
    used_at: datetime | None # NULL = noch gültig
```

→ 2 Alembic-Migrationen erforderlich

---

## 2. E-Mail-Infrastruktur

### Empfohlene Bibliothek: `fastapi-mail`

```
pip install fastapi-mail
```

- Async, passt zu FastAPI
- Unterstützt SMTP + HTML-Templates via Jinja2
- Einfache Konfiguration über `ConnectionConfig`

Für bessere Deliverability (viele externe User): **Mailgun**, **Postmark** oder **AWS SES**
(dann API-Key statt SMTP-Credentials). Für interne Tools reicht SMTP.

### Umgebungsvariablen (`.env`)

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=secret
SMTP_FROM_EMAIL=noreply@dashboard.example.com
SMTP_FROM_NAME=Schienenprojekte-Dashboard
SMTP_TLS=true
APP_BASE_URL=https://dashboard.example.com
```

---

## 3. Backend

### Neue/geänderte Dateien

| Datei | Inhalt |
|---|---|
| `models/password_reset_token.py` | ORM-Modell (s. o.) |
| `crud/password_reset.py` | `create_token()`, `get_token()`, `mark_used()` |
| `schemas/auth.py` | `PasswordResetRequest(email)`, `PasswordResetConfirm(token, password)` |
| `core/email.py` | `send_reset_email(to, reset_url)` via fastapi-mail |
| `api/v1/endpoints/auth.py` | 2 neue Endpoints (eigener Router, **kein Auth**) |
| `api/v1/router.py` | `auth`-Router einbinden (`/api/v1/auth/`) |
| `models/users.py` | `email`-Feld ergänzen |
| `schemas/users.py` | `UserRead` + `UserCreate` um `email` erweitern |

### Neue Endpoints

```
POST /api/v1/auth/request-reset
  Body: { "email": "user@example.com" }
  Response: 200 (immer — kein Leak ob E-Mail existiert)
  Intern: Token erstellen, Reset-Mail versenden

POST /api/v1/auth/reset-password
  Body: { "token": "<UUID>", "password": "neues_passwort" }
  Response: 204 bei Erfolg
            400 wenn Token ungültig / abgelaufen / bereits verwendet
            404 wenn User nicht mehr existiert
```

### Sicherheit

- Token = UUID4 (122 Bit Entropie — nicht ratbar)
- Gültigkeitsdauer: 1 Stunde
- Einmalverwendung (`used_at` wird gesetzt)
- `request-reset` gibt immer 200 zurück (verhindert E-Mail-Enumeration)
- Für später nachrüstbar: Rate-Limiting via `slowapi`

### Tests

- `request-reset` mit bekannter E-Mail → 200, Token in DB
- `request-reset` mit unbekannter E-Mail → 200 (kein Fehler)
- `reset-password` mit gültigem Token → 204, neues Passwort funktioniert
- `reset-password` mit abgelaufenem Token → 400
- `reset-password` mit bereits benutztem Token → 400
- `reset-password` mit unbekanntem Token → 400

---

## 4. Admin-Erweiterungen (UsersPage)

- `UsersPage` → neue Spalte `E-Mail`
- `CreateUserModal` → optionales E-Mail-Feld
- Optional: Button "Reset-Mail senden" pro User-Zeile (Admin triggert Reset für anderen User)

---

## 5. Frontend

### `LoginModal.tsx`

- Link "Passwort vergessen?" → wechselt zu Step 2 im Modal

### Step 2: E-Mail-Formular

```
[TextInput: E-Mail-Adresse]
[Button: Reset-Link senden]
→ Bestätigung: "Falls ein Konto mit dieser Adresse existiert, wurde ein Link versendet."
```

### Neue Route `/reset-password`

- Liest `?token=...` aus URL-Params
- Zeigt zwei `PasswordInput`-Felder (neues Passwort + Bestätigung)
- Client-seitige Validierung: ≥ 8 Zeichen, Übereinstimmung
- Bei Erfolg: Redirect zu `/` + Login-Modal öffnet sich automatisch
- Bei ungültigem Token: Fehlermeldung mit Link zurück zum Login

---

## 6. Implementierungsreihenfolge

1. `email`-Feld in `User`-Modell + Migration
2. `password_reset_tokens`-Tabelle + Migration
3. SMTP-Konfiguration in Settings + `send_reset_email()`
4. CRUD für Tokens
5. Endpoints `request-reset` + `reset-password` + Tests
6. Admin-UI: E-Mail-Feld in `CreateUserModal` + `UsersPage`
7. Frontend: "Passwort vergessen?" in `LoginModal`
8. Frontend: `/reset-password`-Route
