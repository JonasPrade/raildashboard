"""fix the imported GVFG edition 2023–2027 in place

The first import of the 2023 programme ran before the parser handled the
typos of that PDF (docs/features/feature-gvfg-import.md → "Druckfehler im
Kopf (2023)"). This writes what the fixed parser reads from the same PDF, so
the edition does not have to be uploaded and reviewed again:

- year columns: "1967–2020" (p. 41, 44) is "1967–2021", "2022" (p. 42) is
  "vsl. 2022" — renamed in every amount line, dropped from the edition
- 16 D 4520_A: the aid total was not read (header split over two cells)
- 09 G 7034_A: the C line was lost ("Kat: C")
- 03 D 4505_A: missing entirely (key printed without underscore); it is
  linked to the projects of the same key in the newest other edition

Nothing happens without an imported 2023 edition. Data only, no schema
change; the downgrade leaves the corrected data in place.

Revision ID: 20261022002
Revises: 20261022001
Create Date: 2026-10-22
"""

from alembic import op
import sqlalchemy as sa

revision = "20261022002"
down_revision = "20261022001"
branch_labels = None
depends_on = None

YEAR_FROM = 2023
ALIASES = {"1967–2020": "1967–2021", "2022": "vsl. 2022"}

_LABELS = ("1967–2021", "vsl. 2022", "2023", "2024", "2025", "2026", "2027", "ab 2028")


def _periods(*values: str) -> dict[str, str]:
    return dict(zip(_LABELS, values))


_ZERO = _periods(*["0.00"] * 8)


def _line(category: str, cost: str, eligible: str, aid: str, periods: dict[str, str]) -> dict:
    return {
        "category": category,
        "cost_total": cost,
        "cost_eligible": eligible,
        "aid_total": aid,
        "periods": periods,
    }


# Amount lines as the fixed parser reads them from the PDF (∑, A, C).
LINES = {
    "16 D 4520_A": [
        _line("SUM", "140.00", "115.00", "86.25", _periods(*["0.00"] * 5, "2.75", "5.00", "78.50")),
        _line("A", "0.00", "0.00", "0.00", _ZERO),
        _line("C", "140.00", "115.00", "86.25", _periods(*["0.00"] * 5, "2.75", "5.00", "78.50")),
    ],
    "09 G 7034_A": [
        _line("SUM", "59.05", "53.15", "26.58", _periods(*["0.00"] * 5, "0.50", "0.50", "25.58")),
        _line("A", "0.00", "0.00", "0.00", _ZERO),
        _line("C", "59.05", "53.15", "26.58", _periods(*["0.00"] * 5, "0.50", "0.50", "25.58")),
    ],
    "03 D 4505_A": [
        _line("SUM", "15.00", "13.50", "10.13", _periods(*["0.00"] * 5, "0.50", "1.00", "8.63")),
        _line("A", "0.00", "0.00", "0.00", _ZERO),
        _line("C", "15.00", "13.50", "10.13", _periods(*["0.00"] * 5, "0.50", "1.00", "8.63")),
    ],
}

MISSING_ENTRY = {
    "key": "03 D 4505_A",
    "key_raw": "03 D 4505 A",
    "land": "Niedersachsen",
    "kind": "db",
    "part": "finanzrelevant",
    "nr": "5",
    "name": "Braunschweig Hbf - BS/Gliesmarode",
    "funding_type": "Kapazitätserhöhung",
    "funding_rate": 75,
    "start_year": 2026,
    "construction_start": 2026,
    "page": 11,
}

program_t = sa.table(
    "gvfg_program", sa.column("id", sa.Integer), sa.column("year_from", sa.Integer), sa.column("periods", sa.JSON)
)
entry_t = sa.table(
    "gvfg_entry",
    sa.column("id", sa.Integer),
    sa.column("program_id", sa.Integer),
    *(sa.column(name) for name in MISSING_ENTRY),
)
amount_t = sa.table(
    "gvfg_entry_amount",
    sa.column("id", sa.Integer),
    sa.column("entry_id", sa.Integer),
    sa.column("line_no", sa.Integer),
    sa.column("category", sa.String),
    sa.column("computed", sa.Boolean),
    sa.column("cost_total", sa.Numeric),
    sa.column("cost_eligible", sa.Numeric),
    sa.column("aid_total", sa.Numeric),
    sa.column("periods", sa.JSON),
)
link_t = sa.table("gvfg_entry_project", sa.column("entry_id", sa.Integer), sa.column("project_id", sa.Integer))


def fix_edition(bind) -> None:
    program = bind.execute(
        sa.select(program_t.c.id, program_t.c.periods).where(program_t.c.year_from == YEAR_FROM)
    ).one_or_none()
    if program is None:
        return
    program_id = program.id
    bind.execute(
        program_t.update()
        .where(program_t.c.id == program_id)
        .values(periods=[p for p in program.periods or [] if p["label"] not in ALIASES])
    )

    entry_ids = sa.select(entry_t.c.id).where(entry_t.c.program_id == program_id)
    for amount_id, periods in bind.execute(
        sa.select(amount_t.c.id, amount_t.c.periods).where(amount_t.c.entry_id.in_(entry_ids))
    ):
        if any(label in ALIASES for label in periods or {}):
            renamed = {ALIASES.get(label, label): value for label, value in periods.items()}
            bind.execute(amount_t.update().where(amount_t.c.id == amount_id).values(periods=renamed))

    entry_by_key = dict(
        bind.execute(
            sa.select(entry_t.c.key, entry_t.c.id).where(
                entry_t.c.program_id == program_id, entry_t.c.key.in_(LINES)
            )
        ).all()
    )
    if MISSING_ENTRY["key"] not in entry_by_key:
        entry_id = bind.execute(
            entry_t.insert().values(program_id=program_id, **MISSING_ENTRY).returning(entry_t.c.id)
        ).scalar_one()
        entry_by_key[MISSING_ENTRY["key"]] = entry_id
        # The projects of the same key in the newest other edition that links it.
        newest = (
            sa.select(program_t.c.year_from)
            .join(entry_t, entry_t.c.program_id == program_t.c.id)
            .join(link_t, link_t.c.entry_id == entry_t.c.id)
            .where(entry_t.c.key == MISSING_ENTRY["key"], program_t.c.id != program_id)
            .order_by(program_t.c.year_from.desc())
            .limit(1)
            .scalar_subquery()
        )
        project_ids = bind.execute(
            sa.select(link_t.c.project_id.distinct())
            .join(entry_t, entry_t.c.id == link_t.c.entry_id)
            .join(program_t, program_t.c.id == entry_t.c.program_id)
            .where(entry_t.c.key == MISSING_ENTRY["key"], program_t.c.year_from == newest)
        ).scalars().all()
        for project_id in project_ids:
            bind.execute(link_t.insert().values(entry_id=entry_id, project_id=project_id))

    for key, lines in LINES.items():
        entry_id = entry_by_key.get(key)
        if entry_id is None:
            continue
        bind.execute(amount_t.delete().where(amount_t.c.entry_id == entry_id))
        for line_no, line in enumerate(lines):
            bind.execute(amount_t.insert().values(entry_id=entry_id, line_no=line_no, computed=False, **line))


def upgrade() -> None:
    fix_edition(op.get_bind())


def downgrade() -> None:
    # The corrected rows are what the PDF says; there is nothing to restore.
    pass
