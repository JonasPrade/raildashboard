# Review-Checkliste: Release v0.0.4 — Direction F · Bahnhofshalle Tag

_Stand: 2026-04-26_

Vor dem Tag von `v0.0.4` einmal komplett durchklicken. Alle Punkte sollen ohne Fehler funktionieren und das neue Brand-Idiom (Anthrazit-Ink, Gold-Akzent, Preußenblau-Gewicht, scharfe Kanten, Archivo-Narrow-Headlines, IBM Plex Sans/Mono) zeigen.

## Was du prüfen musst

### Header & globale Navigation
- [ ] Header zeigt **Signet** (Anthrazit-Quadrat mit goldenem Innenquadrat) und **Wordmark** „Schienendashboard" links.
- [ ] Header-Hintergrund weiß (`--bg`), 2px-Anthrazit-Linie oben, Hairline-Linie unten.
- [ ] Nav-Links sind **uppercase, Mono-Font**, mit „▸"-Prefix; aktiver Link bekommt eine **goldene** Unterstreichung.
- [ ] Klick auf das Wordmark führt zurück zu `/`.
- [ ] „Anmelden"-Button (Preußenblau) öffnet Login-Modal; Hover wechselt auf Anthrazit mit Goldschrift.
- [ ] Nach Login: „Abmelden"-Button (Ghost-Variant) ist klar als Anthrazit auf Weiß lesbar — **kein** Kontrast-Problem.
- [ ] Als editor/admin: „▸ Admin"-Link mit goldenem Badge zeigt die Anzahl offener FinVe/VIB-Zuordnungen.
- [ ] Burger-Menü (Fenster < ~1600px) öffnet Drawer mit denselben Links und „Abmelden"/„Anmelden".

### Startseite (`/`)
- [ ] Toggle Karte/Liste über `?view=map` und `?view=list` (Tab-Style mit Goldunterstreichung aktiv).
- [ ] Suchfeld debounced; `?search=` bleibt in URL.
- [ ] Gruppenfilter (Drawer) öffnet sich; Auswahl persistiert in `?group=`.
- [ ] Toggle „Nur übergeordnete Projekte" funktioniert.
- [ ] Karte: Klick auf eine Geometrie zeigt Projektnummer + Beschreibung; Linienstärke/Punktgröße einstellbar.
- [ ] Liste: Treffer werden gefiltert; Klick navigiert in Projektdetail.

### Projektdetail (`/projects/:id`)
- [ ] Headlines in Archivo Narrow Großbuchstaben; `<em>` rendert in Gold.
- [ ] ChronicleCard hat 1-px-Hairline-Border, **keine** abgerundeten Ecken, **kein** Schatten.
- [ ] Inhaltsverzeichnis links ausklappbar.
- [ ] Bearbeitungsformular nur sichtbar als editor/admin; Speichern legt ChangeLog-Eintrag an.
- [ ] Versionshistorie nur sichtbar mit Login; „Zurücksetzen"-Button pro Eintrag funktioniert.
- [ ] BVWP-Bewertungs-Sektion sichtbar wenn Daten vorhanden, sonst ausgeblendet.
- [ ] VIB-Sektion: Klick auf Edit-Icon öffnet Drawer; Speichern persistiert; Markdown-Rendering der Prosa-Felder.
- [ ] FinVe-Bereich: SV-FinVes als kompakter Tag.
- [ ] Geometrie verwalten (editor/admin): Modal öffnet, Route-Calculator mit Start/Via/End funktioniert, Confirm setzt geojson_representation.

### Haushalt (`/finves`)
- [ ] Liste aller FinVes mit Kartenansicht, Suche, Typ-Filter.
- [ ] Budget-Diagramme (Bar/Line/Detailtabelle) klappen aus.
- [ ] Verknüpfte Projekt-Mini-Karten verlinken in das jeweilige Projekt.

### Admin (`/admin`)
- [ ] Übersicht zeigt Kacheln für: Offene Zuordnungen, Haushalts-Import, VIB-Import, Neues Projekt, Benutzerverwaltung.
- [ ] `/admin/unassigned`: zwei Sektionen (FinVe + VIB), Inline-MultiSelect für Projektzuweisung; Header-Badge sinkt nach Zuweisung.
- [ ] „Neues Projekt anlegen"-Button auf `/admin/unassigned` und im Admin-Index führt zu `/admin/projects/new`.

### Wizard `/admin/projects/new` (5 Schritte)
- [ ] Schritt 1 (Stammdaten): Pflichtfelder validiert; weiter blockiert bei Fehler.
- [ ] Schritt 2 (Geometrie): Inline-Geometry-Calculator funktioniert; überspringbar.
- [ ] Schritt 3 (Projekteigenschaften): nutzt `ProjectEditFields`; überspringbar.
- [ ] Schritt 4 (FinVes): MultiSelect verlinkt FinVes; überspringbar.
- [ ] Schritt 5 (VIB): VIB-Einträge zuordnen; Abschluss legt Projekt an und navigiert zur Detailseite.

### Haushalts-Import (`/admin/haushalt-import`)
- [ ] Upload-Flow startet Celery-Task; Polling zeigt Fortschritt.
- [ ] Review-Tabelle zeigt neu/geändert/unmatched korrekt.
- [ ] Sammel-FinVe-Sektion (Phase 2) erscheint mit per-Projekt-Unterzeilen + ✦-Vorschlägen.
- [ ] Confirm synct FinVe ↔ Projekt bidirektional; SV-FinVes nur fürs aktuelle Importjahr.
- [ ] Anleitung unter `/admin/haushalt-import/guide` erreichbar; F-Idiom sichtbar.

### VIB-Import (`/admin/vib-import`)
- [ ] Upload + OCR-Verarbeitung (Mistral oder pymupdf-Fallback) funktionieren.
- [ ] `VibStructurePreviewPage` zeigt Markdown-Tabellen, Quality-Chips, Sub-Section-Badges; **kein** ungenutzter Quality-Color-Indikator.
- [ ] Review-Seite: per-Eintrag „KI extrahieren"; m:n Projektzuordnung.

### Karte (`/map` bzw. `?view=map`)
- [ ] Map-Controls (Layer-Toggle, Stilauswahl) im F-Idiom: scharfe Kanten, Mono-Labels.
- [ ] Loading-Indikator beim Initialladen sichtbar.

### Komponenten-Visual (Spotchecks)
- [ ] Mindestens eine `ChronicleCard tone="board"` (z. B. in `<KpiCard>`-Kontext) wechselt auf Tafel-dunkel.
- [ ] `<MiniBoard>` (sofern auf einer Seite eingebaut) zeigt LED-Header, Mono-Spalten, Status-Punkte (go/delay/info/wait).
- [ ] Keine alten Brand-Referenzen mehr sichtbar: nirgends Schienengrün-Petrol, nirgends Noto-Serif, keine abgerundeten Mantine-Default-Ecken auf Karten/Buttons.
- [ ] Favicon und Theme-Color (`#0d1013`) korrekt im Browser-Tab.

### Smoke-Tests (Backend)
- [ ] `cd apps/backend && .venv/bin/python -m pytest tests/api -q` läuft durch (Routing-DB-Tests benötigen Live-DB und dürfen weiter erroren — kein Release-Blocker, solange `tests/api` grün ist).
- [ ] `make migrate` zeigt „No new migrations".

### Frontend-Build
- [ ] `cd apps/frontend && npx tsc --noEmit` ohne Fehler.
- [ ] `cd apps/frontend && npx vitest run` alle Tests grün.
- [ ] `npm --prefix apps/frontend run build` erstellt `dist/` ohne Warnings.

### Letzter Schritt
- [ ] Tag `v0.0.4` setzen mit Release-Notes, die seit `v0.0.3` die folgenden Bereiche zusammenfassen: Routing/GraphHopper, Admin-Wizard, Unassigned-Page, VIB-Edit-Drawer, FinVe-Übersicht, Direction-F-Rebrand.
