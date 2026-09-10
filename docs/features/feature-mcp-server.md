# Feature: MCP-Server mit API-Key-Authentifizierung

**Status: geplant (2026-09-09)** — Konzept abgestimmt, noch nicht implementiert.

## Ziel

Das Dashboard über das **Model Context Protocol (MCP)** für KI-Assistenten
zugänglich machen: Projekte, Finanzierung und Planungsstand abfragen und gezielt
fortschreiben, ohne den Umweg über die Weboberfläche. Der Zugriff läuft über
**persönliche API-Keys** und erbt dabei vollständig das bestehende Rollen- und
Rechtemodell — ein Key kann nie mehr als der Nutzer, dem er gehört.

## Designentscheidungen (mit dem Nutzer abgestimmt, 2026-09-09)

- **API-Keys statt OAuth** — nicht als Übergangslösung, sondern als eigene,
  bleibende Auth-Art. Der geplante Authentik-Umzug löst den *Menschen*-Login
  (Browser, SSO); Maschinen- und Agenten-Zugriff läuft auch danach über Keys.
  Es entsteht also kein Wegwerf-Code (siehe
  [Abgrenzung zu Authentik/OAuth](#abgrenzung-zu-authentikoauth)).
- **MCP-Server im Backend gemountet**, nicht als eigener Compose-Service. Ein
  Deployment, eine Auth-Kette, keine Token-Weitergabe zwischen zwei Prozessen.
  Ein separater Service brächte ein zweites Rechte-Modell und eine zusätzliche
  Vertrauensgrenze, ohne Gegenwert.
- **Tools rufen die vorhandene CRUD-/Service-Schicht**, nicht die eigene
  HTTP-API. Kein Selbstaufruf über das Netzwerk, keine doppelte Serialisierung.
- **Lesen *und* Schreiben** — Schreib-Tools sind über den bestehenden
  Permission-Katalog gegated und lassen sich pro Key zusätzlich einschränken
  (ein Key kann read-only sein, auch wenn sein Nutzer Editor ist).
- **Importe bleiben draußen** — VIB-/Haushalt-/PDF-Import sind langlaufende
  Celery-Jobs mit Mensch-im-Loop-Review; die gehören nicht in eine
  Tool-Aufruf-Semantik mit Sekunden-Timeout.

## Ausgangslage (Stand 2026-09-09)

- **Authentifizierung** (`core/security.py`): HTTP Basic (`HTTPBasic`) **oder**
  signiertes Session-Cookie (`session`, HMAC-SHA256, 7 Tage). Passwörter als
  PBKDF2-HMAC-SHA256 mit 390.000 Iterationen und zufälligem Salt; ein
  kurzlebiger Credential-Cache (5 min, HMAC-Fingerprint, Issue #92) fängt die
  PBKDF2-Kosten pro Request ab. Kein JWT, kein Bearer-Token, kein OAuth.
- **Rechte** (`core/permissions.py`): Capability-Katalog im Code
  (`project.edit`, `progress.edit`, `todo.create`, …), Rollen in der DB,
  `require_permission(*keys)` als FastAPI-Dependency,
  `User.has_permission()` mit Super-Admin-Bypass. Siehe
  `docs/features/feature-user-roles-permissions.md`.
- **API-Oberfläche**: `apps/backend/dashboard_backend/api/v1/` mit ~25 Routern,
  gemountet unter `/api/v1` (`main.py`), nginx leitet `/api/` an
  `backend:8000` weiter (`apps/frontend/nginx.conf`).
- **MCP existiert im Repo bisher nicht.**

## Abgrenzung zu Authentik/OAuth

Der Authentik-Umzug ist ein **eigenes, vorgelagertes oder paralleles Thema** und
nicht Teil dieses Features. Wichtig ist nur, dass dieses Feature ihn nicht
blockiert und von ihm nicht entwertet wird:

| | heute | nach Authentik |
|---|---|---|
| Menschen im Browser | Basic + Session-Cookie | OIDC-Login gegen Authentik |
| Agenten / Maschinen | **API-Key (dieses Feature)** | API-Key (unverändert) **oder** von Authentik ausgestelltes Token |
| MCP-Tools | unverändert | unverändert |
| Rechteprüfung | `User.has_permission()` | `User.has_permission()` |

Der Authentik-Umzug ergänzt später einen **zweiten Bearer-Zweig** an derselben
Stelle in derselben Dependency: `/mcp` wird Resource Server, das Bearer-Token
ist dann ein von Authentik signiertes JWT statt eines API-Keys. Tools,
Rechteprüfung und Datenmodell bleiben davon unberührt. Erst damit wird auch der
Connector-Weg über claude.ai möglich, der OAuth voraussetzt; Clients mit
konfigurierbaren Headern (Claude Code) funktionieren schon vorher.

## Scope

**In scope:**

1. Datenmodell `api_keys` inkl. Alembic-Migration.
2. Bearer-Auth als dritter Weg in der bestehenden Auth-Kette (gilt damit für
   die gesamte REST-API, nicht nur für MCP).
3. Key-Verwaltung: Endpunkte + Admin-UI (anlegen, auflisten, widerrufen).
4. MCP-Server unter `/mcp`, Streamable HTTP, im Backend gemountet.
5. Tool-Katalog (lesend + schreibend) mit Permission-Gates.
6. Tests, `make gen-api`, Deployment-Konfiguration, Doku.

**Out of scope:**

- OAuth / Authentik-Anbindung (eigenes Thema, siehe oben).
- Import-Pipelines als MCP-Tools (VIB, Haushalt, Bauportal, Fulda, Medien).
- Löschen von Projekten oder anderen Stammdaten über MCP.
- MCP-*Resources* und *Prompts* — die erste Ausbaustufe bietet nur *Tools*.
- Pro-Key-Ratelimits (nur `last_used_at`-Tracking, siehe Sicherheit).

## Datenmodell

Neue Tabelle **`api_keys`**:

| Spalte | Typ | Bedeutung |
|---|---|---|
| `id` | Integer, PK | |
| `user_id` | FK → `users.id`, cascade delete | Besitzer; der Key erbt dessen Rechte |
| `name` | String(100) | Klartext-Label („Claude Code Laptop") |
| `prefix` | String(12), unique, indexiert | Klartext-Teil des Tokens, dient dem Lookup |
| `key_hash` | String(64) | SHA-256-Hex des Geheimnisses |
| `scopes` | JSON/Array of String, nullable | `NULL` = alle Rechte des Nutzers; sonst Schnittmenge |
| `created_at` | DateTime | |
| `last_used_at` | DateTime, nullable | gedrosselt geschrieben (siehe unten) |
| `expires_at` | DateTime, nullable | `NULL` = unbegrenzt |
| `revoked_at` | DateTime, nullable | gesetzt = sofort ungültig; Zeile bleibt für die Nachvollziehbarkeit |

Migration über `make migrate-create MSG="add api_keys table"` — nie `alembic`
direkt aufrufen.

## Token-Format und Prüfung

Format: `rdb_<prefix>_<secret>`

- `prefix`: 12 Zeichen, base32, im Klartext gespeichert und indexiert → der
  Lookup ist ein einzelner Index-Treffer statt eines Scans über alle Keys.
- `secret`: 32 zufällige Bytes (`secrets.token_urlsafe(32)`).
- Gespeichert wird `sha256(secret)`, verglichen mit `hmac.compare_digest`.

**Warum SHA-256 und nicht PBKDF2**: die 390.000 Iterationen in `security.py`
sind für Passwörter richtig, weil Passwörter wenig Entropie haben. Ein Token
mit 256 Bit Entropie ist gegen Offline-Brute-Force auch mit einem einfachen
Hash unangreifbar — und PBKDF2 pro Request wäre bei einem Agenten, der Dutzende
Tool-Calls hintereinander absetzt, nicht bezahlbar. Der Basic-Auth-Cache aus
Issue #92 wird für Keys damit gar nicht erst gebraucht.

Das vollständige Token wird **genau einmal** bei der Erzeugung zurückgegeben und
danach nirgends mehr — weder in der API noch im Log. In Logs erscheint
höchstens der `prefix`.

## Integration in die Auth-Kette

`require_permission()` in `core/security.py` bekommt einen dritten Zweig, vor
den bestehenden Cookie- und Basic-Prüfungen:

1. `Authorization: Bearer rdb_<prefix>_<secret>` → Key über `prefix` laden,
   Hash vergleichen, `revoked_at`/`expires_at` prüfen → `User` + Key.
2. Session-Cookie (unverändert).
3. HTTP Basic (unverändert).

Effektive Rechte eines Key-Requests: `user.effective_permissions ∩ scopes`
(bei `scopes IS NULL`: die Rechte des Nutzers). **Der Super-Admin-Bypass aus
`User.has_permission()` greift bei Key-Auth nicht** — sonst wäre ein Key eines
Admins durch `scopes` nicht einschränkbar, und genau das ist der Zweck von
`scopes`. Das ist der einzige Punkt, an dem sich Key-Auth vom bisherigen
Verhalten unterscheidet, und muss beim Umbau explizit getestet werden.

Fehlerfälle: kein/ungültiges Token → `401` mit `WWW-Authenticate: Bearer`
(die Stelle, an die später die `resource_metadata`-Angabe für OAuth gehört);
gültiges Token ohne die nötige Capability → `403`.

`last_used_at` wird **gedrosselt** geschrieben (höchstens einmal pro Minute pro
Key), damit nicht jeder Tool-Call einen DB-Write auslöst.

## Key-Verwaltung

Neuer Router `api/v1/endpoints/api_keys.py` unter `/api/v1/api-keys`:

| Methode | Pfad | Wirkung |
|---|---|---|
| `GET` | `/api-keys` | eigene Keys (Metadaten, nie das Token) |
| `POST` | `/api-keys` | Key anlegen → Antwort enthält das Token **einmalig** |
| `DELETE` | `/api-keys/{id}` | widerrufen (setzt `revoked_at`) |

Jeder eingeloggte Nutzer verwaltet seine eigenen Keys — dafür braucht es keine
neue Capability. Fremde Keys sehen und widerrufen darf nur, wer `user.manage`
hat (Admin-Bereich). Ein Key-Request darf die Key-Verwaltung **nicht** bedienen
(kein Selbst-Eskalationspfad): diese Endpunkte verlangen Cookie oder Basic.

Frontend: neue Sektion in der Benutzerverwaltung (`features/admin/`) mit
Anlege-Dialog, einmaliger Token-Anzeige samt Kopier-Button und Warnhinweis,
Liste mit `name`, `prefix`, `last_used_at`, `expires_at` und Widerruf-Aktion.
Nach den Backend-Änderungen `make gen-api` laufen lassen.

## MCP-Server

- **Bibliothek**: offizielles Python-SDK `mcp` (aktuell `2.2.0`, Python ≥ 3.10,
  Backend läuft auf 3.13), exakt gepinnt in `requirements.txt` wie alle anderen
  Abhängigkeiten. Es deckt Streamable HTTP ab; die konkrete ASGI-Mount-API ist
  bei der Umsetzung gegen die v2-Doku zu prüfen (v1-Beispiele aus dem Netz
  passen nicht mehr).
- **Ort**: `apps/backend/dashboard_backend/mcp/` — `server.py` (Server-Instanz
  und Mount), `tools/` (ein Modul je fachlichem Bereich).
- **Mount**: als ASGI-App unter `/mcp` in `main.py`, neben
  `app.include_router(api_router, prefix="/api/v1")`.
- **Zustand**: stateless betreiben, solange möglich — das Backend läuft
  potenziell mit mehreren Uvicorn-Workern, und eine im Prozess gehaltene
  Session würde bei Lastverteilung brechen.
- **Kontext**: jeder Tool-Aufruf löst den `User` aus dem Bearer-Token des
  Requests auf und prüft die Capability, bevor er die CRUD-Schicht ruft. Es
  gibt keinen Service-Account und keinen Fallback auf einen „System"-Nutzer.

### Tool-Katalog (erste Ausbaustufe)

| Tool | Wirkung | benötigte Capability |
|---|---|---|
| `list_projects` | Projekte suchen/filtern (Text, Projektgruppe, Phase) | — (eingeloggt) |
| `get_project` | Projektdetail inkl. BVWP-Daten und Unterprojekten | — |
| `get_project_progress` | Planungsstand inkl. Beobachtungen und Prognose | — |
| `list_project_finves` | Finanzierungsvereinbarungen und Budgets eines Projekts | — |
| `get_project_texts` | Projekttexte nach Typ | — |
| `list_todos` | Aufgaben, gefiltert | — |
| `update_project` | Projektfelder ändern | `project.edit` |
| `add_progress_observation` | Planungsstand-Beobachtung ergänzen | `progress.edit` |
| `upsert_project_text` | Projekttext anlegen/ändern | `projecttext.edit` |
| `create_todo` | Aufgabe anlegen | `todo.create` |
| `update_todo` | Aufgabe ändern | `todo.edit` |

Bewusst schmal gehalten: ein Tool je Absicht, keine generischen
„führe-beliebige-Abfrage-aus"-Tools. Ausgaben sind kompakt zu halten (Listen
paginiert, keine Geometrien im Volltext), weil jede Antwort im Kontextfenster
des Clients landet.

## Konfiguration & Deployment

- Neue `Settings`-Felder (`core/config.py`): `mcp_enabled: bool = True`.
  Optionale Felder brauchen keinen conftest-Eintrag — **würde ein Pflichtfeld
  dazukommen, muss es in `apps/backend/tests/conftest.py` einen
  `os.environ.setdefault(...)` bekommen**, sonst bricht der CI-Test-Gate auf
  einem sauberen Checkout ohne `.env`.
- `apps/frontend/nginx.conf`: `location /mcp/` analog zu `/api/`, zusätzlich
  `proxy_buffering off;` und ein erhöhtes `proxy_read_timeout` — Streamable HTTP
  hält langlebige Verbindungen, die nginx sonst puffert oder abschneidet.
- Kein neuer Compose-Service, keine Änderung an den GHCR-Images außer der neuen
  Python-Abhängigkeit.
- Neue Konfiguration in `.env.prod.example` dokumentieren.
- `CHANGELOG.md` und `docs/production_setup.md` nachziehen (nginx-Regel ist
  deploy-relevant).

Client-seitig (Claude Code, `.mcp.json`):

```json
{
  "mcpServers": {
    "raildashboard": {
      "type": "http",
      "url": "https://<host>/mcp",
      "headers": { "Authorization": "Bearer rdb_..." }
    }
  }
}
```

## Sicherheit

- Token nur über HTTPS; der Key steht beim Client im Klartext in einer
  Config-Datei — deshalb sind Ablaufdatum und Widerruf Pflichtfunktionen und
  kein Nice-to-have.
- Schreib-Tools sind doppelt gegated: Capability des Nutzers **und** `scopes`
  des Keys. Empfehlung in der UI: für Agenten-Zugriff standardmäßig einen
  Read-only-Key anlegen.
- Kein Token, kein Prefix-plus-Secret und keine Passwörter in Logs oder
  Fehlermeldungen.
- Schreibende Tools schreiben wie die REST-Endpunkte in den `change_log`, damit
  Agenten-Änderungen nachvollziehbar und über die bestehende Revert-Funktion
  rücknehmbar bleiben.
- Ein Key-Request kann keine Keys verwalten (siehe oben).

## Tests

- `security.py`: gültiger Key, unbekannter Prefix, falsches Secret,
  widerrufener Key, abgelaufener Key, `scopes`-Schnittmenge, kein
  Admin-Bypass bei Key-Auth.
- Key-Endpunkte: Token erscheint genau einmal; fremde Keys nur mit
  `user.manage`; Key-Auth wird an der Key-Verwaltung abgewiesen.
- MCP-Tools: je ein Lese- und ein Schreib-Tool end-to-end mit Key;
  Schreib-Tool ohne Capability → Fehler; Schreib-Tool mit Read-only-Key →
  Fehler.
- Bestehende Auth-Tests müssen unverändert grün bleiben (Cookie und Basic
  dürfen sich nicht ändern).

## Akzeptanzkriterien

**Phase 1 — API-Keys als Auth-Weg**

- [ ] Tabelle `api_keys` + Migration; `make migrate` läuft sauber durch.
- [ ] `Authorization: Bearer …` authentifiziert gegen die gesamte REST-API.
- [ ] `scopes` schränken die Rechte ein, auch bei einem Admin-Nutzer.
- [ ] Widerrufener oder abgelaufener Key → `401`.
- [ ] Key-Endpunkte inkl. einmaliger Token-Anzeige; Key-Auth dort abgewiesen.
- [ ] Admin-UI zum Anlegen, Ansehen und Widerrufen; `make gen-api` gelaufen.
- [ ] Cookie- und Basic-Auth verhalten sich unverändert.

**Phase 2 — MCP-Server**

- [ ] `/mcp` antwortet über Streamable HTTP und listet die Tools aus dem
      Katalog.
- [ ] Claude Code verbindet sich mit einem Key aus `.mcp.json` und ruft
      erfolgreich ein Lese-Tool auf.
- [ ] Schreib-Tools respektieren Capability *und* Key-Scopes.
- [ ] Schreibende Tools erzeugen `change_log`-Einträge.
- [ ] nginx-Regel für `/mcp/` steht; `docs/production_setup.md` und
      `CHANGELOG.md` nachgezogen.
- [ ] `mcp` exakt gepinnt; Backend-Tests grün.

## Offene Punkte

- Ablaufzeit-Voreinstellung für neue Keys (kein Ablauf vs. 90 Tage) — beim
  Umsetzen von Phase 1 mit dem Nutzer klären.
- Ob `scopes` als freie Capability-Liste oder als zwei Presets
  („read-only" / „wie mein Nutzer") in der UI angeboten werden.
- Genauer Zuschnitt der Filter von `list_projects` — sinnvollerweise an dem
  ausrichten, was die Projektliste im Frontend heute kann.

## Umsetzung

Zwei Issues, in dieser Reihenfolge:

1. **API-Keys als Auth-Weg** (`area:auth`, `type:backend`) — Phase 1 oben.
   Eigenständig nützlich, auch ohne MCP.
2. **MCP-Server** (`area:auth`, `type:integration`) — Phase 2 oben.
   `Depends on:` Issue 1.
