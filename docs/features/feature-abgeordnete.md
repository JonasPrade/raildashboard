# Feature: Wahlkreise und Abgeordnete auf Projekten

## Ziel

Jedes Projekt beantwortet die Frage, die vor jedem politischen Gespräch dieselbe ist:
**Was verbindet diese Abgeordnete konkret mit diesem Vorhaben?** Ein Projekt im eigenen
Wahlkreis ist das stärkste Argument, weil es nicht mehr abstrakt ist.

Dafür werden die Projektgeometrien mit den 299 Bundestagswahlkreisen verschnitten und
die zuständigen Abgeordneten an die Wahlkreise gehängt. Zielgruppe ist nicht die
Öffentlichkeit, sondern die eigene Lobbyarbeit — mit zwei Arbeitsrichtungen:

- **Vor einem Termin** steht die Person fest, die Projekte werden gesucht.
- **Vor einer Kampagne** steht das Projekt fest, die Ansprechpartner werden gesucht.

## Kontext — was der Prototyp gezeigt hat

Vorlage ist der Prototyp `ideen/ueberlastete-strecken-bundestag/` in
`JonasPrade/scratchbook` (privat), der dieselbe Verschneidung auf den 26 dauerhaft
überlasteten Schienenwegen der DB InfraGO gemacht hat. Ergebnis dort: 26 Strecken
berühren 83 Wahlkreise mit 166 Abgeordneten, davon **35 im Verkehrs- oder
Haushaltsausschuss**, einschließlich beider Vorsitzenden. Der Engpass vor der Haustür
ist keine Ausnahme, er trifft die Zuständigen selbst.

Vier Entscheidungen des Prototyps werden hier übernommen, weil sie sich erst im
Gebrauch gezeigt haben:

1. **Gewichten statt binär zuordnen.** Streckenkilometer je Wahlkreis fallen bei der
   Verschneidung ohnehin ab. 51 km in einem Wahlkreis und 3 km in einem anderen binär
   gleich zu behandeln ist in einem Gespräch nicht zu halten.
2. **Zwei Grade von Zuständigkeit, sichtbar getrennt.** Direktmandat ist das eine;
   „über die Landesliste eingezogen, im Wahlkreis angetreten" das andere und schwächere.
   Einen gepflegten *Betreuungs*wahlkreis kennt die Datenquelle nicht — die Kandidatur
   ist der beste verfügbare Ersatz und muss als solche ausgewiesen bleiben.
3. **„Kein Direktmandat besetzt" ist eine Aussage, keine Lücke.** Seit der
   Wahlrechtsreform trifft das 27 der 299 Wahlkreise. Wo zusätzlich niemand über die
   Liste angetreten ist, gibt es schlicht keinen naheliegenden Ansprechpartner.
4. **Der Einstieg über den Personennamen ist der häufigste.** Gedacht waren zwei
   Richtungen (Projekt → Wahlkreis → Person), gebraucht wird vor allem die dritte:
   Name eintippen, Ausschussfilter setzen, Arbeitsliste lesen.

**Was hier anders ist als im Prototyp:** Der Prototyp musste sich Geometrien aus Ketten
von Betriebsstellen zusammensetzen und dazwischen interpolieren. Im raildashboard ist
das erledigt — Projekte haben `geojson_representation`, und PostGIS ist da. Die
Verschneidung ist **eine Datenbankoperation**, keine Rekonstruktion, und damit
belastbarer. Dafür sind es nicht 26 feste Objekte, sondern der laufend geänderte
Gesamtbestand: die Zuordnung muss **gepflegt** werden und darf nicht bei jedem
Seitenaufruf neu gerechnet werden.

## Scope

**In scope**

1. Datenmodell für Wahlperiode, Wahlkreis (Geometrie), Person, Mandat, Ausschuss und
   Ausschussmitgliedschaft + Migration.
2. Idempotenter, wiederholbarer Import: Wahlkreisgeometrien (einmalig je Wahl) und
   Abgeordnetendaten (laufend) aus abgeordnetenwatch v2.
3. Materialisierte Verknüpfung `project_to_constituency` mit Kilometern und Anteil,
   gepflegt bei jeder Geometrieänderung, plus vollständiger Neuaufbau.
4. Drei Oberflächen-Einstiege: im Projekt, über die Person, über den Wahlkreis (Karte).
5. Abrufstand je Import, in der Oberfläche sichtbar.

**Nicht in scope**

- Die überlasteten Schienenwege selbst — eigene Idee, eigene Datenquelle.
- Kontaktdaten, Anschreiben, Mailversand aus dem Dashboard heraus.
- Landtage und frühere Wahlperioden. Das Datenmodell verbaut sie aber nicht
  (`parliament_period` als eigene Tabelle, alles Personenbezogene hängt am Mandat).
- Automatische Zeitsteuerung des Imports (kein Celery Beat) — der Import wird von Hand
  angestoßen, siehe *Aktualisierung*.

## Beantwortete Fragen (die Entscheidungen im Einzelnen)

### Welche Geometrie gilt bei Teilprojekten?

**Jedes Projekt wird mit seiner eigenen `geojson_representation` verschnitten** —
Blattprojekte mit ihrer eigenen, Überprojekte mit der aus den Teilprojekten
aggregierten (bzw. mit der selbst gepflegten, wenn `geojson_from_subprojects = false`).

Begründung: Die aggregierte Geometrie eines Überprojekts *ist* die Vereinigung seiner
Kinder — die Projektdetailseite eines Überprojekts braucht eine eigene, vollständige
Antwort, und die Kinder brauchen ihre. Die Zeilen werden immer **je Projekt** gelesen
und nie über den Baum summiert, es entsteht also keine Doppelzählung. Überlappende
Linien innerhalb einer aggregierten `FeatureCollection` werden vor der Messung per
`ST_UnaryUnion` zusammengefasst, damit ein doppelt hinterlegter Abschnitt nicht doppelt
zählt.

Folge: Ändert sich ein Teilprojekt, ändert sich die Geometrie aller Vorfahren — die
Neuberechnung läuft deshalb an derselben Stelle wie die Geometrie-Kaskade und für
dieselbe Projektmenge (Projekt + Vorfahrenkette).

### Was passiert mit Projekten ohne Geometrie?

Sie fallen aus dem Feature heraus — es gibt nichts zu verschneiden. **Das wird
ausgewiesen, nicht verschwiegen:**

- Auf der Projektdetailseite steht im Block statt einer leeren Liste: „Für dieses
  Projekt ist keine Geometrie hinterlegt — eine Wahlkreiszuordnung ist deshalb nicht
  möglich." Für Nutzer mit `project.edit` mit Link auf die Geometrieverwaltung.
- `GET /api/v1/parliament/status` liefert die Abdeckung als Kennzahl
  (`projects_total`, `projects_with_geometry`, `projects_linked`,
  `projects_without_geometry`), sichtbar auf der Abgeordnetenseite und im Adminbereich.

Wie viele es sind, ist eine Frage an den Datenbestand und keine Konstante — die Zahl
kommt aus der Kennzahl, nicht aus diesem Dokument. Sie ist Teil der Test-Checkliste.

### Punkt- gegen Liniengeometrien

Die Gewichtung trägt beide Fälle, weil sie zwei Größen führt und die Art der
Überlappung mitschreibt (`overlap_kind`):

| Fall | `length_km` | `share` | `overlap_kind` |
|---|---|---|---|
| Linienanteil im Wahlkreis | Länge der `ST_Intersection` auf `geography`, in km | Anteil an der Gesamtlänge des Projekts | `line` |
| nur Punkte (Bahnhofsprojekt) | `0` | Anteil der Projektpunkte in diesem Wahlkreis | `point` |
| gemischt | Linienlänge (kann 0 sein) | wie Linie | `line`, sonst `point` |

Ein Bahnhofsprojekt mit genau einem Punkt ergibt also eine Zeile mit
`length_km = 0`, `share = 1.0`, `overlap_kind = point`. Die Oberfläche zeigt dort
„Lage im Wahlkreis" statt einer Kilometerangabe; sortiert wird nach
`length_km DESC NULLS LAST`, dann nach Wahlkreisnummer, damit Punktprojekte nicht
zwischen Linienprojekten verschwinden. Flächen (Polygone) werden wie Linien behandelt,
gemessen wird ihr Umriss — im Bestand kommen sie praktisch nicht vor, brechen aber
nichts.

### Wie oft wird der Abgeordnetenstand aktualisiert, und wer stößt das an?

Die beiden Datenteile altern unterschiedlich schnell, deshalb zwei getrennte Läufe:

- **Wahlkreisgeometrien** — einmal je Bundestagswahl. Lauf per Skript
  (`scripts/import_constituencies.py`), nicht über die Oberfläche.
- **Abgeordnetendaten** — Nachrücker und Ausschussumbesetzungen verschieben die
  Zuordnung laufend, ohne dass an den Geometrien etwas falsch würde. Anstoß **von Hand
  im Adminbereich** („Abgeordnetenstand aktualisieren", Recht `parliament.import`),
  ausgeführt als Celery-Task. Empfehlung: monatlich, mindestens aber vor einer
  Kampagne. Der Abrufstand steht in der Oberfläche, damit man sieht, wann es zuletzt
  passiert ist; ist er älter als 60 Tage, wird er als veraltet markiert.

Ein erneuter Lauf ist billig: rund 15 API-Abrufe (Wahlperiode, 299 Wahlkreise, 630
Mandate, zwei Ausschüsse mit Mitgliedslisten, Seitengröße 100) und ein Upsert über
wenige tausend Zeilen. Er berührt die **Geometrien nicht** und damit auch nicht
`project_to_constituency` — die teure Verschneidung läuft dabei gerade nicht.

### Laufzeit: was kostet die Neuberechnung?

- **Je Projekt** (der Normalfall, bei jeder Geometrieänderung): eine Query, die die
  Projektgeometrie gegen die 299 Wahlkreise hält. Der GiST-Index auf
  `constituency.geom` reduziert das auf die wenigen Kandidaten, die die Bounding-Box
  schneiden. **Gemessen** gegen die echten 299 Wahlkreisgeometrien (PostGIS 3.4,
  Linienprojekt Hamburg–Berlin über 10 Wahlkreise): **7 ms**. Bei einem Teilprojekt
  kommt die Vorfahrenkette dazu, also typisch ein bis drei weitere Projekte.
- **Vollständiger Neuaufbau** (`POST /parliament/recompute-links`, Celery-Task): einmal
  über alle Projekte mit Geometrie. Hochgerechnet aus der Messung liegt der Bestand
  (Größenordnung 1.000 Projekte) bei **unter 10 Sekunden**. Gebraucht wird er nur nach
  einem Geometrie-Import oder einer neuen Wahlperiode.
- Der Geometrie-Import selbst (299 Wahlkreise aus GeoJSON) lief in **1,7 s**.

Die inkrementelle Pflege reicht damit im laufenden Betrieb; der Neuaufbau ist die
Reparatur, nicht der Normalfall. Die Hochrechnung ist gegen den echten Bestand zu
bestätigen — Eintrag in `docs/manual-tests-backlog.md`.

### Sichtbarkeit

**Lesen ist öffentlich**, wie alle anderen `GET`-Endpunkte des Dashboards (der
`AuthRouter` gated nur Nicht-GET-Methoden). Die Zuordnung ist öffentliche Information
über Amtsträger aus einer CC0-Quelle; im bestehenden Berechtigungsmodell gibt es keinen
Grund, sie hinter `editor` zu verschieben. **Geschrieben** wird nur über den Import, und
der bekommt ein eigenes Recht `parliament.import` (Gruppe „Inhalte") — nicht wegen der
Daten, sondern weil ein Importlauf externe Abrufe auslöst und Bestandsdaten
überschreibt.

Das Recht wird **keiner System-Rolle vorgeseedet**: `admin` hat es über den
Superadmin-Bypass ohnehin, und der `editor`-Seed bildet bewusst den historischen
Rechtebestand ab (`tests/api/test_roles_seed.py` prüft ihn exakt) — dieselbe
Entscheidung wie zuvor bei `guides.edit`. Wer den Import einer anderen Rolle geben
will, hakt ihn unter `/admin/roles` an.

## Datenquellen

**Wahlkreisgeometrien** der Bundeswahlleiterin (Wahl 2025, 299 Wahlkreise). Fällt die
Originalquelle aus, gibt es einen offenen Spiegel:
`github.com/ZeitOnline/bundestagswahl-historische-wahlkreis-daten`,
`shapes_2025/wkr2025.geojson`. Herkunftshinweis **© GeoBasis-DE / BKG** wird als
`geometry_source` je Wahlkreis mitgeführt und in der Oberfläche am Kartenlayer
ausgewiesen.

**Abgeordnete** über die abgeordnetenwatch-API v2 (CC0),
`https://www.abgeordnetenwatch.de/api/v2`. Vier Abrufe, alle mit
`range_start`/`range_end` durchzublättern (Seitengröße 100):

| Zweck | Aufruf |
|---|---|
| Wahlperiode | `/parliament-periods?type=legislature&parliament=5&sort_by=id&sort_direction=desc` — aktuell ID 161, „Bundestag 2025 – 2029" |
| Wahlkreise | `/constituencies?parliament_period=<id>` — `number` (1–299) und `name` |
| Mandate | `/candidacies-mandates?parliament_period=<id>&type=mandate` — 630 Stück, mit `politician`, `fraction_membership`, `electoral_data.mandate_won`, `electoral_data.constituency` |
| Ausschüsse | `/committees?field_legislature=<id>` für „Verkehrsausschuss" und „Haushaltsausschuss", dann `/committee-memberships?committee=<id>` mit `committee_role` |

Drei Fallstricke aus dem Prototyp, die im Importer explizit behandelt werden:

- Die **Wahlkreisnummer steht nur im Label** der `constituency`
  (`"14 - Rostock – Landkreis Rostock II (Bundestag …)"`) — vor dem ersten `" - "`
  abschneiden.
- **Fraktionslabels enthalten weiche Trennstriche** (`­`), die jeden
  Namensvergleich sprengen — beim Import entfernen.
- Maßgeblich für „Direktmandat" ist **ausschließlich** `mandate_won == "constituency"`.
  „nachgerückt" (`moved_up`) zählt nicht als Direktmandat. Bei mehreren Ausschussrollen
  gewinnt die stärkste: Vorsitz > Stellv. Vorsitz > Obfrau/Obmann > Sprecher/in >
  Mitglied > Stellv. Mitglied.

## Datenmodell

Neue Tabellen unter `models/parliament/`, die Assoziation wie üblich unter
`models/associations/`. Alles Personenbezogene hängt am **Mandat**, nicht an der
Person — so kommen weitere Wahlperioden (und später Landtage) dazu, ohne das Modell zu
brechen.

| Tabelle | Inhalt |
|---|---|
| `parliament_period` | Wahlperiode: `external_id` (abgeordnetenwatch, unique), `label`, `parliament_label`, `start_date`, `end_date`, `is_current` |
| `constituency` | Wahlkreis: `parliament_period_id`, `number` (1–299), `name`, `state` (Bundesland), `election_year`, `external_id`, `geom` (`MULTIPOLYGON`, SRID 4326, GiST-Index), `geometry_source`. Unique `(parliament_period_id, number)` |
| `politician` | Person: `external_id` (unique), `first_name`, `last_name`, `label`, `party_label`, `abgeordnetenwatch_url` |
| `mandate` | Mandat: `external_id` (unique), `politician_id`, `parliament_period_id`, `constituency_id` (nullable), `mandate_type` (`constituency` / `list` / `moved_up`), `is_direct_mandate` (bool), `fraction_label`, `info` |
| `committee` | Ausschuss: `external_id` (unique), `parliament_period_id`, `key` (`verkehr` / `haushalt`), `label` |
| `committee_membership` | `mandate_id`, `committee_id`, `role` (API-Wert), `role_label` (deutsch), `role_rank` (int, kleiner = stärker). Unique `(mandate_id, committee_id)` |
| `project_to_constituency` | `project_id`, `constituency_id`, `length_km` (Float), `share` (Float 0–1), `overlap_kind` (`line` / `point`), `computed_at`. PK `(project_id, constituency_id)`, Index auf `constituency_id` |
| `parliament_import_run` | Abrufstand: `started_at`, `finished_at`, `kind` (`politicians` / `constituencies` / `links`), `parliament_period_id`, `status` (`running` / `success` / `error`), `stats` (JSON: Mandate, Wahlkreise, Direktmandate, Ausschussmitglieder …), `error`, `triggered_by_user_id` |

Warum Person **und** Mandat getrennt: eine Person kann über mehrere Wahlperioden
mehrere Mandate haben, und der Nachrücker-Fall bindet ein neues Mandat an dieselbe
Person. Fraktion, Wahlkreisbezug und Ausschussrolle sind Eigenschaften des Mandats.

Warum `is_direct_mandate` **zusätzlich** zu `mandate_type`: die Unterscheidung ist die
tragende Aussage der Oberfläche und soll nicht in jeder Query aus einem String-Vergleich
neu abgeleitet werden. Sie wird beim Import genau einmal gesetzt
(`mandate_won == "constituency"`).

`Project` bekommt keine neue Spalte — die Verknüpfung lebt vollständig in
`project_to_constituency`.

## Backend

### Import

`services/parliament_import.py` (reine Abruf- und Upsert-Logik, ohne FastAPI) plus zwei
Einstiege:

- **Celery-Task** `import_parliament_data` (`tasks/parliament.py`) — von der Oberfläche
  angestoßen, schreibt `parliament_import_run`.
- **Skript** `scripts/import_constituencies.py` — liest die GeoJSON-Datei der
  Wahlkreisgeometrien (Pfad als Argument) und schreibt `constituency`.

Der Import ist **idempotent**: Upsert über `external_id` bzw.
`(parliament_period_id, number)`, keine Löschung von Projekten oder Geometrien. Mandate,
die es in der Quelle nicht mehr gibt, werden entfernt (Nachrücker ersetzen Vorgänger),
Personen bleiben stehen.

### Verschneidung

`services/constituency_matching.py`:

```
compute_links_for_project(db, project_id) -> int   # Zeilen geschrieben
recompute_links_for_projects(db, ids)              # Projekt + Vorfahren
recompute_all_links(db) -> Stats                   # vollständiger Neuaufbau
```

Kern ist eine SQL-Anweisung, die die `geojson_representation` des Projekts über
`ST_GeomFromGeoJSON` je Feature einliest, Linien und Punkte trennt, die Linien per
`ST_UnaryUnion` zusammenfasst und gegen `constituency.geom` schneidet:

```sql
ST_Length(ST_Intersection(lines, c.geom)::geography) / 1000.0  AS length_km
```

`::geography` gibt echte Meter auf dem Ellipsoid, ohne Umprojektion. Der GiST-Index auf
`constituency.geom` trägt den `&&`-Vorfilter.

**Aufgehängt** wird die Neuberechnung an derselben Stelle, an der heute die
Geometrie-Kaskade läuft — `crud/projects/projects.py`, in `recompute_geojson_for_parent`
und in `update_project`, damit sie auch die Aggregation aus Teilprojekten mitnimmt.

> **Befund beim Lesen des Codes:** `Project.centroid` wird heute **nirgends** gepflegt —
> die Spalte wird nur beim Alt-Import (`scripts/import_old_db/`) geschrieben und danach
> nur noch gelesen. Der Auftrag ging davon aus, dass `geojson_representation` und
> `centroid` gemeinsam nachgezogen werden; tatsächlich existiert nur die
> Geojson-Kaskade. Die Verschneidung hängt sich deshalb **an die Geojson-Kaskade** —
> das ist die Stelle, die wirklich läuft. Der ungepflegte `centroid` ist ein eigener
> Befund und gehört in ein eigenes Issue, nicht in dieses Feature.

### Endpunkte

Neuer Router `api/v1/endpoints/parliament.py`, Prefix `/api/v1/parliament`, plus eine
Route am bestehenden Projekt-Router. Alle `GET` öffentlich, alle Schreiboperationen mit
`parliament.import`.

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/projects/{id}/constituencies` | Wahlkreise des Projekts, absteigend nach km, je Wahlkreis die Abgeordneten (Direktmandat zuerst) |
| `GET` | `/parliament/politicians` | Personenliste; Filter `query` (Name), `committee` (`verkehr`/`haushalt`), `fraction`; mit Projektanzahl |
| `GET` | `/parliament/politicians/{id}` | Person + Projekte im Wahlkreis, nach km sortiert |
| `GET` | `/parliament/constituencies` | Wahlkreisliste mit Projekt- und Abgeordnetenzahl |
| `GET` | `/parliament/constituencies/{id}` | Wahlkreis + Projekte + Abgeordnete |
| `GET` | `/parliament/constituencies/geojson` | Grenzen als Kartenlayer (vereinfacht, mit Herkunftshinweis) |
| `GET` | `/parliament/status` | Abrufstand, Wahlperiode, Kennzahlen, Abdeckung, Fraktionsliste für den Filter |
| `POST` | `/parliament/import` | Abgeordnetenstand aktualisieren (Celery, gibt `task_id` zurück) |
| `POST` | `/parliament/recompute-links` | Verschneidung vollständig neu (Celery) |

## Frontend

Komponenten unter `src/features/abgeordnete/`, Client über `make gen-api`.

1. **Im Projekt** (`ProjectDetail`) — Block „Wahlkreise und Abgeordnete", eigener
   Eintrag im Inhaltsverzeichnis. Wahlkreise absteigend nach Kilometern, je Wahlkreis
   die Abgeordneten: **Direktmandat zuerst und sichtbar abgesetzt** von „über Liste,
   hier angetreten". Ausschussmitglieder markiert, Rolle im Ausschuss dabei. „Kein
   Direktmandat besetzt" wird ausgeschrieben; ist auch niemand über die Liste
   angetreten, steht dort „kein naheliegender Ansprechpartner".
2. **Über die Person** — Seite `/abgeordnete` mit Namenssuche (umlaut-tolerant wie die
   bestehende Projektsuche) und Filtern auf Verkehrs-/Haushaltsausschuss und Fraktion.
   Zu jeder Person die Projekte in ihrem Wahlkreis, nach km sortiert. Das ist die
   Arbeitsliste vor einem Termin und erfahrungsgemäß der meistgenutzte Einstieg — sie
   bekommt deshalb einen Header-Eintrag.
3. **Über den Wahlkreis** — auf der bestehenden Karte ein zuschaltbarer Layer
   „Wahlkreise" (`MapControls`); Auswahl eines Wahlkreises öffnet ein Panel mit
   Projekten und Abgeordneten.

UI-Texte deutsch, Code und Commits englisch.

## Akzeptanzkriterien

- [ ] Migration legt alle acht Tabellen an; `constituency.geom` hat einen GiST-Index.
- [ ] Der Abgeordneten-Import ist idempotent: zwei Läufe hintereinander erzeugen
      dieselben Zeilenzahlen und keine Dubletten.
- [ ] Ein Mandat mit `mandate_won = "constituency"` erscheint als Direktmandat, eines
      mit `list` oder `moved_up` nicht.
- [ ] Fraktionslabels enthalten keine weichen Trennstriche mehr.
- [ ] Bei mehreren Ausschussrollen gewinnt die stärkste.
- [ ] Ein Linienprojekt über zwei Wahlkreise bekommt zwei Zeilen mit plausiblen
      Kilometern; die Summe der `share` liegt bei 1.
- [ ] Ein Punktprojekt (Bahnhof) bekommt genau eine Zeile mit `overlap_kind = point`
      und `length_km = 0`.
- [ ] Ändert sich die Geometrie eines Teilprojekts, sind danach die Zeilen des
      Teilprojekts **und** die des Überprojekts aktuell.
- [ ] Ein Projekt ohne Geometrie erzeugt keine Zeilen, und die Oberfläche sagt warum.
- [ ] `GET /projects/{id}/constituencies` ist ohne Login abrufbar; `POST
      /parliament/import` antwortet ohne Recht `parliament.import` mit 403.
- [ ] Die Abgeordnetenseite findet eine Person über einen Namensteil und lässt sich auf
      Verkehrs-/Haushaltsausschuss filtern.
- [ ] Der Wahlkreis-Layer lässt sich auf der Karte zuschalten; die Auswahl eines
      Wahlkreises zeigt Projekte und Abgeordnete.
- [ ] Der Abrufstand ist in der Oberfläche sichtbar und wird nach 60 Tagen als veraltet
      markiert.
- [ ] Backend-Tests grün, `tsc`/`eslint` sauber, `make gen-api` gelaufen.

## Technische Schritte

1. **Datenmodell + Import** — Modelle unter `models/parliament/`, Migration über
   `make migrate-create`, `services/parliament_import.py`, `tasks/parliament.py`,
   `scripts/import_constituencies.py`, Recht `parliament.import`, Endpunkte
   `/parliament/status` und `/parliament/import`, Tests.
2. **Verschneidung** — `models/associations/project_to_constituency.py`,
   `services/constituency_matching.py`, Aufhängung an der Geojson-Kaskade,
   `POST /parliament/recompute-links`, `GET /projects/{id}/constituencies`, Tests.
3. **Oberfläche im Projekt** — `ProjectConstituencySection`, Inhaltsverzeichnis-Eintrag,
   `make gen-api`.
4. **Oberfläche über die Person** — Seite `/abgeordnete`, Route, Header-Eintrag,
   Suche und Filter.
5. **Oberfläche über den Wahlkreis** — Kartenlayer + Auswahl-Panel.
6. **Dokumentation** — `docs/models.md`, `docs/roadmap.md`, READMEs,
   `DocumentationPage.tsx`, `CHANGELOG.md`.

## Offene Punkte

- **Wahlkreisgeometrien beschaffen** ist ein Vorgang außerhalb des Codes (Download der
  Bundeswahlleiterin bzw. des Spiegels). Ohne die Datei bleibt `constituency` leer und
  das Feature zeigt überall „keine Daten" — das ist der erwartete Zustand vor dem
  ersten Import, kein Fehler.
- **Laufzeit messen**: der vollständige Neuaufbau über den echten Bestand ist hier nicht
  messbar (keine Produktionsdaten in der Entwicklungsumgebung) → Eintrag in
  `docs/manual-tests-backlog.md`.
- **Betreuungswahlkreise** gibt es in der Quelle nicht. Sollte das jemals gepflegt
  werden, wäre es eine dritte Stufe der Zuständigkeit neben Direktmandat und
  Kandidatur — das Modell trägt sie über ein weiteres Feld am Mandat.

## Konzept-Verweis

Dieses Dokument. Bereich `area:projects`.
