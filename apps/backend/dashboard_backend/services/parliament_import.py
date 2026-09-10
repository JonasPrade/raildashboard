"""Import of constituencies and members of parliament.

Two data sources, two very different rates of change:

* **Constituency outlines** — Bundeswahlleiterin (© GeoBasis-DE / BKG), once per
  election. Imported from a GeoJSON file by ``scripts/import_constituencies.py``.
* **Members of parliament** — abgeordnetenwatch API v2 (CC0). Substitutes moving
  up and committee reshuffles change this constantly, so a rerun has to be cheap:
  four paged endpoints, then an upsert over a few thousand rows.

Both are idempotent: everything is matched on the source's own id, nothing is
deleted that the source still knows about.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Iterator

from sqlalchemy.orm import Session

from dashboard_backend.models.parliament import (
    COMMITTEE_KEY_BUDGET,
    COMMITTEE_KEY_TRANSPORT,
    COMMITTEE_LABELS,
    IMPORT_KIND_CONSTITUENCIES,
    IMPORT_KIND_POLITICIANS,
    IMPORT_STATUS_ERROR,
    IMPORT_STATUS_RUNNING,
    IMPORT_STATUS_SUCCESS,
    Committee,
    CommitteeMembership,
    Constituency,
    Mandate,
    ParliamentImportRun,
    ParliamentPeriod,
    Politician,
    role_label,
    role_rank,
)
from dashboard_backend.models.parliament.mandate import MANDATE_TYPE_CONSTITUENCY

API_BASE = "https://www.abgeordnetenwatch.de/api/v2"
PAGE_SIZE = 100
# abgeordnetenwatch parliament id of the Bundestag.
BUNDESTAG_PARLIAMENT_ID = 5

# Soft hyphens in faction labels ("BÜND­NIS 90") break every name comparison;
# they are stripped on import, not on read.
SOFT_HYPHEN = "\u00ad"

# "bl" in the ZeitOnline mirror is the two-digit Land key of the Amtlicher
# Gemeindeschlüssel; the original Bundeswahlleiterin file ships LAND_NAME.
LAND_NAMES: dict[str, str] = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Württemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}


# --- pure helpers -----------------------------------------------------------


def constituency_number_from_label(constituency: dict[str, Any] | None) -> int | None:
    """``"14 - Rostock – Landkreis Rostock II (Bundestag …)"`` → ``14``.

    The number is the key both sources agree on, and it lives only in the label —
    the ``constituency`` object of a mandate carries no ``number`` field.
    """
    if not constituency:
        return None
    label = constituency.get("label")
    if not isinstance(label, str):
        return None
    head = label.split(" - ", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def clean_fraction_label(label: str | None) -> str | None:
    """Faction label without the parenthesised period and without soft hyphens."""
    if not label:
        return None
    return label.split(" (")[0].replace(SOFT_HYPHEN, "").strip() or None


def current_fraction_label(fraction_membership: Iterable[dict[str, Any]] | None) -> str | None:
    """The running membership if there is one, else the last one seen."""
    label: str | None = None
    for membership in fraction_membership or []:
        fraction = membership.get("fraction") or {}
        candidate = clean_fraction_label(fraction.get("label"))
        if candidate:
            label = candidate
        if membership.get("valid_until") is None and label:
            break
    return label


def split_name(politician: dict[str, Any]) -> tuple[str | None, str | None]:
    first = politician.get("first_name")
    last = politician.get("last_name")
    if first or last:
        return first, last
    label = politician.get("label") or ""
    parts = label.split()
    if not parts:
        return None, None
    return " ".join(parts[:-1]) or None, parts[-1]


def _parse_date(value: Any) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def land_name(properties: dict[str, Any]) -> str | None:
    for key in ("LAND_NAME", "land_name", "bundesland", "state"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key in ("bl", "BL", "LAND_NR", "land_nr"):
        value = properties.get(key)
        if value is None:
            continue
        return LAND_NAMES.get(str(value).zfill(2))
    return None


def constituency_properties(properties: dict[str, Any]) -> tuple[int | None, str | None]:
    """Number and name from one GeoJSON feature, tolerant of both field sets.

    The ZeitOnline mirror uses ``wkr_id``/``name``; the Bundeswahlleiterin's own
    shapefile export uses ``WKR_NR``/``WKR_NAME``.
    """
    number = None
    for key in ("wkr_id", "WKR_NR", "wkr_nr", "number", "nummer"):
        value = properties.get(key)
        if value is None:
            continue
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        break
    name = None
    for key in ("name", "WKR_NAME", "wkr_name", "bezeichnung"):
        value = properties.get(key)
        if isinstance(value, str) and value.strip():
            name = value.strip()
            break
    return number, name


# --- API client -------------------------------------------------------------


class AbgeordnetenwatchClient:
    """Minimal client for the four endpoints this feature needs (CC0 data)."""

    def __init__(self, base_url: str = API_BASE, timeout: int = 90, retries: int = 4) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        url = self.base_url + path
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(url, timeout=self.timeout) as response:
                    return json.load(response)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt == self.retries - 1:
                    break
                time.sleep(2**attempt)
        raise RuntimeError(f"abgeordnetenwatch request failed: {url}") from last_error

    def paged(self, path: str, **params: Any) -> Iterator[dict[str, Any]]:
        start = 0
        while True:
            payload = self.get(path, range_start=start, range_end=PAGE_SIZE, **params)
            data = payload.get("data") or []
            yield from data
            if len(data) < PAGE_SIZE:
                return
            start += PAGE_SIZE


# --- import -----------------------------------------------------------------


@dataclass
class ImportStats:
    politicians: int = 0
    mandates: int = 0
    direct_mandates: int = 0
    constituencies_matched: int = 0
    constituencies_without_direct_mandate: int = 0
    committee_members: int = 0
    committees: dict[str, int] = field(default_factory=dict)
    mandates_without_constituency: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "politicians": self.politicians,
            "mandates": self.mandates,
            "direct_mandates": self.direct_mandates,
            "constituencies_matched": self.constituencies_matched,
            "constituencies_without_direct_mandate": self.constituencies_without_direct_mandate,
            "committee_members": self.committee_members,
            "committees": self.committees,
            "mandates_without_constituency": self.mandates_without_constituency,
        }


def _upsert_period(db: Session, payload: dict[str, Any]) -> ParliamentPeriod:
    external_id = int(payload["id"])
    period = (
        db.query(ParliamentPeriod)
        .filter(ParliamentPeriod.external_id == external_id)
        .one_or_none()
    )
    if period is None:
        period = ParliamentPeriod(external_id=external_id)
        db.add(period)
    period.label = payload.get("label") or f"Wahlperiode {external_id}"
    parliament = payload.get("parliament") or {}
    period.parliament_label = parliament.get("label")
    parliament_id = parliament.get("id")
    period.parliament_external_id = int(parliament_id) if parliament_id else None
    period.start_date = _parse_date(payload.get("start_date_period"))
    period.end_date = _parse_date(payload.get("end_date_period"))
    db.flush()
    # Exactly one period is the one the UI reads.
    db.query(ParliamentPeriod).filter(ParliamentPeriod.id != period.id).update(
        {ParliamentPeriod.is_current: False}, synchronize_session=False
    )
    period.is_current = True
    db.flush()
    return period


def _upsert_constituency_names(
    db: Session, period: ParliamentPeriod, rows: list[dict[str, Any]]
) -> dict[int, Constituency]:
    """Names and external ids for the 299 constituencies of *period*.

    Rows without a geometry are created here on purpose: the people side must
    work even before the outlines have been imported — the map layer is then
    empty, the names are not.
    """
    existing = {
        row.number: row
        for row in db.query(Constituency).filter(Constituency.parliament_period_id == period.id)
    }
    for row in rows:
        number = row.get("number")
        if number is None:
            continue
        number = int(number)
        constituency = existing.get(number)
        if constituency is None:
            constituency = Constituency(parliament_period_id=period.id, number=number)
            db.add(constituency)
            existing[number] = constituency
        constituency.name = row.get("name") or constituency.name or f"Wahlkreis {number}"
        constituency.external_id = int(row["id"]) if row.get("id") else constituency.external_id
    db.flush()
    return existing


def _upsert_politician(db: Session, cache: dict[int, Politician], payload: dict[str, Any]) -> Politician:
    external_id = int(payload["id"])
    politician = cache.get(external_id)
    if politician is None:
        politician = (
            db.query(Politician).filter(Politician.external_id == external_id).one_or_none()
        )
        if politician is None:
            politician = Politician(external_id=external_id)
            db.add(politician)
        cache[external_id] = politician
    first_name, last_name = split_name(payload)
    politician.label = payload.get("label") or politician.label or str(external_id)
    politician.first_name = first_name
    politician.last_name = last_name
    politician.party_label = clean_fraction_label((payload.get("party") or {}).get("label"))
    politician.abgeordnetenwatch_url = payload.get("abgeordnetenwatch_url")
    return politician


def _upsert_committees(
    db: Session, period: ParliamentPeriod, client: AbgeordnetenwatchClient
) -> dict[str, Committee]:
    """The two committees this feature cares about, matched by their label."""
    wanted = {label: key for key, label in COMMITTEE_LABELS.items()}
    found: dict[str, Committee] = {}
    for row in client.paged("/committees", field_legislature=period.external_id):
        key = wanted.get(row.get("label"))
        if key is None:
            continue
        external_id = int(row["id"])
        committee = (
            db.query(Committee).filter(Committee.external_id == external_id).one_or_none()
        )
        if committee is None:
            committee = Committee(external_id=external_id)
            db.add(committee)
        committee.parliament_period_id = period.id
        committee.key = key
        committee.label = row.get("label") or COMMITTEE_LABELS[key]
        found[key] = committee
    missing = set(COMMITTEE_LABELS) - set(found)
    if missing:
        raise RuntimeError(
            "committee not found in parliament period %s: %s"
            % (period.external_id, ", ".join(sorted(missing)))
        )
    db.flush()
    return found


def _committee_roles(
    client: AbgeordnetenwatchClient, committee: Committee
) -> dict[int, str]:
    """mandate external id → role; the strongest role wins."""
    roles: dict[int, str] = {}
    for membership in client.paged("/committee-memberships", committee=committee.external_id):
        mandate = membership.get("candidacy_mandate") or {}
        mandate_id = mandate.get("id")
        if mandate_id is None:
            continue
        mandate_id = int(mandate_id)
        role = membership.get("committee_role") or "member"
        current = roles.get(mandate_id)
        if current is None or role_rank(role) < role_rank(current):
            roles[mandate_id] = role
    return roles


def import_politicians(
    db: Session,
    *,
    period_external_id: int | None = None,
    client: AbgeordnetenwatchClient | None = None,
    user_id: int | None = None,
) -> ParliamentImportRun:
    """Fetch period, constituencies, mandates and committee memberships.

    Idempotent: a second run writes the same rows. Mandates the source no longer
    lists are removed (a substitute replaces a predecessor); the *people* stay,
    because a person outlives a mandate.
    """
    client = client or AbgeordnetenwatchClient()
    run = ParliamentImportRun(kind=IMPORT_KIND_POLITICIANS, status=IMPORT_STATUS_RUNNING)
    run.triggered_by_user_id = user_id
    db.add(run)
    db.flush()

    try:
        if period_external_id:
            period_payload = client.get(f"/parliament-periods/{period_external_id}")["data"]
        else:
            period_payload = client.get(
                "/parliament-periods",
                type="legislature",
                parliament=BUNDESTAG_PARLIAMENT_ID,
                sort_by="id",
                sort_direction="desc",
                range_end=1,
            )["data"][0]
        period = _upsert_period(db, period_payload)
        run.parliament_period_id = period.id

        constituencies = _upsert_constituency_names(
            db, period, list(client.paged("/constituencies", parliament_period=period.external_id))
        )
        committees = _upsert_committees(db, period, client)
        roles_by_committee = {
            key: _committee_roles(client, committee) for key, committee in committees.items()
        }

        stats = ImportStats()
        politician_cache: dict[int, Politician] = {}
        seen_mandate_ids: set[int] = set()

        for payload in client.paged(
            "/candidacies-mandates", parliament_period=period.external_id, type="mandate"
        ):
            external_id = int(payload["id"])
            seen_mandate_ids.add(external_id)
            politician = _upsert_politician(db, politician_cache, payload["politician"])
            db.flush()

            mandate = db.query(Mandate).filter(Mandate.external_id == external_id).one_or_none()
            if mandate is None:
                mandate = Mandate(external_id=external_id)
                db.add(mandate)
            mandate.politician_id = politician.id
            mandate.parliament_period_id = period.id

            electoral_data = payload.get("electoral_data") or {}
            mandate_won = electoral_data.get("mandate_won")
            mandate.mandate_type = mandate_won
            # Only ``constituency`` counts as a direct mandate — "moved_up" does not.
            mandate.is_direct_mandate = mandate_won == MANDATE_TYPE_CONSTITUENCY
            mandate.fraction_label = current_fraction_label(payload.get("fraction_membership"))
            mandate.info = payload.get("info")

            number = constituency_number_from_label(electoral_data.get("constituency"))
            constituency = constituencies.get(number) if number is not None else None
            mandate.constituency_id = constituency.id if constituency is not None else None

            stats.mandates += 1
            if mandate.is_direct_mandate:
                stats.direct_mandates += 1
            if mandate.constituency_id is None:
                stats.mandates_without_constituency += 1
            db.flush()

            for key, roles in roles_by_committee.items():
                role = roles.get(external_id)
                committee = committees[key]
                membership = (
                    db.query(CommitteeMembership)
                    .filter(
                        CommitteeMembership.mandate_id == mandate.id,
                        CommitteeMembership.committee_id == committee.id,
                    )
                    .one_or_none()
                )
                if role is None:
                    if membership is not None:
                        db.delete(membership)
                    continue
                if membership is None:
                    membership = CommitteeMembership(
                        mandate_id=mandate.id, committee_id=committee.id
                    )
                    db.add(membership)
                membership.role = role
                membership.role_label = role_label(role)
                membership.role_rank = role_rank(role)
                stats.committee_members += 1
                stats.committees[key] = stats.committees.get(key, 0) + 1

        # Mandates the source dropped (substitutes replacing predecessors).
        stale_query = db.query(Mandate).filter(Mandate.parliament_period_id == period.id)
        if seen_mandate_ids:
            stale_query = stale_query.filter(~Mandate.external_id.in_(seen_mandate_ids))
        for mandate in stale_query.all():
            db.delete(mandate)

        stats.politicians = len(politician_cache)
        stats.constituencies_matched = len(constituencies)
        db.flush()
        direct_constituencies = {
            mandate.constituency_id
            for mandate in db.query(Mandate).filter(
                Mandate.parliament_period_id == period.id,
                Mandate.is_direct_mandate.is_(True),
                Mandate.constituency_id.isnot(None),
            )
        }
        # Not a data gap: since the electoral reform a constituency without a
        # direct mandate is a regular case, and saying so is the point.
        stats.constituencies_without_direct_mandate = len(constituencies) - len(
            direct_constituencies
        )

        run.stats = stats.as_dict()
        run.status = IMPORT_STATUS_SUCCESS
        run.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001 — the run row records the failure
        db.rollback()
        run = db.merge(run)
        run.status = IMPORT_STATUS_ERROR
        run.error = str(exc)[:2000]
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
    return run


def import_constituency_geometries(
    db: Session,
    features: Iterable[dict[str, Any]],
    *,
    period_external_id: int,
    election_year: int,
    source: str,
    user_id: int | None = None,
) -> ParliamentImportRun:
    """Write the constituency outlines from GeoJSON features.

    The geometry is handed to PostGIS as GeoJSON and normalised to
    ``MULTIPOLYGON`` — the source mixes ``Polygon`` and ``MultiPolygon``.
    """
    from sqlalchemy import text  # local import: PostGIS-only code path

    run = ParliamentImportRun(kind=IMPORT_KIND_CONSTITUENCIES, status=IMPORT_STATUS_RUNNING)
    run.triggered_by_user_id = user_id
    db.add(run)
    db.flush()

    try:
        period = (
            db.query(ParliamentPeriod)
            .filter(ParliamentPeriod.external_id == period_external_id)
            .one_or_none()
        )
        if period is None:
            period = ParliamentPeriod(
                external_id=period_external_id,
                label=f"Wahlperiode {period_external_id}",
                is_current=True,
            )
            db.add(period)
            db.flush()
        run.parliament_period_id = period.id

        existing = {
            row.number: row
            for row in db.query(Constituency).filter(
                Constituency.parliament_period_id == period.id
            )
        }
        written = 0
        skipped = 0
        for feature in features:
            properties = feature.get("properties") or {}
            number, name = constituency_properties(properties)
            geometry = feature.get("geometry")
            if number is None or geometry is None:
                skipped += 1
                continue
            constituency = existing.get(number)
            if constituency is None:
                constituency = Constituency(parliament_period_id=period.id, number=number)
                db.add(constituency)
                existing[number] = constituency
            constituency.name = name or constituency.name or f"Wahlkreis {number}"
            constituency.state = land_name(properties) or constituency.state
            constituency.election_year = election_year
            constituency.geometry_source = source
            db.flush()
            db.execute(
                text(
                    "UPDATE constituency SET geom = ST_Multi("
                    "  ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)"
                    ") WHERE id = :id"
                ),
                {"geojson": json.dumps(geometry), "id": constituency.id},
            )
            written += 1

        run.stats = {"constituencies": written, "skipped": skipped, "source": source}
        run.status = IMPORT_STATUS_SUCCESS
        run.finished_at = datetime.utcnow()
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.merge(run)
        run.status = IMPORT_STATUS_ERROR
        run.error = str(exc)[:2000]
        run.finished_at = datetime.utcnow()
        db.commit()
        raise
    return run
