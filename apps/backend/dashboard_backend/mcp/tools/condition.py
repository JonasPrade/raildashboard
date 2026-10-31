"""InfraGO-Zustandsbericht tools (feature-zustandsbericht.md → "Import über
MCP + Skill").

An agent reads the report (page text, page images where the text is not
enough) and writes one table per call. The server checks the inner sums of
every table and refuses a write that breaks them, unless the agent says why
the report itself does not add up. Values written here are UNGEPRUEFT; a
person releases the year in the admin view. The skill
``.claude/skills/zustandsbericht-import`` holds the procedure. Every tool
requires ``condition.import``.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.mcpserver.utilities.types import Image
from pydantic import BaseModel, Field

from dashboard_backend.crud import condition as crud
from dashboard_backend.mcp.context import get_principal, require, tool_session
from dashboard_backend.mcp.tools.projects import READ_ONLY, WRITE
from dashboard_backend.services.condition_catalog import GRADE_LABELS, LAENDER, METRICS, SCOPE_LABELS
from dashboard_backend.services.infraplan_page_text import layout_text

PERMISSION = "condition.import"

Domain = Literal["FAHRWEG", "PERSONENBAHNHOF"]
Scope = Literal["GESAMT", "HLN", "FLN", "SE", "LAND"]
Metric = Literal[
    "WBW", "WBW_BEWERTET", "WBW_ANTEIL", "NOTE", "VERTEILUNG_WBW", "VERTEILUNG_MENGE",
    "MENGE_BEWERTET", "MENGE_GESAMT", "ERNEUERUNGSBEDARF_MENGE", "ERNEUERUNGSBEDARF_MRD",
    "NACHHOLBEDARF_MRD",
]


def _error(exc: Exception) -> ToolError:
    return ToolError(str(exc))


def _report(db, year: int):
    try:
        return crud.report_or_error(db, year)
    except crud.ConditionNotFoundError as exc:
        raise _error(exc) from exc


def _jsonable(report: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in report.items()}


def list_condition_reports(*, ctx: Context) -> dict[str, Any]:
    """Zustandsbericht years with status (ENTWURF | FREIGEGEBEN), whether a
    PDF is stored and how many values are written / still unchecked
    (requires ``condition.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {"reports": [_jsonable(r) for r in crud.list_reports(db)]}


def create_condition_report(
    year: int,
    title: str | None = None,
    source_url: str | None = None,
    published_on: date | None = None,
    price_basis: str | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Create the report of a year (requires ``condition.import``). The same
    year twice is refused with the existing id. The PDF is uploaded in the
    admin view (Admin → Zustandsbericht); page text/images need it."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    with tool_session(ctx) as db:
        try:
            report = crud.create_report(
                db, year=year, title=title, source_url=source_url, published_on=published_on,
                price_basis=price_basis, note=note, username=principal.username,
            )
        except crud.ConditionError as exc:
            raise _error(exc) from exc
        return _jsonable(crud.report_out(db, report))


def update_condition_report(
    year: int,
    title: str | None = None,
    source_url: str | None = None,
    published_on: date | None = None,
    price_basis: str | None = None,
    note: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Correct the metadata of an existing year (requires ``condition.import``)
    — e.g. the price basis of the annex tables when the year was created
    without it. Only the fields you pass change; the year itself cannot. A
    released year is refused — a person corrects it in the admin view."""
    require(get_principal(ctx), PERMISSION)
    changes = {
        field: value
        for field, value in (
            ("title", title),
            ("source_url", source_url),
            ("published_on", published_on),
            ("price_basis", price_basis),
            ("note", note),
        )
        if value is not None
    }
    if not changes:
        raise ToolError("Keine Änderung übergeben.")
    with tool_session(ctx) as db:
        report = _report(db, year)
        if report.status == "FREIGEGEBEN":
            raise ToolError(
                f"Der Zustandsbericht {year} ist freigegeben — Korrekturen macht ein Mensch in der Admin-Ansicht."
            )
        try:
            report = crud.update_report(db, report, changes)
        except crud.ConditionError as exc:
            raise _error(exc) from exc
        return _jsonable(crud.report_out(db, report))


def get_condition_page_text(year: int, page: int, *, ctx: Context) -> dict[str, Any]:
    """Text of one PDF page with its layout (requires ``condition.import``):
    one line per text line, ``"<top>: word@x word@x …"`` (points from the top,
    word centre). Table columns line up by x — read the annex tables (Tab. 5–7)
    column by column. ``page`` is the PDF page (the report prints two pages on
    one PDF page)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        report = _report(db, year)
        try:
            words = crud.page_words(report, page)
        except crud.ConditionNotFoundError as exc:
            raise _error(exc) from exc
    return {"year": year, "page": page, "lines": layout_text(words)}


def get_condition_page_image(year: int, page: int, dpi: int = 110, *, ctx: Context) -> Image:
    """One PDF page as image (requires ``condition.import``) — for charts and
    the Länder map, where the text alone does not say which number belongs
    where. dpi 50–200."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        report = _report(db, year)
        try:
            png = crud.render_page(report, page, max(50, min(dpi, 200)))
        except crud.ConditionNotFoundError as exc:
            raise _error(exc) from exc
    return Image(data=png, format="png")


def list_condition_classes(domain: Domain | None = None, *, ctx: Context) -> dict[str, Any]:
    """Asset classes (stable key, name, unit, trade) plus the allowed metrics,
    scopes, Länder and grades — use these keys in set_condition_values
    (requires ``condition.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return {
            "classes": [crud.class_out(c) for c in crud.list_classes(db, domain)],
            "metrics": {k: {"unit": unit, "per_grade": graded} for k, (unit, graded) in METRICS.items()},
            "scopes": SCOPE_LABELS,
            "laender": LAENDER,
            "grades": GRADE_LABELS,
        }


def create_condition_class(
    key: str,
    domain: Domain,
    name: str,
    unit: str | None,
    reason: str,
    trade: Literal["KIB", "OB", "LST", "ET"] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Add an asset class the report has but list_condition_classes lacks
    (requires ``condition.import``). Stable snake_case key with prefix fw_ or
    pb_; ``reason`` names where the report introduces it."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        try:
            record = crud.create_class(
                db, key=key, domain=domain, name=name, unit=unit, trade=trade, description=reason
            )
        except crud.ConditionError as exc:
            raise _error(exc) from exc
        return crud.class_out(record)


class ConditionValueInput(BaseModel):
    """class_key = asset class (omit for the total of the table); grade 1–6
    only for VERTEILUNG_WBW / VERTEILUNG_MENGE; reference_year defaults to the
    report year (previous-year columns: the year before); value null removes
    the slot; source_page = PDF page; source_ref e.g. "Tab. 5", "Abb. 31"."""

    class_key: str | None = None
    metric: Metric
    grade: int | None = Field(default=None, ge=1, le=6)
    reference_year: int | None = None
    value: float | None
    source_page: int | None = None
    source_ref: str | None = Field(default=None, max_length=50)


def set_condition_values(
    year: int,
    domain: Domain,
    scope: Scope,
    values: list[ConditionValueInput],
    region: str | None = None,
    override_reason: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Write the values of ONE table — domain × scope (× region for LAND) —
    all or nothing (requires ``condition.import``). The server checks the
    table with what is already stored: grade distribution = 100 %, quantities
    per grade = rated quantity, grades 4–6 = Erneuerungsbedarf, classes =
    total. A failed check writes nothing and lists the errors: re-read the
    page. Only if the report itself does not add up (the printed numbers are
    what you sent), repeat with ``override_reason`` naming the page and the
    mismatch — it is recorded on the report and shown at release. Values
    stay UNGEPRUEFT until a person releases the year."""
    principal = get_principal(ctx)
    require(principal, PERMISSION)
    if not values:
        raise ToolError("Keine Werte übergeben.")
    with tool_session(ctx) as db:
        report = _report(db, year)
        if report.status == "FREIGEGEBEN":
            raise ToolError(
                f"Der Zustandsbericht {year} ist freigegeben — Korrekturen macht ein Mensch in der Admin-Ansicht."
            )
        try:
            return crud.set_values(
                db,
                report,
                domain=domain,
                scope=scope,
                region=region,
                values=[v.model_dump() for v in values],
                status="UNGEPRUEFT",
                username=principal.username,
                override_reason=override_reason,
            )
        except crud.ConditionError as exc:
            raise _error(exc) from exc


def get_condition_values(
    year: int,
    domain: Domain | None = None,
    scope: Scope | None = None,
    metric: Metric | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Stored values of a year, optionally filtered — e.g. to compare with the
    previous year before writing (requires ``condition.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        report = _report(db, year)
        return {
            "year": year,
            "values": crud.report_values(db, report, domain=domain, scope=scope, metric=metric),
        }


def check_condition_report(year: int, *, ctx: Context) -> dict[str, Any]:
    """All checks over the year again, the accepted mismatches and what is
    still missing (annex tables, Länder) — call it before reporting back
    (requires ``condition.import``)."""
    require(get_principal(ctx), PERMISSION)
    with tool_session(ctx) as db:
        return crud.check_report(db, _report(db, year))


def register(server: MCPServer) -> None:
    for fn in (
        list_condition_reports,
        get_condition_page_text,
        get_condition_page_image,
        list_condition_classes,
        get_condition_values,
        check_condition_report,
    ):
        server.add_tool(fn, annotations=READ_ONLY)
    for fn in (
        create_condition_report,
        update_condition_report,
        create_condition_class,
        set_condition_values,
    ):
        server.add_tool(fn, annotations=WRITE)
