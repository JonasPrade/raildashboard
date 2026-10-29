---
name: haushalt-nacharbeit
description: Arbeitet ein im Frontend bestätigtes Haushaltsjahr (Anlage VWIB Teil B) per MCP nach — FinVes ohne Projekt zuordnen, Sammel-FinVes je Jahr den finanzierten Projekten zuordnen, archivierte Zuordnungen auf Nachfolger umhängen, offene Zeilen einer FinVe zuweisen. Verwenden, wenn der Nutzer sagt „Haushalt-Import nacharbeiten“, „Haushalt 20xx aufräumen“, „FinVes zuordnen“, „Sammel-FinVes zuordnen“.
metadata:
  mcp: true
---

# Haushalt-Import nacharbeiten

Der Haushaltsbericht (Anlage VWIB, Teil B) wird **im Frontend** importiert (PDF
hochladen → Review → Bestätigen). Was danach offen bleibt, arbeitest du hier per MCP ab.
Den Import selbst kann der MCP nicht; ein Jahr mit unbestätigtem Lauf (`confirmed_at`
leer) erst im Frontend bestätigen lassen.

**Zwei Arten von Zuordnung:**

- **Reguläre FinVe** (eine Maßnahme, auch die ohne FinVe-Nummer aus den Tabellen 2–5):
  feste Zuordnung, gilt für alle Jahre → `update_finve_projects`.
- **Sammel-FinVe** (`is_sammel_finve`, z. B. „SV Lph. 1/2 A“, „SV EKrG 2021“,
  InvKG-Planungs-SVs): Zuordnung **je Haushaltsjahr** — welche Projekte sie in diesem
  Jahr finanziert → `set_sammel_finve_year_projects`.

Zuordnungen wirken sofort, stehen im Änderungsprotokoll des Projekts (zurücksetzbar) und
berechnen den Planungsstand neu. Bist du unsicher, lass die FinVe offen und sag es im
Bericht. Projekte anlegen oder zusammenführen nur, wenn der Nutzer das für diesen Lauf
will — frag einmal vorab, nicht je FinVe.

Rechte: `finve.edit` (Zuordnen), `haushalt.import` (offene Zeilen), für Bereinigung
zusätzlich `project.create`, `project.merge`.

## 1. Lage erfassen

1. `list_haushalt_years` — je Jahr `finves`, `finves_without_project`,
   `sammel_without_project`, `unmatched_open` und die Importläufe. Das neueste
   bestätigte Jahr zuerst.
2. Arbeitsliste holen: `list_haushalt_finves(haushalt_year, open_only=true)`, mit
   `limit`/`offset` blättern; nach Tabelle mit `table_number` (1 Bedarfsplan,
   2 Lärmsanierung, 3 ERTMS, 4 Kleine und Mittlere Maßnahmen, 5 InvKG).
3. Dem Nutzer die Zahlen nennen und fragen, ob auch angelegt bzw. zusammengeführt werden
   darf.

## 2. Reguläre FinVes ohne Projekt

Je FinVe:

1. `suggest_haushalt_finve_projects(finve_id)` — Kandidaten mit Gründen:
   `bedarfsplan` (eine andere FinVe mit derselben Bedarfsplannummer hängt schon an dem
   Projekt — der stärkste Hinweis), `name` (Namensähnlichkeit, schwach).
2. Prüfen mit `get_finve` (Name, Bedarfsplannummer, Budgetverlauf) und `get_project`:
   Gehört die FinVe zum Gesamtvorhaben oder zu einem Teilprojekt (Bauabschnitt,
   Planfeststellungsabschnitt)? Dann das Teilprojekt
   (`list_projects(superior_project_id=…)`).
3. Kein passender Kandidat: `list_projects(search=…)` mit markanten Orten aus dem Namen.
4. `update_finve_projects(finve_id, add_project_ids=[…], note="…")` — `note` mit der
   Begründung (z. B. „gleiche Bedarfsplannummer B0080 wie FinVe 2345“).

**Tabellen 2–5** (Lärmsanierung, ERTMS, Kleine und Mittlere Maßnahmen, InvKG) sind oft
Programme ohne einzelnes Projekt. Nur zuordnen, wenn es ein Projekt für genau dieses
Programm gibt (z. B. „Mittelrheintal“, „Digitaler Knoten Stuttgart“); sonst offen lassen
und im Bericht als Programm-FinVe nennen.

## 3. Sammel-FinVes je Jahr

Je Sammel-FinVe ohne Projekt im Jahr (oder mit `review_notes`):

1. `list_haushalt_finves` zeigt `erlaeuterung_projects` — die Maßnahmen, die der
   Bericht unter der Sammel-FinVe nennt. Das ist die Grundlage; ohne Erläuterung keine
   Zuordnung raten.
2. `suggest_haushalt_finve_projects(finve_id, haushalt_year)` — Gründe
   `erlaeuterung` (Name aus der Erläuterung passt), `other_year` (im anderen Jahr
   zugeordnet), `archived_link` (Zuordnung dieses Jahres hängt an einem archivierten
   Projekt; Kandidat ist der Nachfolger, `successor_of`).
3. Je Erläuterungs-Maßnahme ein Projekt bestimmen; die Erläuterung nennt meist
   Gesamtvorhaben (z. B. „ABS Hannover – Berlin“), dann das Gesamtprojekt, nicht ein
   Teilprojekt.
4. `set_sammel_finve_year_projects(finve_id, haushalt_year, project_ids, note="…")`
   **ersetzt** die Zuordnung dieses Jahres — immer die vollständige Liste übergeben.
   Zuordnungen archivierter Projekte bleiben als Historie stehen; archivierte Projekte
   lassen sich nicht neu zuordnen.
5. `following_years=true` nur, wenn die Erläuterung der Folgejahre dieselben Maßnahmen
   nennt (vorher in `list_haushalt_finves(haushalt_year=<Folgejahr>)` prüfen).

Ältere Jahre ändern nur, wenn der Nutzer das will; ein Fehler im Vorjahr ist meist im
Vorjahresbericht so gedruckt.

## 4. Offene Zeilen

1. `list_haushalt_unmatched_rows(haushalt_year)` — Zeilen, die der Import keiner FinVe
   zuordnen konnte (z. B. `B0140 L 03` ohne FinVe-Nummer).
2. FinVe suchen: `list_finves(search=<lfd. Nr. oder Name>, budget_year=…)`.
3. `resolve_haushalt_unmatched_row(row_id, finve_id)` — vermerkt nur die Zuordnung, schreibt
   keine Werte. Meldet das Tool `finve_has_budget_in_year: false`, fehlen die Werte des
   Jahres: im Bericht sagen, dass das Jahr neu importiert werden muss.

## 5. Gegenprobe und Bericht

1. `list_haushalt_years` erneut: `finves_without_project` und `unmatched_open` vorher →
   nachher.
2. Bericht an den Nutzer:
   - **Stand:** je Jahr zugeordnet / gesamt, offen vorher → nachher.
   - **Zugeordnet:** reguläre FinVes und Sammel-FinVes (mit Jahr), Auffälliges mit
     Begründung (Zuordnung nur über Namensähnlichkeit, Teilprojekt statt Gesamtvorhaben).
   - **Umgehängt:** archivierte Projekte → Nachfolger.
   - **Offen:** FinVes ohne Projekt und warum (Programm-FinVe, kein Projekt vorhanden,
     Erläuterung fehlt), offene Zeilen.
