# Feature: Betriebsstellen als GeoJSON-Point-Features

## Ziel

Im "Geometrie verwalten"-Modal können Betriebsstellen per Suchfeld als `Point`-Features zur
`geojson_representation` eines Projekts hinzugefügt werden. Die Suchlogik ist identisch mit der
Routing-Formular-Combobox. Der `deleteExisting`-Toggle steuert, ob bestehende Geometrie ersetzt
wird — einheitlich für Linien und Punkte.

## Scope

Rein Frontend. Keine Backend- oder Datenbankänderungen nötig.

## Verhalten

### Neue UI-Sektion im Modal

Unterhalb des Routing-Blocks, oberhalb des GeoJSON-Uploads, erscheint:

```
── Betriebsstellen hinzufügen ──
[Suchfeld — Station suchen…]
● Frankfurt Hbf  ✕
● Mannheim Hbf  ✕
```

- Auswahl einer Station im Dropdown fügt sie sofort zur Liste hinzu
- Jeder Eintrag hat einen Entfernen-Button (×)
- Punkte werden auf der Karte als orange Circles (Preview) angezeigt

### handleAccept-Logik

Der `deleteExisting`-Toggle gilt für alle Geometrie-Typen gleich.

```
neue Geometrie = Route-LineString (falls vorhanden) + ausgewählte Punkte (falls vorhanden)

if (!hasExisting || deleteExisting) && neue Geometrie vorhanden:
    → geojson_representation = FeatureCollection { features: [LineString Feature?, ...Point Features] }

if !hasExisting && nur Punkte:
    → geojson_representation = FeatureCollection { features: [...Point Features] }

if deleteExisting && keine neue Geometrie:
    → geojson_representation = null  (bisheriges Verhalten)
```

### Point-Feature-Format

```json
{
  "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [lon, lat] },
  "properties": { "name": "Frankfurt Hbf", "op_id": "FFM", "feature_type": "operational_point" }
}
```

### Karte

- Bestehende Points (aus existingGeojson, falls FeatureCollection) → blaue Circles
- Preview-Punkte (neu ausgewählt) → orange Circles
- Bounds-Fitting berücksichtigt auch Punkte

## Akzeptanzkriterien

- [ ] Suchfeld im Modal findet Betriebsstellen (selbe API wie Routing-Formular)
- [ ] Ausgewählte Punkte erscheinen als Liste mit Entfernen-Button
- [ ] Punkte werden als orange Circles auf der Vorschau-Karte angezeigt
- [ ] Beim Bestätigen werden Punkte + ggf. Routing-Linie als FeatureCollection gespeichert
- [ ] `deleteExisting`-Toggle gilt für Punkte identisch wie für Linien
- [ ] Bestehende Punkte in existingGeojson werden als blaue Circles auf der Karte gezeigt

## Betroffene Dateien

| Datei | Änderung |
|---|---|
| `features/routing/StationSelect.tsx` | NEU — extrahiert aus RouteCalculatorForm |
| `features/routing/RouteCalculatorForm.tsx` | Import von StationSelect aus neuem File |
| `features/routing/GeometryManagementModal.tsx` | Neue Sektion, State, FeatureCollection-Logik |
| `features/routing/GeometryPreviewMap.tsx` | Circle-Layer für Preview- und Existing-Punkte |
