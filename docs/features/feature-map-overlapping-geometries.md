# Feature: Überlappende Projektgeometrien auf der Karte

## Ziel

Belegen mehrere Projekte dieselbe Strecke oder denselben Bahnhof, soll auf der Karte jedes
von ihnen **sichtbar** und **auswählbar** sein. Heute liegt das eine deckungsgleich über dem
anderen, und nur das oberste reagiert auf Klick und Hover.

Drei Bausteine, einzeln auslieferbar:

| Baustein | Was | Wo |
|---|---|---|
| **A · Mehrfachauswahl** | Klick sammelt alle Projekte unter dem Zeiger und zeigt eine Liste; Hover hebt alle hervor | nur Frontend |
| **B1 · Parallele Spuren** | Überlappende Projekte bekommen unterschiedliche Spuren und werden zoomabhängig nebeneinander gezeichnet | Backend + Frontend |
| **D · Zähler an Bahnhöfen** | Koordinatengleiche Punkte werden zu einem Punkt mit Anzahl zusammengefasst | nur Frontend |

Grundlage ist die Vorschlagsseite mit klickbaren Demos
(https://claude.ai/artifact/Kizsac1wC7f11XptjpnHFg); gewählt wurden dort A, B1 und D.

Issues: A #273 · B1 Backend #274 · B1 Frontend #275 · MCP `check_geometry` #276 · D #277.

## Kontext

`apps/frontend/src/features/map/MapView.tsx` baut je Projekt genau ein Linien-Feature
(Source `project-routes`, `MultiLineString`) und ein Punkt-Feature (Source `project-points`,
`MultiPoint`), Feature-ID = Projekt-ID. Der Klick-Handler (`handleProjectClick`) nimmt
`event.features[0]`, der Hover-Handler (`handleMouseMove`) ebenso nur den obersten Treffer
von `queryRenderedFeatures`.

Typische Fälle:

- Ein Ausbau-Korridor und eine Elektrifizierung desselben Abschnitts, beide über das
  Schienennetz geroutet: deckungsgleich auf dem gemeinsamen Abschnitt.
- Mehrere Punktprojekte an derselben Betriebsstelle: ein sichtbarer Kreis.
- Bei ausgeschaltetem „Nur Hauptprojekte“ Über- und Unterprojekt (die Geometrie des
  Überprojekts ist die Vereinigung seiner Kinder, `feature-parent-geojson-merge.md`).
  Dieser Fall wird hier nur über A erreichbar gemacht, nicht eigens dargestellt (siehe
  *Nicht im Scope*).

Die Übersichtskarte bekommt vereinfachte Geometrien über
`GET /api/v1/project_groups/{id}/geometries` (Douglas-Peucker, ~20 m, Koordinaten auf fünf
Nachkommastellen, `services/geometry_simplify.py`, `feature-slim-project-groups.md`). Zwei
Projekte auf derselben Strecke haben danach unterschiedliche Stützpunkte. Ob sich Linien
überlappen, lässt sich im Browser deshalb nicht zuverlässig erkennen; das ermittelt der
Server (B1).

## Scope

- **A:** Klick und Hover auf der Karte berücksichtigen alle Treffer; Auswahlliste im Popup.
  Gilt für jede `MapView` (Übersichtskarte `/` und „Karte – Unterprojekte“ auf der
  Detailseite).
- **B1:** Materialisierte Tabelle überlappender Projektpaare, gefüllt im bestehenden
  Geometrie-Kaskadenlauf; Spurzuweisung; Auslieferung über den geometries-Endpoint;
  Zeichnen mit datengetriebenem `line-offset`. Nur Übersichtskarte.
- **B1-Prüfwerkzeug:** MCP `check_geometry` meldet Überlappungen mit anderen Projekten
  (Hinweis auf Dubletten für `merge_projects`).
- **D:** Zusammenfassen koordinatengleicher Punkte mit Zähler; Klick öffnet die Liste aus A.

## Nicht im Scope

- **Elternband** (Überprojekt als breites Band hinter seinen sichtbaren Unterprojekten bei
  ausgeschaltetem „Nur Hauptprojekte“). Über- und Unterprojekt bleiben in diesem Fall
  deckungsgleich, sind aber über die Liste aus A beide erreichbar.
- **Streifen** auf gemeinsamen Abschnitten (B3) und **Transparenz** (B4).
- **Strichmuster je Spur** (B2). Mögliche spätere Ergänzung, falls ähnliche Gruppenfarben
  auf benachbarten Spuren schwer zu unterscheiden sind; `line-dasharray` ist nicht
  datengetrieben und bräuchte einen Layer je Spur.
- Spuren auf der Detailkarte („Karte – Unterprojekte“). Sie zeigt die exakte Geometrie aus
  `GET /projects/{id}` und bekommt keine Überlappungsdaten; A und D greifen dort trotzdem.
- Auffächern von Bahnhofspunkten im Kreis (Spider-Cluster).
- Zusammenführen von Dubletten: `check_geometry` weist nur darauf hin, entschieden wird
  weiterhin mit `merge_projects`.

## Gewünschtes Verhalten

### Baustein A · Mehrfachauswahl

**Treffer sammeln.** Klick und Hover fragen `queryRenderedFeatures` über
`project-routes-line` und `project-points-circle` (ab D zusätzlich den Zähler-Layer) ab und
deduplizieren nach `projectId`. Statt eines einzelnen Pixels wird ein kleines Rechteck um den
Zeiger abgefragt (Vorschlag ±4 px, bei grobem Zeiger `(pointer: coarse)` ±8 px), damit eine
4 px breite Linie und die benachbarten Spuren aus B1 auch mit dem Finger getroffen werden.
Reihenfolge der Treffer: nach Name (stabil, unabhängig von der Zeichenreihenfolge).

**Ein Treffer.** Wie heute: Kurzkarte (`ProjectSummaryCard`) mit „Auswählen“.

**Mehrere Treffer.** Popup mit Liste:

- Überschrift „N Projekte an dieser Stelle“.
- Je Eintrag: Farbfeld in Gruppenfarbe (dieselbe, die die Karte zeichnet), Name,
  Projektnummer rechts in gedämpfter Schrift. Eintrag ist ein Knopf, auf grobem Zeiger
  ≥ 44 px hoch (`feature-mobile-usability.md`).
- Hover oder Fokus auf einen Eintrag hebt **nur** die Linie bzw. die Punkte dieses
  Projekts hervor (`feature-state hover`), die anderen Hervorhebungen gehen so lange aus.
- Klick auf einen Eintrag ersetzt die Liste durch dessen Kurzkarte mit „Auswählen“ und
  darüber einem Rückweg „← Alle N Projekte“.
- Ab etwa acht Einträgen scrollt die Liste innerhalb des Popups; das Popup bleibt bei 360 px
  Breite vollständig sichtbar (bestehende Begrenzung `min(340px, calc(100vw - 32px))` und
  Randkorrektur in `MapView.tsx`).
- Escape und Klick außerhalb schließen das Popup wie heute.

**Hover auf der Karte.** Alle Projekte unter dem Zeiger werden hervorgehoben (Linien und
Punkte), nicht nur das oberste. Verlässt der Zeiger sie, gehen alle Hervorhebungen aus.

**Wahlkreise.** Der Vorrang bleibt: Liegt ein Projekt unter dem Zeiger, wählt der Klick
keinen Wahlkreis (`feature-abgeordnete.md` → Kartenlayer). Das Rechteck aus „Treffer
sammeln“ gilt dabei auch für diese Prüfung, damit beide dieselben Treffer sehen.

### Baustein B1 · Parallele Spuren

**Darstellung.** Jedes Projekt hat eine Spur `lane` (0, 1, 2, …). Spur 0 liegt auf dem Gleis;
Spur 1 rechts, Spur 2 links, Spur 3 doppelt rechts, Spur 4 doppelt links usw.:

```
laneOffset(lane) = 0                    für lane = 0
                 = +ceil(lane / 2)      für ungerade lane
                 = -lane / 2            für gerade lane
```

Der Versatz wächst mit dem Zoom: herausgezoomt liegen die Linien aufeinander, ab etwa
Zoom 12 stehen sie im Abstand `lineWidth + 2` px nebeneinander. Der Linienbreiten-Slider
skaliert den Abstand mit. Projekte ohne Überlappung behalten Spur 0 und sehen aus wie heute.

**Was als Überlappung zählt.** Zwei Projekte überlappen, wenn ihre Linien auf einer
gemeinsamen Länge von mindestens 500 m **oder** mindestens 50 % der kürzeren Linie (dann
mindestens 100 m) innerhalb eines Puffers von 25 m zueinander verlaufen (W4). Nur Linien,
keine Punkte (dafür ist D da). Archivierte Projekte und Entwürfe zählen nicht (sie stehen nicht
auf der Karte; „ein archiviertes Projekt zählt nirgends“, `architecture.md` → Principles).

Über- und Unterprojekte zählen wie alle anderen (W5). Ob beide auf der Karte stehen, regelt
der Schalter „Nur Hauptprojekte“: Ist er an (Standard), sind die Unterprojekte nicht geladen,
und das Überprojekt bleibt auf dem Gleis, weil nur sichtbare Projekte Spuren belegen (W1).
Ist er aus, liegen Über- und Unterprojekt nebeneinander statt deckungsgleich.

Die 25 m decken Abweichungen zwischen zwei Routings desselben Gleises und zwischen
Richtungsgleisen ab (Gleismittenabstand ~4 m, Routing-Abweichung einige Meter), ohne
parallel geführte, getrennte Strecken (S-Bahn neben Fernbahn mit eigenem Bahnkörper,
meist > 25 m) zusammenzuziehen.

**Spurzuweisung.** Aus den Paaren entsteht ein Graph (Knoten = Projekte, Kanten =
Überlappungen). Benachbarte Projekte bekommen unterschiedliche Spuren, jeweils die kleinste
freie. Zwei Stufen (W1):

1. **Server, über alle Projekte:** jedes Projekt hat eine gespeicherte Spur. Sie ist
   **stabil** (W3): Ändert sich die Geometrie von Projekt P, behält P seine Spur, solange
   kein Überlappungspartner sie hat, sonst bekommt P die kleinste freie. Die Partner
   behalten ihre. Nach absteigendem Grad neu gefärbt wird nur bei der Erstbefüllung.
2. **Browser, nur sichtbare Projekte:** Der Server liefert je Projekt die gespeicherte Spur
   und die IDs seiner Partner. Die Karte färbt nur die gerade sichtbaren Projekte (nach
   Gruppe, Planungsphase, Datum, Suche und „Nur Hauptprojekte“), in der Reihenfolge
   gespeicherte Spur, dann ID. Ein Projekt, dessen Partner ausgeblendet ist, liegt so auf
   dem Gleis, und zwei gleichzeitig eingeblendete Gruppen kollidieren trotzdem nicht.

**Richtung.** `line-offset` versetzt relativ zur Zeichenrichtung der Linie. Zwei Projekte,
deren Linien in entgegengesetzter Richtung digitalisiert sind, landeten mit Spur 1 und 2 auf
derselben Seite. Der Server liefert die vereinfachten Linienteile deshalb einheitlich
ausgerichtet aus: Start westlich des Endes, bei gleichem Längengrad südlich (W2). Das trifft
den Normalfall; nur Schleifen und U-förmige Teile können unsauber bleiben.

### Baustein D · Zähler an Bahnhöfen

- Punkte mehrerer Projekte mit identischen Koordinaten (nach Rundung auf fünf
  Nachkommastellen, wie der Server sie liefert; auf der Detailkarte rundet das Frontend
  selbst) werden zu **einem** Punkt zusammengefasst. Mehrere Punkte desselben Projekts an
  derselben Stelle zählen einmal.
- Darstellung: größerer Kreis (Vorschlag `pointSize + 5`) mit Ink-Rand und der Anzahl als
  Text in der Mitte, in der Schrift des Design Systems (Inter, `--font-sans`, fett). Füllfarbe: Gruppenfarbe der Mehrheit der beteiligten Projekte, bei
  Gleichstand die des ersten (nach der Reihenfolge der Projekte auf der Karte).
- Punkte mit nur einem Projekt bleiben unverändert.
- Klick öffnet dieselbe Liste wie A. Hover auf den Zählerpunkt hebt alle beteiligten
  Projekte hervor, auch ihre Linien und übrigen Punkte; Hover auf ein Projekt (Linie,
  Listeneintrag) hebt auch die Zählerpunkte hervor, an denen es beteiligt ist.
- Der Punktgrößen-Slider skaliert den Zählerpunkt mit.

## Entscheidungen

Aus dem Widerspruchs-Check (2026-10-25), entschieden von Jonas am 2026-10-26.

| # | Frage | Entscheidung |
|---|---|---|
| W1 | Spur global oder je sichtbarer Auswahl? | Server speichert eine globale Spur und liefert die Überlappungspartner mit; der Browser färbt nur die sichtbaren Projekte (globale Spur als Vorzug, dann ID). |
| W2 | Zeichenrichtung | Server richtet jeden vereinfachten Linienteil einheitlich aus (Start westlich des Endes, bei gleichem Längengrad südlich). |
| W3 | Stabilität der Spur | Inkrementell: P behält seine Spur, solange kein Partner sie hat, sonst die kleinste freie; Partner bleiben. Vollfärbung nur bei der Erstbefüllung. |
| W4 | Schwelle für „überlappt“ | Gemeinsame Länge ≥ 500 m **oder** ≥ 50 % der kürzeren Linie (mindestens 100 m). |
| W5 | Über-/Unterprojekt-Paare | Keine Sonderbehandlung, sie zählen wie alle anderen. Ob beide sichtbar sind, regelt der Schalter „Nur Hauptprojekte“; mit W1 belegen unsichtbare Unterprojekte keine Spur. In `check_geometry` erscheinen sie nicht als Befund (dort sind sie erwartet, keine Dublette). |
| D1 | Schrift im Zähler | Design-System-Schrift Inter. MapLibre kann für Kartentext keine woff2-Datei verwenden, sondern bräuchte eigens erzeugte Glyphen-Dateien. Deshalb zeichnet MapLibre nur den Kreis, die Zahl liegt als HTML-Element darüber (siehe *Frontend*). |

## Akzeptanzkriterien

### A · Mehrfachauswahl

- [ ] Auf `/` zwei Gruppen einblenden, in denen zwei Projekte dieselbe Strecke belegen. Auf
      den gemeinsamen Abschnitt klicken: Popup „2 Projekte an dieser Stelle“ mit beiden
      Einträgen (Farbfeld, Name, Projektnummer).
- [ ] Mit der Maus über den ersten Listeneintrag fahren: nur dessen Linie wird breiter.
- [ ] Ersten Eintrag anklicken: Kurzkarte dieses Projekts mit „Auswählen“; „← Alle 2
      Projekte“ führt zurück zur Liste; „Auswählen“ öffnet die Detailseite (mit `?group=`
      wie heute).
- [ ] Auf einen Abschnitt klicken, auf dem nur ein Projekt liegt: direkt die Kurzkarte, wie
      heute.
- [ ] Mit der Maus über den gemeinsamen Abschnitt fahren (ohne Klick): beide Linien werden
      breiter; Zeiger wegbewegen: beide wieder normal.
- [ ] „Nur Hauptprojekte“ ausschalten, auf einen Abschnitt eines Überprojekts klicken:
      Liste nennt Überprojekt und Unterprojekt.
- [ ] Wahlkreise einblenden, auf einen gemeinsamen Abschnitt klicken: Projektliste
      erscheint, kein Wahlkreis wird ausgewählt.
- [ ] Bei 360 px Breite (Smartphone) einen gemeinsamen Abschnitt antippen: Liste vollständig
      sichtbar, Einträge mit dem Finger treffbar, Liste scrollt bei vielen Einträgen im Popup.
- [ ] Detailseite eines Überprojekts mit überlappenden Unterprojekten: Klick auf den
      gemeinsamen Abschnitt in „Karte – Unterprojekte“ zeigt die Liste.

### B1 · Parallele Spuren

- [ ] Zwei überlappende Projekte auf `/` einblenden und bis Zoom 12 heranzoomen: beide
      Linien liegen nebeneinander, eine davon auf dem Gleis. Bei Zoom 8 liegen sie
      aufeinander.
- [ ] Ein drittes Projekt auf demselben Abschnitt: es liegt auf der anderen Seite des Gleises.
- [ ] Linienbreiten-Slider vergrößern: Linien werden dicker, der Abstand wächst mit, sie
      berühren sich nicht.
- [ ] Ein Projekt ohne Überlappung liegt bei jedem Zoom auf dem Gleis.
- [ ] Phasenfilter so setzen, dass nur eines von zwei überlappenden Projekten sichtbar
      ist: es liegt auf dem Gleis.
- [ ] Geometrie eines Projekts per „Geometrie verwalten“ ändern (z. B. neu routen), Karte neu
      laden: unbeteiligte Projekte behalten ihre Seite.
- [ ] Projekt archivieren: sein Partner rückt auf das Gleis zurück.
- [ ] `GET /api/v1/project_groups/{id}/geometries` liefert die Spurdaten; nach einer
      Geometrieänderung in einer **anderen** Gruppe antwortet derselbe Aufruf mit neuem ETag,
      ohne Änderung mit 304.

### MCP `check_geometry`

- [ ] `check_geometry(project_id=…)` für ein Projekt mit Überlappung nennt den Befund
      `overlaps` mit Partner-ID, Name und gemeinsamer Länge in km.
- [ ] Zwei fast deckungsgleiche Projekte (je ≥ 90 % der eigenen Länge gemeinsam): der Befund
      trägt den Hinweis auf eine mögliche Dublette und `merge_projects`.
- [ ] Ein Überprojekt meldet seine eigenen Unterprojekte nicht als Überlappung (W5).

### D · Zähler an Bahnhöfen

- [ ] Drei Punktprojekte an derselben Betriebsstelle einblenden: ein Kreis mit „3“, Füllung
      in der Gruppenfarbe der Mehrheit, Ink-Rand.
- [ ] Zählerpunkt anklicken: Liste mit drei Einträgen wie bei A; Hover auf einen Eintrag hebt
      dessen Punkte hervor.
- [ ] Mit der Maus über den Zählerpunkt fahren: alle drei Projekte werden hervorgehoben,
      auch ihre Linien.
- [ ] Punktgrößen-Slider: Zählerpunkt wächst mit, Zahl bleibt lesbar.
- [ ] Bei 360 px Breite: Zählerpunkt antippbar, Liste vollständig sichtbar.

## Technische Notizen

### Annahmen geprüft (2026-10-25)

- MapLibre GL JS `^5.6.2` (`apps/frontend/package.json`): `line-offset` ist datengetrieben
  und darf zoom- **und** eigenschaftsabhängig sein. **Korrektur zum Entwurf:** `["zoom"]` ist
  nur als Eingabe eines **äußersten** `interpolate`/`step` erlaubt; ein `["*", …,
  ["interpolate", …, ["zoom"], …]]` lehnt der Style-Validator ab. Richtig:

  ```ts
  "line-offset": [
      "interpolate", ["linear"], ["zoom"],
      8, 0,
      12, ["*", ["get", "laneOffset"], lineWidth + 2],
  ]
  ```

  Beim Slider-Effekt (`setPaintProperty`) wie heute bei `line-width` neu setzen.
- `feature-state` funktioniert für beliebig viele IDs gleichzeitig (ein `setFeatureState` je
  ID); die IDs sind die numerischen Projekt-IDs. Für A wird `hoverFeatureIdRef` zur Menge.
- `queryRenderedFeatures` kann ein Projekt mehrfach liefern (Kachelgrenzen, mehrere Layer);
  deshalb die Deduplizierung nach `projectId`.
- Array-Properties in einer GeoJSON-Source kommen aus `queryRenderedFeatures` als
  JSON-Text zurück. Für D also die Projekt-IDs je Zählerpunkt in einer Lookup-Map im Ref
  halten, im Feature nur Schlüssel, Anzahl und Farbe.
- Die Projekt-Geometrie ist Text (`project.geojson_representation`), es gibt keine
  Geometriespalte. Der Wahlkreisabgleich rechnet in PostGIS gegen die indizierte
  `constituency.geom` und ist auf SQLite ein No-op. Für die Überlappung zweier
  Projekttexte bringt PostGIS keinen Index-Vorteil; **Shapely** (`shapely==2.1.2`, schon für
  das Vereinfachen im Einsatz) rechnet auf beiden Dialekten und ist damit in `make test`
  prüfbar. Kein `pyproj`: für 25 m genügt eine lokale äquirektanguläre Projektion um die
  mittlere Breite des Paars.
- ETag: `etag_json_response` hasht den Body; neue Spurdaten im Body ändern den ETag von
  selbst, auch wenn sich nur ein Partner in einer anderen Gruppe geändert hat. Kein
  zusätzlicher Mechanismus nötig.
- Alle Geometrie-Schreibwege laufen heute über `recompute_links_for_project_ids`
  (`update_project`, `recompute_geojson_for_parent`, `merge.py`, `archive.py`); die
  Kaskade reicht die berührten Vorfahren schon als `touched` durch.

### Backend (B1)

**Datenmodell** (neue Datei `models/projects/project_map_geometry.py`, Migration additiv):

| Tabelle | Spalten | Zweck |
|---|---|---|
| `project_map_geometry` | `project_id` (PK, FK `project.id` `ON DELETE CASCADE`), `min_lon`, `min_lat`, `max_lon`, `max_lat`, `line_km`, `geometry_hash`, `lane` (SmallInteger, NULL = keine Linie), `computed_at` | Bounding-Box als Vorfilter, Hash zum Überspringen unveränderter Geometrie, gespeicherte Spur |
| `project_overlap` | `project_a_id`, `project_b_id` (PK zusammen, FKs `ON DELETE CASCADE`, Check `a < b`), `shared_km`, `share_a`, `share_b` (Anteil an der eigenen Linienlänge), `computed_at` | materialisierte Überlappungspaare; Index auf `project_b_id` |

**Berechnung** in neuem `services/project_overlap.py`:

```
recompute_overlaps_for_project_ids(db, ids)
  für jedes P in ids:
    Linien von P parsen (volle Auflösung, 2D, unary_union) → keine Linie / archiviert /
      Entwurf: Zeilen von P löschen, lane = NULL, fertig
    Hash unverändert → überspringen
    Bounding-Box, line_km, Hash schreiben
    Kandidaten: Bounding-Box-Schnitt per SQL (Box um 25 m erweitert), ohne P, ohne
      archivierte und Entwürfe (Über-/Unterprojekte zählen mit, W5)
    je Kandidat Q: shared = min(len(Q ∩ buffer(P, 25 m)), len(P ∩ buffer(Q, 25 m)))
      Schwelle (W4) erfüllt → Paar schreiben, sonst Paar löschen
    Spur von P neu bestimmen (W3)
recompute_all_overlaps(db) → Stats   # Erstbefüllung, Vollfärbung nach absteigendem Grad
```

Geparste und projizierte Kandidatenlinien werden wie in `geometry_simplify.py` je
Prozess nach Hash zwischengespeichert. Laufzeit: Die Bounding-Box filtert auf eine
Handvoll bis wenige hundert Kandidaten (lange Korridore haben große Boxen); je Kandidat
Puffer und Schnitt im Millisekundenbereich.

**Einhängen.** Ein gemeinsamer Helfer (`refresh_derived_geometry(db, ids)`) ruft
`recompute_links_for_project_ids` und `recompute_overlaps_for_project_ids` auf und ersetzt
die heutigen Aufrufe von `recompute_links_for_project_ids` in `crud/projects/projects.py`,
`merge.py` und `archive.py`. So kann kein Schreibweg eines der beiden vergessen. Wie beim
Wahlkreisabgleich darf ein Fehler (Savepoint) das Speichern nicht scheitern lassen.

**Auslieferung.** `ProjectGroupGeometriesSchema` bekommt ein neues Feld (rückwärtskompatibel,
Default leer):

```python
class MapLaneSchema(BaseModel):
    lane: int = 0
    overlaps: list[int] = []   # IDs der Überlappungspartner (W1)

lanes: dict[int, MapLaneSchema] = {}   # nur Projekte mit lane > 0 oder Partnern
```

`read_project_group_geometries` liest es in einer Abfrage für die Projekte der Gruppe.
Ausrichtung der Linienteile (W2) in `geometry_simplify._simplify`, damit der Cache sie
mitnimmt.

**Erstbefüllung.** Die Überlappungen werden beim Speichern eines Projekts berechnet. Nach
dem Deploy ist die Tabelle aber leer, denn die vorhandenen Projekte wurden ja noch nicht neu
gespeichert. Sie muss deshalb einmal für alle Projekte gefüllt werden. Das läuft
**automatisch**: Findet das Backend beim Start eine leere `project_map_geometry`, stößt es
einmal die Celery-Aufgabe `recompute_all_overlaps_task` an (läuft im Worker, blockiert den
Start nicht). Bis sie fertig ist, ist `lanes` leer und die Karte sieht aus wie heute. Für
einen späteren Neuaufbau von Hand gibt es zusätzlich `POST /api/v1/admin/overlap-recompute`
(wie `progress-recompute`, Recht wie dort). Kein Handschritt nach dem Deploy.

### MCP

- `services/geometry_check.py` / `mcp/tools/data_quality.py`: neuer Befund `overlaps` in
  `check_geometry`, gelesen aus `project_overlap` (keine Neuberechnung im Tool): je Partner
  `project_id`, `name`, `shared_km`, `share_self`, `share_other`, größte zuerst, höchstens
  fünf. Eigene Vor- und Nachfahren (Über-/Unterprojekte) erscheinen nicht: sie überlappen
  zwangsläufig und sind keine Dublette (W5). Sind beide Anteile ≥ 90 %, trägt der Eintrag `possible_duplicate: true` mit dem
  Hinweis auf `merge_projects` (erst ohne `apply`).
- Doku im selben Commit: `docs/features/feature-mcp-server.md` (Befundtabelle unter
  *Datenpflege*), Server-Instruktionen in `mcp/server.py`, falls sie Befunde aufzählen, und
  `.claude/skills/gvfg-nacharbeit/SKILL.md` → „Mehrfachzuordnungen und Dubletten“
  (`check_geometry` als Beleg für eine Dublette). Heute (2026-10-25) nennt kein anderer Skill
  `check_geometry`; bei der Umsetzung erneut prüfen (AGENT.md → Skills).

### Frontend

- `MapView.tsx`:
  - A: Treffer-Rechteck, Deduplizierung, Hover-Menge, Popup-Zustand
    `{ kind: "list" | "single", projects, x, y }`, neue Komponente für die Liste.
  - B1: Feature-Property `laneOffset` aus der Spur; `line-offset` wie oben; Slider-Effekt
    setzt `line-offset` mit. Die Färbung der sichtbaren Projekte (W1) als reine
    Funktion (`assignVisibleLanes(projects, lanes)`) mit Unit-Test. Die Hover-Breite
    `lineWidth + 4` darf die Nachbarspur kurz überdecken. Soll die hervorgehobene Linie
    oben liegen: `line-sort-key` ist eine Layout-Eigenschaft und kann `feature-state` nicht
    lesen; dafür eine zweite Linien-Ebene mit `setFilter(["in", ["get", "projectId"],
    ["literal", ids]])` über der normalen.
  - D: Punkt-Features je gerundeter Koordinate statt je Projekt; synthetische Feature-IDs
    mit Lookup `featureId → projectIds` und `projectId → featureIds` für Hover; Layer
    `project-points-counter` (`circle`, gefiltert auf Anzahl > 1) trägt Farbe, Rand,
    Klick und Hover. Die Zahl (D1) ist ein `maplibregl.Marker` je Zählerpunkt mit einem
    `<span>` in `--font-sans`, fett, `pointer-events: none`, damit Klick und Hover beim
    Kreis darunter ankommen. Kein `symbol`-Layer: der bräuchte eine Glyphs-URL, die der
    Style nicht hat, und eigens erzeugte Glyphen-Dateien der Inter. Die Marker werden bei
    jeder Datenänderung neu gesetzt; es sind nur die mehrfach belegten Punkte.
- `MapPage.tsx`: Spurdaten aus `useProjectGroupGeometries` an `MapViewProject` hängen.
- `shared/api/queries.ts`: `combineGeometries` führt `lanes` mit; `make gen-api`.
- `shared/theme/semanticColors.ts`: Farbe für den Zählerrand und -text (`MAP_COLOR`, Ink)
  hier ergänzen, nicht in `MapView.tsx` (`architecture.md` → Principles, `DESIGN.md`).
- `features/documentation/DocumentationPage.tsx`: Kartenabschnitt um Liste, Spuren, Zähler.

### Betroffene Dateien

| Datei | Baustein | Änderung |
|---|---|---|
| `apps/frontend/src/features/map/MapView.tsx` | A, B1, D | siehe oben |
| `apps/frontend/src/features/map/MapOverlapList.tsx` (neu) | A | Liste im Popup |
| `apps/frontend/src/features/map/assignVisibleLanes.ts` (neu, W1 b) | B1 | Färbung sichtbarer Projekte + Test |
| `apps/frontend/src/features/map/MapPage.tsx` | B1 | Spur an Projekte hängen |
| `apps/frontend/src/shared/api/queries.ts` | B1 | `lanes` zusammenführen |
| `apps/frontend/src/shared/theme/semanticColors.ts` | D | Zählerfarben |
| `apps/frontend/src/features/documentation/DocumentationPage.tsx` | A, B1, D | In-App-Doku |
| `apps/backend/dashboard_backend/models/projects/project_map_geometry.py` (neu) | B1 | zwei Tabellen |
| `apps/backend/alembic/versions/…_add_project_overlap.py` (neu) | B1 | additive Migration |
| `apps/backend/dashboard_backend/services/project_overlap.py` (neu) | B1 | Berechnung, Spur |
| `apps/backend/dashboard_backend/crud/projects/projects.py`, `merge.py`, `archive.py` | B1 | `refresh_derived_geometry` |
| `apps/backend/dashboard_backend/services/geometry_simplify.py` | B1 | Ausrichtung (W2) |
| `apps/backend/dashboard_backend/schemas/projects/project_group_schema.py` | B1 | `lanes` |
| `apps/backend/dashboard_backend/api/v1/endpoints/project_groups.py` | B1 | `lanes` ausliefern |
| `apps/backend/dashboard_backend/api/v1/endpoints/admin_assignments.py`, `tasks/` | B1 | Task + Endpoint für den Neuaufbau |
| Backend-Start (Lifespan) | B1 | Erstbefüllung anstoßen, wenn die Tabelle leer ist |
| `apps/backend/dashboard_backend/services/geometry_check.py`, `mcp/tools/data_quality.py` | MCP | Befund `overlaps` |
| `docs/features/feature-mcp-server.md`, `.claude/skills/gvfg-nacharbeit/SKILL.md` | MCP | Doku, Skill |
| `CHANGELOG.md`, `docs/production_setup.md` | B1 | Erstbefüllung beim ersten Start vermerken |

### Migration

Eine Revision (`make migrate-create MSG="add project overlap tables"`), nur neue Tabellen,
keine Änderung an `project`. Ein Rollback auf den alten Code ignoriert die Tabellen
(Expand/Contract). Die Migration befüllt nichts (Erstbefüllung siehe oben): leere Tabellen bedeuten Spur 0 für alle,
also das heutige Bild. Keine neue harte Abhängigkeit für `/healthz`.

## Verifikation

- Backend: Unit-Tests für `project_overlap.py` mit synthetischen Linien (deckungsgleich,
  versetzt um 10 m und 40 m, kurz unter lang, gegenläufig, Über-/Unterprojekt, archiviert),
  Spurzuweisung inkl. Stabilität; Erstbefüllung beim Start nur bei leerer Tabelle; API-Test für `lanes` und ETag im geometries-Endpoint;
  Test für den Befund `overlaps` in `check_geometry`.
- Frontend: Unit-Tests für Deduplizierung der Treffer, `assignVisibleLanes`,
  Punktzusammenfassung und Mehrheitsfarbe; Komponententest für die Liste.
- `make test` (wie in der CI).
- Manuell: Klickpfade aus den Akzeptanzkriterien, auch bei 360 px Breite.
