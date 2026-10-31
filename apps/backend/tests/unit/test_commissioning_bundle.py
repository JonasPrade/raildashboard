"""Commissioning of a project over all its parts (#344).

feature-project-timeline.md → „Oberprojekte schließen alle Teilabschnitte ein“.
"""

from __future__ import annotations

from datetime import date

from dashboard_backend.models.projects.progress_enums import DatePrecision, MainPhase
from dashboard_backend.services.progress_forecast import (
    PENDING_SOURCE,
    CommissioningParts,
    ConcreteDate,
    ExpectedDate,
    PartCommissioning,
    PendingPart,
    PfaForecastInput,
    build_forecast,
    bundle_commissioning,
)
from dashboard_backend.services.progress_timeline import (
    KIND_PART_IBN,
    KIND_PHASE,
    ConstructionUnitInput,
    build_timeline,
)

TODAY = date(2026, 10, 31)

STAGE_1 = PartCommissioning(
    name="Baustufe 1a",
    date=ConcreteDate(date=date(2017, 12, 15), source="VIB-PFA", precision=DatePrecision.MONTH),
)
OPEN = (
    PendingPart(name="Teilmaßnahme 1", project_id=1, phase=MainPhase.GENEHMIGUNGSPLANUNG),
    PendingPart(name="Bahnhof Julbach", project_id=2, phase=None),
)


def _bundle(**kwargs) -> dict[MainPhase, ConcreteDate]:
    concrete = {MainPhase.IN_BETRIEB: STAGE_1.date}
    return bundle_commissioning(concrete, CommissioningParts(**kwargs), TODAY)


def test_without_open_parts_the_latest_known_date_stays():
    result = _bundle(parts=(STAGE_1,), pending=())
    assert result[MainPhase.IN_BETRIEB] == STAGE_1.date


def test_open_parts_turn_a_past_stage_into_a_lower_bound():
    """Mühldorf–Freilassing: Baustufe 1a/1b in service 12/2017, the rest open."""

    ibn = _bundle(parts=(STAGE_1,), pending=OPEN)[MainPhase.IN_BETRIEB]
    assert ibn.precision is DatePrecision.NOT_BEFORE
    assert ibn.date == date(2027, 1, 1)  # „nach 2026“
    assert ibn.source == PENDING_SOURCE
    assert ibn.partial == STAGE_1.date
    assert [p.name for p in ibn.pending] == ["Teilmaßnahme 1", "Bahnhof Julbach"]
    assert "2 Abschnitte ohne Inbetriebnahme" in ibn.derivation


def test_bound_follows_a_later_known_part():
    later = PartCommissioning(
        name="Baustufe 2", date=ConcreteDate(date=date(2030, 12, 31), source="VIB-PFA")
    )
    ibn = _bundle(parts=(STAGE_1, later), pending=OPEN)[MainPhase.IN_BETRIEB]
    assert ibn.date == date(2031, 1, 1)  # „nach 2030“
    assert ibn.partial is None  # the latest part is not in service yet


def test_overall_date_of_the_parent_replaces_the_bound():
    overall = ConcreteDate(date=date(2035, 12, 31), source="Fulda-Runde", precision=DatePrecision.YEAR)
    ibn = _bundle(parts=(STAGE_1,), pending=OPEN, overall=overall)[MainPhase.IN_BETRIEB]
    assert (ibn.date, ibn.source, ibn.precision) == (overall.date, "Fulda-Runde", DatePrecision.YEAR)
    assert ibn.pending == OPEN


def test_overall_date_never_earlier_than_the_latest_part():
    later = PartCommissioning(
        name="Baustufe 2", date=ConcreteDate(date=date(2030, 12, 31), source="VIB-PFA")
    )
    overall = ConcreteDate(date=date(2028, 12, 31), source="Infraplan")
    ibn = _bundle(parts=(later,), pending=OPEN, overall=overall)[MainPhase.IN_BETRIEB]
    assert ibn.date == date(2030, 12, 31)
    assert "liegt vor der spätesten Teil-Inbetriebnahme" in ibn.derivation


def test_manual_date_of_the_project_always_wins():
    result = _bundle(parts=(STAGE_1,), pending=OPEN, has_manual=True)
    assert result[MainPhase.IN_BETRIEB] == STAGE_1.date


def test_open_parts_alone_invent_no_commissioning():
    concrete: dict[MainPhase, ConcreteDate] = {}
    assert bundle_commissioning(concrete, CommissioningParts(pending=OPEN), TODAY) == {}


def test_a_dated_commissioning_without_parts_is_pulled_back():
    """E.g. a superior's own Infraplan year is weighed as a section date."""

    concrete = {MainPhase.IN_BETRIEB: ConcreteDate(date=date(2019, 12, 15), source="VIB-PFA")}
    ibn = bundle_commissioning(concrete, CommissioningParts(pending=OPEN), TODAY)[MainPhase.IN_BETRIEB]
    assert ibn.date == date(2027, 1, 1)
    assert ibn.partial is None  # no known part to mark


def test_forecast_no_longer_reports_an_overdue_date():
    """A past Baubeginn of a project still in planning is one part's start."""

    result = build_forecast(
        effective_phase=MainPhase.GENEHMIGUNGSPLANUNG,
        today=TODAY,
        pfas=[PfaForecastInput(baubeginn=date(2002, 8, 10), inbetriebnahme=date(2017, 12, 15))],
        commissioning_parts=CommissioningParts(parts=(STAGE_1,), pending=OPEN),
    )
    steps = {s.phase: s for s in result.next_steps}
    assert steps[MainPhase.BAU].precision is DatePrecision.NOT_BEFORE
    assert "weitere Abschnitte offen" in steps[MainPhase.BAU].derivation
    assert steps[MainPhase.IN_BETRIEB].precision is DatePrecision.NOT_BEFORE
    assert result.remaining_text == "Ende der aktuellen Phase offen (nach 2026)"
    assert "überschritten" not in result.remaining_text
    # The list cache keeps the real first Baubeginn.
    assert result.concrete[MainPhase.BAU].date == date(2002, 8, 10)


def test_timeline_marks_the_partial_commissioning():
    result = build_timeline(
        today=TODAY,
        pfas=[PfaForecastInput(baubeginn=date(2002, 8, 10), inbetriebnahme=date(2017, 12, 15))],
        commissioning_parts=CommissioningParts(parts=(STAGE_1,), pending=OPEN),
    )
    (part,) = [m for m in result.milestones if m.kind == KIND_PART_IBN]
    assert part.date == date(2017, 12, 15)
    (ibn,) = [m for m in result.milestones if m.kind == KIND_PHASE and m.phase is MainPhase.IN_BETRIEB]
    assert ibn.precision is DatePrecision.NOT_BEFORE
    assert [p.name for p in result.pending_parts] == ["Teilmaßnahme 1", "Bahnhof Julbach"]


def test_open_parts_keep_the_gap_between_construction_stages():
    """HLK 11 with an undated third subproject: the stages stay separate."""

    def unit(start, end):
        return ConstructionUnitInput(
            manual_expected=[
                ExpectedDate(phase=MainPhase.BAU, date=start),
                ExpectedDate(phase=MainPhase.IN_BETRIEB, date=end),
            ]
        )

    result = build_timeline(
        today=TODAY,
        manual_expected=[
            ExpectedDate(phase=MainPhase.BAU, date=date(2028, 1, 1)),
            ExpectedDate(phase=MainPhase.IN_BETRIEB, date=date(2031, 7, 1)),
        ],
        construction_units=[
            unit(date(2028, 1, 1), date(2028, 7, 1)),
            unit(date(2031, 1, 1), date(2031, 7, 1)),
            ConstructionUnitInput(),
        ],
        commissioning_parts=CommissioningParts(
            parts=(
                PartCommissioning(name="11-2", date=ConcreteDate(date=date(2031, 7, 1), source="Manuell")),
            ),
            pending=(PendingPart(name="11-3", project_id=3, phase=None),),
        ),
    )
    assert result.construction_periods == [
        (date(2028, 1, 1), date(2028, 7, 1)),
        (date(2031, 1, 1), date(2031, 7, 1)),
    ]
    (ibn,) = [m for m in result.milestones if m.kind == KIND_PHASE and m.phase is MainPhase.IN_BETRIEB]
    assert ibn.precision is DatePrecision.NOT_BEFORE
