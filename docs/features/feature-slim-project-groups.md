# Feature: Slim project-group list with lazily loaded geometries

**Goal:** The map page loads fast. `GET /api/v1/project_groups/` was ~8 MB of JSON
(TTFB 0.82 s in production) because every group embedded the full `ProjectSchema`
of each of its projects — including `geojson_representation`, the full-resolution
geometry as an escaped JSON string. The list now carries metadata only; geometries
are loaded separately, simplified, per selected group.

## Cause (analysis)

- `geojson_representation` dominates each project row. It was sent as a string
  (every quote escaped) with full float precision.
- Geometry was **multiplied**: a parent project's geometry is the aggregated
  FeatureCollection of its subprojects (`recompute_geojson_for_parent`), so every
  child geometry was sent again with each ancestor — and a project in *n* groups
  was serialised *n* times.
- ~60 scalar fields per project, `justification`, `centroid` (a Shapely
  conversion per row) and `project_groups` refs were sent although the map uses
  a handful of them.
- Queries were already fine (no N+1; `selectinload`), but the ORM loaded every
  column, geometry text included.
- No compression: the container nginx gzips, but not behind a proxy that
  forwards with HTTP/1.0 (nginx default `gzip_http_version 1.1`).

Consumers of the endpoint: `MapPage` (map + list tab), `GroupFilterDrawer`,
`ProjectGroupsAdminPage` (count only), project wizard / edit form (group id +
name only). No worker, task or external caller uses it; the old-DB import
scripts use the ORM directly.

## Scope

1. **Slim list.** `ProjectGroupSchema.projects` is `ProjectListItem[]`: `id`,
   `name`, `project_number`, `superior_project_id`, `description`, `length` and
   `active_features` (names of the boolean properties that are true). The CRUD
   query uses `load_only(..., raiseload=True)` so geometry is never loaded on
   this path. Same shape for `GET /project_groups/{id}`.
2. **Geometry endpoint.** `GET /api/v1/project_groups/{id}/geometries?only_superior=true|false`
   returns `{group_id, only_superior, tolerance, geometries: {project_id: FeatureCollection}}`.
   Per project: one MultiLineString (simplified, topology-preserving, tolerance
   0.0002° ≈ 20 m) and one MultiPoint (unchanged), coordinates rounded to 5
   decimals (≈ 1 m), 2D, properties dropped. Polygons are skipped — the map
   never rendered them. `only_superior=true` (map default) omits subprojects,
   whose geometry is already part of their parent's. Drafts are never included.
3. **Frontend.** The map and list render as soon as the list arrives;
   `useProjectGroupGeometries` loads geometries per selected group (one cached
   query per group, keys nested under `projectGroups`), with a small
   „Projektverläufe werden geladen…" hint. The list tab loads no geometry.
   The detail page keeps the exact geometry from `GET /projects/{id}`.
4. **GZip in the backend.** `GZipMiddleware(minimum_size=1024, compresslevel=6)`
   in `main.py`, PDFs/images excluded — works regardless of the proxy in front.
   Additionally `gzip_http_version 1.0` in `apps/frontend/nginx.conf` so the
   static assets (maplibre, vendor chunks) are compressed behind the host proxy.
5. **Caching: ETag, no Redis.** List, single group and geometries are sent with a
   content-hash `ETag` and `Cache-Control: no-cache`; an unchanged response is
   answered `304` without a body. Simplified geometries are memoised in-process,
   keyed by a hash of the source text.

   *Why not Redis:* a server-side response cache would need explicit
   invalidation on every write path that changes a group's projects (project
   edit, parent-geometry cascade, imports, group membership, drafts being
   finalised) — easy to miss one and serve stale maps. The slim list is cheap
   to build, and a content hash needs no invalidation at all.

## Out of scope

- Viewport-based (bbox) loading: needs a stored bbox per project (migration +
  hooks in every geometry write path); the start view shows all of Germany
  anyway, so it would not reduce the first load.
- Host nginx config and the published ports 5000/8989 in `docker-compose.yml`.
- The `public` flag of project groups is stored but not enforced anywhere
  (non-public groups are served to anonymous users) — unchanged here, noted for
  a separate decision.

## Acceptance criteria

- List response < 200 KB uncompressed, TTFB < 0.3 s.
- Map shows the same projects and geometries as before; detail view exact.
- `Content-Encoding: gzip` when the client sends `Accept-Encoding: gzip`.
- Tests cover the slim list, the geometry endpoint, ETag and gzip
  (`apps/backend/tests/api/test_project_group_slim_list.py`).

## Measurements

Synthetic dataset calibrated to production size (10 groups, 480 projects /
608 group rows, 120 parents with 3 subprojects, 150–350 vertices per line,
300-character descriptions on every project), SQLite, in-process client:

| | Before | After |
|---|---|---|
| `GET /project_groups/` uncompressed | 10.35 MB | 0.269 MB |
| … gzip on the wire | not compressed | 7.3 KB |
| … server time (median) | 103 ms | 36 ms |
| Geometries, all 10 groups, `only_superior=true` | (in the list) | 0.41 MB (136 KB gzip), 7 ms/group |
| Revalidation with `If-None-Match` | — | `304`, 0 bytes |

In this dataset ~190 KB of the 269 KB are descriptions; the production size
depends on the real description lengths. If the list stays above 200 KB there,
the next lever is sending a shortened description in the list.
