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
| Phasenbeginn Vorplanung / Genehmigungsplanung / Bau / Inbetriebnahme | erwarteter manueller Eintrag > Fulda-Runde (wenn früher oder Lücke) > VIB-PFA-Termine (`baubeginn` frühester, `inbetriebnahme` spätester Abschnitt) |
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
  ohne Entwürfe) → `ProjectGroupTimelineSchema { group_id, items[], without_dates_count }`.
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
