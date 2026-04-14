# Feature: Automatisches Zusammenführen der Parent-Geometrie

## Ziel

Wenn ein Projekt eine `geojson_representation` bekommt oder diese geändert wird, soll die
Geometrie aller übergeordneten Projekte automatisch neu berechnet werden. Ein Parent-Projekt
erhält stets eine `FeatureCollection`, die alle Features seiner Subprojekte (und deren
Subprojekte) enthält.

## Scope

- Betrifft ausschließlich das Backend (CRUD-Schicht).
- Kein eigener API-Endpunkt; die Logik wird beim PATCH eines Projekts als Seiteneffekt
  ausgeführt.
- Kein Frontend-Aufwand nötig; das Parent-Projekt gibt bereits sein `geojson_representation`
  aus der Datenbank zurück.

## Gewünschtes Verhalten

### Trigger
Immer wenn `geojson_representation` eines Projekts gesetzt oder verändert wird — unabhängig
davon, ob der Wert aus dem GeometryManagement-Modal, einem GeoJSON-Upload oder einem
Routing-Confirm stammt. Der einzige Einstiegspunkt ist `update_project` im CRUD.

### Merge-Algorithmus (pro Parent-Ebene)

1. Alle direkten Kinder des Parents laden (Projekte mit `superior_project_id == parent.id`).
2. Für jedes Kind mit vorhandener `geojson_representation`:
   - Ist es ein `Feature` → als einzelnes Feature übernehmen.
   - Ist es eine `FeatureCollection` → alle enthaltenen Features übernehmen (flatten).
   - Ist es eine rohe Geometry (kein `type: Feature/FeatureCollection`) → in ein Feature wrappen.
3. Alle gesammelten Features zu einer `FeatureCollection` zusammenfassen.
4. Haben **keine** Kinder eine Geometrie → `geojson_representation` des Parents auf `None` setzen.

### Rekursion (beliebige Verschachtelungstiefe)

Nach dem Update des Parents wird dieselbe Prozedur für den Parent-of-Parent aufgerufen,
bis kein übergeordnetes Projekt mehr existiert. Da jede Ebene die Geometrie ihrer direkten
Kinder zusammenfasst (und die bereits aufbereitete `FeatureCollection` eines Kindes dessen
gesamten Teilbaum enthält), ergibt sich korrekte Aggregation über alle Ebenen.

### Subprojekte ohne Geometrie

Werden ignoriert; sie tragen keine Features bei.

### Eigene Geometrie eines Parent-Projekts

Ein Parent-Projekt hat **keine** eigene, manuell gepflegte Geometrie. Die
`geojson_representation` eines Projekts mit Subprojekten wird **immer** aus seinen Kindern
berechnet und überschrieben. Setzt man `geojson_representation` eines Projekts direkt, das
selbst `superior_project_id` hat, läuft die Kaskade aber genauso aufwärts.

## Akzeptanzkriterien

- [ ] Ändert man die Geometrie eines Subprojekts via PATCH, hat das übergeordnete Projekt
      danach eine `FeatureCollection` seiner Kinder.
- [ ] Mehrfach verschachtelte Projekte (Grandchild → Child → Parent) werden korrekt aggregiert.
- [ ] Subprojekte ohne Geometrie werden ignoriert; vorhandene Kinder-Features bleiben erhalten.
- [ ] Hat kein Kind eine Geometrie, ist `geojson_representation` des Parents `None`.
- [ ] Die Kaskade läuft synchron im selben DB-Request.

## Technische Notizen

### Neue CRUD-Funktion `recompute_parent_geojson(db, project)`

```
def recompute_parent_geojson(db, project):
    if project.superior_project_id is None:
        return
    parent = get_project_by_id(db, project.superior_project_id)
    if parent is None:
        return
    children = db.query(Project).filter(
        Project.superior_project_id == parent.id
    ).all()
    features = []
    for child in children:
        features.extend(_extract_features(child.geojson_representation))
    if features:
        parent.geojson_representation = json.dumps({
            "type": "FeatureCollection",
            "features": features,
        })
    else:
        parent.geojson_representation = None
    db.commit()
    db.refresh(parent)
    recompute_parent_geojson(db, parent)   # recurse upwards
```

### Änderungen an `update_project`

Am Ende von `update_project`, nachdem `db.commit()` + `db.refresh()` abgeschlossen sind,
wird `recompute_parent_geojson(db, project)` aufgerufen — aber **nur** wenn
`geojson_representation` im `update_data` enthalten war.

### Betroffene Dateien

| Datei | Änderung |
|---|---|
| `crud/projects/projects.py` | `recompute_parent_geojson` hinzufügen, in `update_project` aufrufen |

Keine Migrationen nötig (kein Schemaänderung).
