# Feature: Zeitstrahl-Ansicht (Gantt über mehrere Projekte)

Roadmap: „ProjectProgress: Gantt-Übersicht über mehrere Projekte" (bisher Long-Term).
Baut auf `feature-project-progress.md` auf (Beobachtungen, Glaubwürdigkeit, Prognose).

## Ziel

Neben **Karte** und **Liste** bietet die Startseite eine dritte Ansicht **„Zeitstrahl"**
(`/?view=timeline`). Sie zeigt die Projekte der gewählten Projektgruppen als Zeilen auf einer
gemeinsamen Jahresachse: wann welche Leistungsphase begann bzw. beginnen soll, wann der
Planfeststellungsbeschluss fällt und wann das Projekt in Betrieb geht. Angezeigt werden nur
Projekte mit **glaubwürdigen Terminen** — Projekte ohne belastbare Daten werden gezählt,
aber nicht gezeichnet.

## Was als „glaubwürdig" gilt

Ein Projekt erscheint, wenn es mindestens einen **konkreten Termin** hat:

| Meilenstein | Quelle (Vorrang wie in der Prognose) |
|---|---|
| Phasenbeginn Vorplanung / Genehmigungsplanung / Bau / Inbetriebnahme | erwarteter manueller Eintrag > sonst je Phase der glaubwürdigere × aktuellere Bericht: VIB-PFA-Termine (`baubeginn` frühester, `inbetriebnahme` spätester Abschnitt) oder Fulda-Prognose (`feature-fulda-import.md`) |
| Planfeststellungsbeschluss (PFB) | redaktionelles PF-Datum > frühestes `datum_pfb` der PFA |
| Parlamentarische Befassung | redaktionelles Datum der Befassung |

**Nicht** glaubwürdig und daher nie gezeichnet: BVWP-Dauerschätzungen und die
„Schätzung"-Platzhalter der Prognose.

Zusätzlich zeichnet der Zeitstrahl **Belege**: Für eine Phase ohne konkreten Termin dient das
früheste Datum einer *glaubwürdigen* Hauptspur-Beobachtung (effektive Konfidenz ≥
Glaubwürdigkeitsschwelle, nicht „erwartet") als „spätestens seit"-Punkt. Belege allein
qualifizieren ein Projekt nicht, und ein Beleg entfällt, wenn eine höhere Phase einen früheren
Termin hat (sonst widerspräche er der Phasenreihenfolge).

Übergeordnete Projekte bündeln ihren Teilbaum: frühester Beginn je Phase, späteste
Inbetriebnahme (wie die Prognose über PFA-Abschnitte).

### Getrennte Bauetappen

Bauen die Unterprojekte eines Oberprojekts zeitlich getrennt (Beispiel HLK 11 München-Ost –
Rosenheim: Etappe 1 01–07/2028, Etappe 2 01–07/2031), darf die Lücke zwischen den Etappen nicht
als Bauzeit erscheinen. Dafür trägt die Zeile zusätzlich `construction_periods`:

- Je **Mitglied des Teilbaums** (Oberprojekt selbst und jedes Unterprojekt) ein Intervall
  Baubeginn–Inbetriebnahme aus seinen *eigenen* konkreten Terminen (gleiche Vorrangregel wie
  oben). Ein PFA-Abschnitt, der einem anderen Unterprojekt zugeordnet ist, zählt nur dort —
  sonst brächte die VIB-Verknüpfung des Oberprojekts die ganze Hüllspanne als ein Intervall.
- Die Intervalle werden als **Vereinigungsmenge** zusammengelegt; überlappende oder direkt
  aneinandergrenzende Intervalle verschmelzen zu einer Periode.
- Geliefert wird nur bei **mindestens zwei** Perioden (echte Lücke); sonst bleibt die Liste
  leer und der Balken unverändert.
- Konservativ bei unvollständigen Daten — eine Lücke wird nie erfunden: Ein Mitglied mit
  Baubeginn ohne Inbetriebnahme (offenes Ende) oder mit widersprüchlichen Terminen hebt die
  Aufteilung auf; ebenso ein Mitglied nur mit Inbetriebnahme, außer diese liegt vor dem
  ersten Baubeginn (abgeschlossene ältere Etappe).

Darstellung: Der BAU-Balken wird auf die Perioden zugeschnitten, die Pause dazwischen als
dünne gestrichelte Linie in der Baufarbe („zwischen Bauetappen", nicht als Bau und nicht als
In Betrieb). Die Meilensteine bleiben unverändert: Baubeginn = erster Baubeginn, die
Kopfzeile „IB 07/2031" = letzte Inbetriebnahme.

Prognose und berechnete Phase des Oberprojekts sind davon nicht berührt und bleiben
konsistent: Die Prognose liest nur die eigenen Termine des Projekts, und die berechnete Phase
eines Oberprojekts ist die Spanne über die Blätter — während der Pause steht dort z. B.
„Genehmigungsplanung – In Betrieb", nicht „Bau".

## Verhalten

- Steuerung wie Liste und Karte: Projektgruppen über denselben Drawer wie auf der Karte
  (Mehrfachauswahl, „Übernehmen“; ohne Auswahl die vorausgewählten Gruppen, sonst alle),
  Suche, Schalter „Nur Hauptprojekte"; Zustand in der URL (`view=timeline`, `group=1,4`,
  `search`, `only_superior`, `sort`). Bei mehreren Gruppen lädt der Client den Zeitstrahl je
  Gruppe und führt die Zeilen zusammen (ein Projekt in zwei Gruppen erscheint einmal); die Zahl
  „ohne Termine“ rechnet er über die vereinigten Projekte nach. Seit 2026-10-31 — das frühere
  Einzel-Select war am Telefon unhandlich.
- Sortierung: Inbetriebnahme (Standard), Baubeginn, Name. Projekte ohne Sortierdatum ans Ende.
- Je Projekt eine Zeile: Name (Link zur Detailseite), darunter der Balken. Segmente in den
  Phasenfarben (`MAIN_PHASE_COLOR`) vom Phasenbeginn bis zum nächsten datierten Phasenbeginn;
  der Teil nach heute ist schraffiert gezeichnet (geplant; seit 2026-10-21, W4 in
  `feature-idt-design.md` — auf der Teal-Rampe des IDT-Designs wäre „heller“ unsichtbar). Inbetriebnahme als grüner Punkt,
  PFB und Parl. Befassung als Rauten, Belege als hohle Punkte. Tooltip je Marke: Meilenstein,
  Datum mit Präzision, Quelle (bei Annahmen die Herleitung); Tooltip je Balken: Zeitraum.
- „Heute"-Linie über alle Zeilen; Jahresachse mit Schrittweite nach Spanne (1/2/5 Jahre).
- Pausierte/abgebrochene Projekte werden abgeblendet und markiert.
- Mobil (360 px): Name über dem Balken, keine horizontale Scrollleiste.

### Unsichere Termine (Datumsqualifikation, #246)

Jeder Meilenstein trägt `date_precision`, `date_label`, `date_text` und `derivation`
(`feature-project-progress.md` → „Datumsqualifikation“). Angezeigt wird er so:

| Präzision | Darstellung |
|---|---|
| `EXACT` / `MONTH` | Balken mit festen Kanten wie bisher; Tooltip mit Tag bzw. Monat |
| `YEAR` | Balken ab 01.01. mit weicher linker Kante (Verlauf) und der Beschriftung „2028“; ohne Folgetermin spannt er das ganze Jahr. Endet eine Phase an einem Jahres-Termin, ist ihre rechte Kante weich. Eine Jahres-Marke sitzt zur Jahresmitte, hohl und gestrichelt. |
| `NOT_BEFORE` | kein geschlossener Balken und keine Marke: ein blass schraffierter, offener Bereich ab der Untergrenze bis zum rechten Rand, mit Pfeil nach rechts und „nach 2031 – Termin offen“ (bzw. dem Terminzusatz). Ist nur die Inbetriebnahme eine Untergrenze, läuft die Bauphase bis zur Grenze und geht dann in den offenen Bereich über („Inbetriebnahme nach 2031 – Termin offen“). Spätere Phasen sind unbekannt. |
| `ASSUMED` | gestrichelter Rahmen in Tintenfarbe um den Balken (die gestrichelte Linie in `seq-4` bleibt die Etappenpause, W3); die Marke ist hohl und gestrichelt; der Tooltip nennt die Herleitung („Annahme: 6 Monate Bauzeit …“). |

- **Kopfzeile:** „IB 2028“, „IB nach 2031“, „IB ca. 07/2028“; sonst MM/JJJJ.
- **Achse:** Eine Untergrenze zählt nur mit ihrem Grenzdatum; die Achse endet wie bisher
  mit dem Folgejahr und wird nicht künstlich gedehnt.
- **Sortierung:** nach dem Sortierwert.
- **Getrennte Bauetappen:** Ein Mitglied mit einer Untergrenze hebt die Aufteilung auf.
  Eine Lücke wird nie erfunden.
- **Legende:** erklärt „nur Jahr bekannt“, „nach … – Termin offen“ und „Annahme“.
- **Hell und dunkel:** beide geprüft. Die Beschriftung steht auf einer Fläche in der
  Oberflächenfarbe, damit sie auf der Schraffur lesbar bleibt.
- **Filter:** „Baubeginn/Inbetriebnahme von–bis“ und „Termin offen“ der Filterleiste wirken
  auch hier.

## Technik

- Pure Service `services/progress_timeline.py` (`build_timeline`), die konkreten Termine aus
  `progress_forecast.concrete_milestone_dates` (gemeinsame Vorrangregel mit der Prognose).
- CRUD `crud/projects/progress_timeline.py`: Sammelabfragen über alle Projekte der Gruppe
  inkl. Teilbäume (keine N+1), liest die gespeicherten Beobachtungen ohne Resync.
- Endpoint `GET /api/v1/project_groups/{group_id}/timeline?only_superior=true` (öffentlich,
  ohne Entwürfe) → `ProjectGroupTimelineSchema { group_id, items[], without_dates_count }`;
  je Item `milestones[]` und `construction_periods[] { start, end }` (`construction_periods`
  in `services/progress_timeline.py`).
- Frontend: `features/timeline/` (`TimelineView`, `timelineLayout.ts` mit Vitest-Tests),
  Hook `useProjectGroupTimeline` in `queries.ts`, dritte Option im `SegmentedControl` der
  `MapPage`.

## Akzeptanzkriterien

- [ ] `/?view=timeline` zeigt für eine Gruppe alle Projekte mit konkreten Terminen; die Zahl
      ausgeblendeter Projekte ohne Termine steht darüber.
- [ ] BVWP-Schätzungen erscheinen nicht.
- [ ] Sortierung, Suche und „Nur Hauptprojekte" wirken und stehen in der URL.
- [ ] Bei 360 px Breite keine horizontale Scrollleiste.
- [ ] Unit-Tests für `build_timeline` und das Layout, API-Test für den Endpoint.
- [ ] Oberprojekte mit getrennten Bauetappen (HLK 11) zeigen je Etappe ein BAU-Segment und
      dazwischen die Linie „zwischen Bauetappen"; überlappende Etappen bleiben ein Segment,
      Oberprojekte ohne Lücke sehen aus wie bisher.
- [ ] Unsichere Termine: Jahr mit weicher Kante, Untergrenze als offener Bereich mit Pfeil
      und „nach 2031 – Termin offen“, Annahme gestrichelt mit Herleitung im Tooltip; Legende
      erklärt alle drei, hell und dunkel lesbar.
