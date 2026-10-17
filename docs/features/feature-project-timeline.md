# Feature: Zeitstrahl-Ansicht (Gantt über mehrere Projekte)

Roadmap: „ProjectProgress: Gantt-Übersicht über mehrere Projekte" (bisher Long-Term).
Baut auf `feature-project-progress.md` auf (Beobachtungen, Glaubwürdigkeit, Prognose).

## Ziel

Neben **Karte** und **Liste** bietet die Startseite eine dritte Ansicht **„Zeitstrahl"**
(`/?view=timeline`). Sie zeigt die Projekte einer Projektgruppe als Zeilen auf einer
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

- Steuerung wie die Liste: eine Projektgruppe, Suche, Schalter „Nur Hauptprojekte"; Zustand
  in der URL (`view=timeline`, `group`, `search`, `only_superior`, `sort`).
- Sortierung: Inbetriebnahme (Standard), Baubeginn, Name. Projekte ohne Sortierdatum ans Ende.
- Je Projekt eine Zeile: Name (Link zur Detailseite), darunter der Balken. Segmente in den
  Phasenfarben (`MAIN_PHASE_COLOR`) vom Phasenbeginn bis zum nächsten datierten Phasenbeginn;
  der Teil nach heute ist heller gezeichnet (geplant). Inbetriebnahme als grüner Punkt,
  PFB und Parl. Befassung als Rauten, Belege als hohle Punkte. Tooltip je Marke: Meilenstein,
  Datum, Quelle.
- „Heute"-Linie über alle Zeilen; Jahresachse mit Schrittweite nach Spanne (1/2/5 Jahre).
- Pausierte/abgebrochene Projekte werden abgeblendet und markiert.
- Mobil (360 px): Name über dem Balken, keine horizontale Scrollleiste.

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
