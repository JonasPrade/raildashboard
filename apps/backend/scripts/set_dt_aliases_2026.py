"""One-off: Deutschlandtakt aliases ("DT nn") from the Infraplan 2026 (feature-infraplan-import.md).

The Infraplan names Deutschlandtakt measures "DT 38"; the dashboard's D-numbers
match only partly (D-38 = DT 38, but DT 105 is D-37). The pairs below were read
from the 2026 rows by name, only where the row names the measure beyond doubt
(ambiguous ones such as DT 44, DT 53/54, DT 76, DT 85/86 are left out). With the
alias the import matches these rows as a sure hit from 2027 on.

A project is only changed when its project number is still the one the pair
was read with; existing aliases are kept. Idempotent.

Usage:
    python scripts/set_dt_aliases_2026.py            # report only
    python scripts/set_dt_aliases_2026.py --apply    # write
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from dashboard_backend.crud.changelog import create_changelog_for_patch
from dashboard_backend.database import Session
from dashboard_backend.models.projects.project import Project

USERNAME = "infraplan-dt-aliases"  # shown in the project history

# (DT number, project id, project number at the time of reading)
PAIRS: tuple[tuple[int, int, str], ...] = (
    (2, 1632, "D-111"),  # Lübeck – Lübeck Hochschulstadt
    (3, 1633, "D-112"),  # Ratzeburg
    (4, 1634, "D-113"),  # Lauenburg
    (5, 1635, "D-114"),  # Mölln – Güster
    (7, 1631, "D-110"),  # Adendorf
    (8, 1584, "D-63"),  # HH-Altona – HH Hbf, Ü-BW Dammtor
    (9, 1583, "D-62"),  # Verbindungsbahn für SPFV
    (10, 1581, "D-60"),  # Tieferlegung S-Bahn
    (12, 1580, "D-59"),  # HH Hbf Südkopf
    (15, 1636, "D-115"),  # Buchholz (Nordheide)
    (26, 1647, "D-126"),  # Stickhausen-Velde
    (27, 1648, "D-127"),  # Bremen Hbf ehem. Bwn – Bremen Hbf
    (28, 1551, "D-30"),  # Twistringen
    (29, 1646, "D-125"),  # Abzw. Utbremen
    (38, 1559, "D-38"),  # Hannover Hbf, Personenunterführung
    (39, 1688, "D-167"),  # Lehrte West – Lehrte Nord
    (40, 1689, "D-168"),  # Ostkopf Lehrte
    (41, 1645, "D-124"),  # Groß Gleidingen
    (45, 1537, "D-16"),  # Bielefeld Hbf
    (50, 1536, "D-15"),  # Löhne – Osnabrück
    (51, 1533, "D-12"),  # Knoten Hamm
    (52, 1532, "D-11"),  # Dortmund Dbw – Hamm
    (56, 1542, "D-21"),  # Abzw. Flughafen Nordwest (Köln)
    (57, 1541, "D-20"),  # Aachen Hbf
    (61, 1876, "D-170"),  # Mainz-Bischofsheim Pbf – Abzw. Mönchwald
    (62, 1528, "D-7"),  # Abzw. Mönchhof – Abzw. Mönchwald
    (87, 1669, "D-148"),  # Langes Feld – Stuttgart Hbf
    (92, 1671, "D-150"),  # Böblingen
    (93, 1686, "D-165"),  # Wurmlingen – Tuttlingen
    (99, 1625, "D-104"),  # Augsburg-Oberhausen
    (100, 1561, "D-40"),  # Donauwörth, Achsverschwenkung
    (102, 1609, "D-88"),  # Malching – Maisach
    (105, 1558, "D-37"),  # München Hbf, Fußgängerüberquerung
    (106, 1624, "D-103"),  # München Hbf, Gleisvorfeld
    (110, 1604, "D-83"),  # Freising – Landshut – Regensburg
    (113, 1622, "D-101"),  # Regensburg Hbf – Obertraubling
    (114, 1611, "D-90"),  # Ergolding
    (115, 1612, "D-91"),  # Niederaichbach
    (116, 1596, "D-75"),  # Ingolstadt – Petershausen
    (117, 1608, "D-87"),  # Überholgleis Petershausen
    (120, 1601, "D-80"),  # Weichering
    (121, 1602, "D-81"),  # Rohrenfeld
    (122, 1600, "D-79"),  # Blindheim
    (125, 1613, "D-92"),  # Altenschwand – Bodenwöhr Nord
    (126, 1614, "D-93"),  # Cham – Cham Schwedenschanze
    (127, 1615, "D-94"),  # Weiding – Arnschwang
    (128, 1618, "D-97"),  # Beratzhausen
    (129, 1619, "D-98"),  # Undorf
    (130, 1617, "D-96"),  # Straßkirchen
    (131, 1616, "D-95"),  # Plattling
    (132, 1627, "D-106"),  # Fürth-Bislohe – Nürnberg
    (133, 1562, "D-41"),  # NBS Würzburg – Nürnberg
    (134, 1563, "D-42"),  # Überholgleis Rottendorf – Fürth-Bislohe
    (135, 1685, "D-164"),  # Neustadt (Aisch)
    (136, 1621, "D-100"),  # Würzburg – Rottendorf
    (137, 1675, "D-154"),  # Veitshöchheim, Puffergleis
    (138, 1676, "D-155"),  # Gemünden
    (139, 1523, "D-2"),  # Heigenbrücken – Nantenbach
    (140, 1572, "D-51"),  # Erfurt, Überwerfungsbauwerk
    (141, 1684, "D-163"),  # Leipzig-Plagwitz
    (142, 1643, "D-122"),  # Leipzig-Wahren
    (143, 1574, "D-53"),  # Leipzig Radefeld/GVZ – Leipzig Messe
    (144, 1575, "D-54"),  # Leipzig Messe Nord – Leipzig Messe
    (148, 1681, "D-160"),  # Nauendorf
    (152, 1568, "D-47"),  # Muldenstein – Radis
    (153, 1587, "D-66"),  # Berlin Südkreuz – Ludwigsfelde
    (156, 1592, "D-71"),  # Berlin-Spandau Westkopf
    (157, 1682, "D-161"),  # Wustermark
    (158, 1683, "D-162"),  # Rathenow
    (159, 1642, "D-121"),  # Oebisfelde
    (160, 1571, "D-50"),  # Oebisfelde – Bamme
    (162, 1566, "D-45"),  # Abzw. Nahrstedt
    (164, 1586, "D-65"),  # Neustadt (Dosse) – Spandau
    (166, 1644, "D-123"),  # Ludwigslust
    (169, 1651, "D-130"),  # Rügendamm – Lietzow
    (170, 1650, "D-129"),  # Lietzow, Bahnsteige
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the change (default: report only)")
    args = parser.parse_args()

    wanted: dict[int, list[str]] = defaultdict(list)
    numbers: dict[int, str] = {}
    for dt, project_id, number in PAIRS:
        wanted[project_id].append(f"DT {dt}")
        numbers[project_id] = number

    deviations = changed = already = 0
    with Session() as db:
        for project_id, aliases in wanted.items():
            project = db.get(Project, project_id)
            if project is None:
                print(f"{project_id}: not found — skipped")
                deviations += 1
                continue
            if project.project_number != numbers[project_id]:
                print(
                    f"{project_id} {project.name!r}: NOT CHANGED — project number is "
                    f"{project.project_number!r}, expected {numbers[project_id]!r}"
                )
                deviations += 1
                continue
            current = list(project.aliases or [])
            new = current + [a for a in aliases if a not in current]
            if new == current:
                already += 1
                continue
            print(f"{project_id} {project.name!r}: aliases {current} -> {new}")
            changed += 1
            if args.apply:
                create_changelog_for_patch(db, project, {"aliases": new}, None, USERNAME)
                project.aliases = new
        if args.apply:
            db.commit()
    mode = "applied" if args.apply else "dry run"
    print(f"{mode}: {changed} changed, {already} already set, {deviations} deviations")
    return 1 if deviations else 0


if __name__ == "__main__":
    sys.exit(main())
