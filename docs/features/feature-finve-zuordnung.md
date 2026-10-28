# Feature: FinVe-Zuordnung bearbeiten

## Goal

The link between a FinVe (Finanzierungsvereinbarung) and its projects can be
changed afterwards — projects added **and removed**, also for FinVes that are
already assigned. Until now links could only be added (open assignments, the
new-project wizard, the Haushalt import review); a wrong link such as FinVe
900008 („Baustufen I + II Digitaler Knoten Stuttgart“) on project 2221
(Gäubahn Abschnitt Nord) created a construction observation from 2020 and could
not be removed anywhere.

## Scope

Three places edit the same links through one backend function:

1. **MCP** — tool `update_finve_projects(finve_id, add_project_ids, remove_project_ids, note)`.
2. **Project page** — the FinVe section shows „Zuordnung entfernen“ per own FinVe
   and „FinVe hinzufügen“ (search by number or name).
3. **FinVe overview** (`/finanzen/bedarfsplan`) — „Projekte bearbeiten“ per FinVe
   opens a drawer with the linked projects (remove) and a project search (add).

Only **permanent links** (`finve_to_project.haushalt_year IS NULL`) are edited.
Year-scoped links of Sammel-FinVes come from the Haushalt import, record which
project a Sammel-FinVe financed in which year and stay untouched; they are shown
but cannot be removed here.

**Archived projects** (`feature-project-archive.md`): archiving requires a project
without permanent FinVe links, so adding a FinVe to an archived project is refused
(409). Sammel-FinVe year links do not block archiving (W5a): they stay on the
archived project as history, are listed last and marked „archiviert“ in the FinVe
overview and drawer, and no longer count (`project_count`, `project_names`).

## Behaviour

- `crud/finve_links.py` → `update_finve_projects(db, finve_id, add, remove, user)`
  is the only write path for permanent links outside the Haushalt import. It
  - validates that the FinVe and every added project exist,
  - adds/removes permanent links (adding an existing link or removing a missing
    one is a no-op),
  - writes one project changelog entry per affected project: field `finve_ids`,
    old/new value = sorted list of the project's **permanent** FinVe ids,
  - commits, then recomputes the planning state (`recompute_progress`) of every
    affected project — FinVes are lower bounds of the planning state, a removed
    link must drop its observation at once.
- The existing add-only paths use it too (decision W4): `PATCH
  /admin/unassigned-finves/{id}/assign` and `POST /projects/{id}/finves`
  (new-project wizard). Every link change is therefore logged and recomputed.
- **Revert:** a `finve_ids` changelog entry can be reverted from the project
  history like any field; the revert sets the project's permanent FinVe links
  back to the old list (again logged and recomputed).
- **Parent projects** (decision W3): the project page lists FinVes inherited from
  sub-projects („aus Teilprojekt …“) but only offers „Zuordnung entfernen“ on the
  project's own links — the hint links to the sub-project where the link lives.
- **Haushalt import** (decision W1): the confirm step applies only the reviewer's
  *changes* to the permanent links — the difference between the project list at
  parse time and the submitted list — instead of overwriting the links with the
  parse-time snapshot. A link removed by hand between parse and confirm stays
  removed; a link the reviewer removes in the review is removed. Sammel-FinVe
  year links keep their set-sync per year.

## API

| Method | Path | Permission | Body / Result |
|---|---|---|---|
| PATCH | `/api/v1/finves/{finve_id}/projects` | `finve.edit` | `{add_project_ids, remove_project_ids}` → `FinveProjectsSchema {finve_id, projects: [{id, name}]}` (permanent links) |

Permission (decision W2): `finve.edit` („Finanzierungsvereinbarungen
einarbeiten“) guards every edit of FinVe links — the new endpoint, the MCP tool,
the wizard endpoint and the revert of a `finve_ids` entry. `assignment.manage`
keeps guarding the list of open assignments and its assign button.

## MCP

`update_finve_projects` (annotation WRITE, requires `finve.edit`) replaces the
earlier tool `unlink_finve` (decided 2026-10-23: one logged write path; unlike
`unlink_finve` it keeps Sammel-FinVe year links and needs `finve.edit`). `note` is a
free reason kept in the tool result (the changelog has no comment column).
Returns the FinVe's permanent projects afterwards and the recomputed project ids.

## Acceptance criteria

- [ ] A FinVe link can be added and removed via MCP, on the project page and in
      the FinVe overview.
- [ ] After a removal the planning state of the project no longer contains the
      FinVe observation.
- [ ] Each change appears in the project history as „FinVe-Zuordnung“ with FinVe
      numbers and can be reverted.
- [ ] Sammel-FinVe year links are neither shown as removable nor changed.
- [ ] A Haushalt confirm does not bring back a link removed after the parse.
- [ ] `make test` green.

## Decisions

| # | Date | Decision |
|---|---|---|
| W1 | 2026-10-23 | Haushalt confirm applies only the reviewer's delta to permanent links (a) |
| W2 | 2026-10-23 | Permission `finve.edit` for all link edits (a) |
| W3 | 2026-10-23 | Remove only own links; inherited ones show a hint (a); archived projects → task Nr. 75 |
| W4 | 2026-10-23 | Existing assign paths use the new function (logged + recomputed) (a) |
| W5 | 2026-10-23 | `update_finve_projects` replaces the parallel MCP tool `unlink_finve`; task Nr. 75 closed (archiving excludes FinVe links) |
