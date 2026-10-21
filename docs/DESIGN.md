# Gestaltung: Design der Initiative Deutschlandtakt

Stand 2026-10-21. Ersetzt „Bahnhofshalle Tag (Direction F)“ vollständig. Dieses
Dokument ist die Kurzfassung mit den Regeln, die im Dashboard gelten; die
Werte stehen in den Quellen, der Umstellungsplan in
`docs/features/feature-idt-design.md`.

## Quellen

| Quelle | Rolle |
|---|---|
| Design System der Initiative (Artefakt `https://claude.ai/artifact/14Xq8ZVdYasy3EUQ8bLhGh`) | Tokens (`project/tokens.json` → `tokens.css`), Komponenten, Datenviz-Palette, Markenregeln, Favicons, Logo, Schrift |
| Anwendungsebene (DS-Abschnitt `anwendungsebene.md`; Ursprung `JonasPrade/ini_strategy` → `docs/design/anwendungsebene/README.md`) | Werkzeug-Bausteine: Tabellen, Felder, Dialoge, Datum, Status, Zustände, Navigation, Icons, Dunkelfassung |
| Strategie-Tool (`JonasPrade/ini_strategy`, `stakeholder/static/stil.css`) | Referenzumsetzung derselben Regeln, besonders die Dunkelfassung |
| Prototyp `docs/features/idt-design/` | Sichtreferenz für das Dashboard (Projektliste, Projektseite, Dialog, Handy) |

Bei Widerspruch: für Werkzeug-Bausteine gilt die Anwendungsebene vor dem DS;
Abweichungen des Dashboards stehen in der Entscheidungstabelle der Feature-Datei.

## Die Regeln in Kürze

1. **Nur Tokens.** Jede Farbe, Größe, jeder Abstand und Rahmen kommt aus
   `src/shared/theme/tokens.css` (DS, verbatim) oder den daraus gemischten
   Mantine-Skalen in `src/shared/theme/theme.ts`. Fachliche Zuordnungen
   (Phase → Farbe, Verkehrsart → Farbe, …) stehen ausschließlich in
   `src/shared/theme/semanticColors.ts`.
2. **Semantische Aliasse, nicht Markenkerne.** Oberflächen schreiben
   `--surface`, `--text-muted`, `--accent-primary`, `--border-frame`; nie
   `--idt-paper` oder `--idt-ink` direkt. Nur so trägt die Dunkelfassung.
3. **Papier und Ink.** Papier `#FFF6F0` ist die Fläche, Ink `#00373C` die
   Schrift und der Rahmen. Violett `#6E50FA` ist die Aktionsfarbe (Knöpfe,
   Links, Fokus, aktive Navigation), Cyan `#00DCFA` sekundär und als Fläche.
   **Gelb kommt im Dashboard nicht vor** (Anwendungsebene); die einzige
   Ausnahme ist die eine Hervorhebungszahl je Ansicht mit Ink-Kontur.
4. **Nur ein Status trägt Farbe.** Rot `#D64545` steht für Versäumnis
   (überfällig) und Löschen, sonst nichts. Erfolg ist ein Haken, kein Grün.
   Datenkategorien (Phasen, Verkehrsarten, Diagrammreihen) sind keine Status
   und tragen die Datenviz-Palette: kategorial `chart-1…6` in fester Reihenfolge,
   ordinal die Teal-Rampe `seq-1…5`, Abweichung `diverge-neg/mid/pos`.
   „In Betrieb“ ist `--idt-success`.
5. **Eckig und gerahmt.** Radius 0 überall. Rahmen 2px Ink (`--border-frame`),
   Haarlinien 1px (`--border`) nur innerhalb von Inhalt. Keine Blockschatten im
   Dashboard; weiche Schatten nur bei Karten der Variante `soft` und beim Dialog
   (`8px 8px 0 rgba(0,55,60,.18)`).
6. **Eine Schrift.** InterVariable, selbst gehostet (`src/shared/theme/fonts/`, von Vite gebündelt). Keine
   Mono-Schrift: Versal-Etiketten in Inter mit `letter-spacing: .12em`, Zahlen
   mit `font-variant-numeric: tabular-nums`. Grundschrift 16px, Stufen
   13 (Marke) · 13,5 (Etikett, Spaltenkopf) · 14,5 (Nebentext, Tabellen) ·
   16 · 19 (Abschnitt) · 21 (Ansichtstitel); Kennzahlen 36px, Band 56px.
7. **Maße der Anwendungsebene.** Bedienhöhe 40px (44 mobil), Tabellenzeile
   48px (`--row-h`), Kopfzeile 72px, Felder `2px` Rahmen mit `8px 11px`
   Polsterung, Fokus 2px Violett mit 2px Abstand. Hover ist ein Farbwechsel,
   nie ein Anheben.
8. **Lucide-Icons.** Nur Kontur, Strich 2, runde Enden, `currentColor`. 16px in
   Zeilen und Feldern, 20px in Leisten, 22–26px als Merkzeichen. Fehlt ein
   Zeichen, wird es aus Lucide nachgezogen, nicht gezeichnet.
9. **Zustände statt Kreisel.** Leer (Überschrift, Satz, eine Aktion), Lädt
   (Platzhalterbalken, kein Kreisel, kein Schimmern), Fehler (rote Innenkante,
   „Erneut versuchen“). Rückmeldung beim Speichern im Kopf der Ansicht.
10. **Keine Erklärtexte in der Oberfläche.** Ein Fragezeichen an der
    Überschrift verweist auf die Dokumentation.
11. **Dunkelfassung.** Vorgabe ist die Systemeinstellung, der Knopf im Kopf
    schaltet ausdrücklich um, die Wahl bleibt im Browser
    (`schienendashboard.thema`). Ink wird Fläche, Papier Schrift, Akzente hellen
    bis 4,5:1 auf (`--accent-primary` → `#ad9bff`). Violett selbst ist auf Ink
    kein Text. Rahmen werden `#8ca09f`, nicht Papier.
12. **Marke.** Bildmarke aus dem DS-Favicon-Set (Ink-Quadrat mit Gleisbalken)
    neben „Schienendashboard“ im Kopf; Inverse-Logo in der Fußzeile; Favicon-Set
    des DS im Tab. Das Logo wird nie neu gesetzt oder nachgezeichnet.

## Shell

- **Kopfzeile:** Papier, 2px Ink-Linie unten, 72px, Bildmarke 40px, Produktname
  19/700, Hauptbereiche als Textlinks 15/600 mit 3px violetter Unterkante am
  aktiven Punkt, Zähler im Ink-Rahmen auf Violett-Soft (rot gerahmt nur mit
  Überfälligem), Dunkel-Knopf rechts, Burger unter 62em.
- **Fußzeile:** Ink, 3px violette Oberkante, Inverse-Logo 26px, Fassung,
  Links Impressum · Datenschutz · Dokumentation.
- **Register** an der linken Kante der Projektseite (ab 62em Spalte, sonst
  Knopf „Abschnitte“ unten), aktiver Abschnitt mit 3px violetter Kante.

## Bausteine (Kurzliste, Werte in der Feature-Datei)

Button (bestätigend violett, abbrechend gerahmt, löschend rot gefüllt nur im
Dialog) · Felder (2px, Fokus violett, gesperrt Paper-3) · Checkbox 18px ·
Tabelle (Filterleiste, Auswahlleiste mit violetter Innenkante, Kopf 13,5/600 mit
2px Ink-Linie, 48px-Zeilen mit Haarlinie, kein Zebra, Karten unter 48em) ·
Dialog (2px Rahmen, harter Schatten, höchstens zwei Aktionen, mobil Vollbild) ·
Tag/Badge (22px, Versalien 11,5/600, kantig) · Callout (8px Linkskante in der
Statusfarbe, kein Rahmen, keine Fläche) · Kennzahl (36/56px, tabellarisch) ·
Karte `soft` (1px + Schatten) / `frame` (2px) / `inverse` (Ink) · Zustände ·
Rückmeldung.

## Mobil

Zwei Breakpoints, 48em und 62em (`feature-mobile-usability.md`). Die
Anwendungsebene wird darauf abgebildet: Karten unter 48em, Register ab 62em,
Bedienhöhe 44px und Vollbild-Dialoge unter 48em.

## Verboten

- Richtung-F-Elemente: Gold, Preußischblau, Anthrazit, Archivo Narrow, IBM
  Plex, Fallblatt, Goldpunkt, Signet-Quadrat, Tafel-Flächen.
- Gelb als Status oder Datenreihe; Grün als Erfolgsfläche; Rot für irgendetwas
  außer Versäumnis und Löschen.
- Verläufe als Flächen, Blockschatten, Hover-Anheben, Radien.
- Google Fonts oder andere externe Schrift- und Script-Quellen.
- DB-Rot `#ec0016` und Parteifarben (politische Kollision, gilt weiter).
- Emoji.

## Barrierefreiheit

- Fließtext 4,5:1, Icons und Rahmen 3:1 auf ihrem Grund, in beiden Fassungen.
  Die Kontrastgrenzen des DS gelten: `text-faint` (3,2:1) und `idt-success`/
  `idt-danger` (4,1:1) nicht für kleine Schrift auf Papier; `idt-warning` nie
  als Schrift; nie Papier auf Cyan; kein Violett-Text auf Ink.
- Farbe ist nie das einzige Signal: Status trägt Gewicht, Haken oder
  Unterkante; Phasen tragen Text und Quadrat.
- Tabulator in Lesereihenfolge, Fokusring 2px Violett; keine eigenen
  Tastenkürzel; Touch-Ziele 44px.

## Pflege

Ändert sich das DS, wird `tokens.css` ausgetauscht (Kopfkommentar mit
Artefakt-Version und Datum) und die Mantine-Skalen in `theme.ts` werden aus den
neuen Werten neu gemischt. Der Dunkel-Block am Ende der vendorten `tokens.css` ist aus
`tokens.json` erzeugt, weil das veröffentlichte DS ihn nicht enthält (#224); beim
Austausch prüfen, ob er nun mitkommt. Neue fachliche Farbzuordnungen kommen nur nach
`semanticColors.ts`. Das WordPress-Theme der Initiative und das Strategie-Tool
konsumieren dieselben Tokens; eine Abweichung in einem der drei Werkzeuge wird
im DS geklärt, nicht lokal.
