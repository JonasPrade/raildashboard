"""Unit tests for the geometry plausibility checks behind MCP ``check_geometry``."""

from __future__ import annotations

from dashboard_backend.services.geometry_check import (
    Station,
    check_features,
    overlap_finding,
    place_names_from_project_name,
)


def _line(*coords):
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": list(coords)}}


def _routed(start, end, steps=40):
    """A straight but densely sampled line, like a GraphHopper route."""
    (x0, y0), (x1, y1) = start, end
    return _line(*[[x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps] for i in range(steps + 1)])


def _checks(findings):
    return [f["check"] for f in findings]


def test_place_names_from_project_name():
    assert place_names_from_project_name("Hochleistungskorridorsanierung Stuttgart – Ulm") == (
        ["Hochleistungskorridorsanierung Stuttgart", "Stuttgart"],
        ["Ulm"],
    )
    # Hyphen with spaces separates, inside a name it does not; parentheses are dropped.
    assert place_names_from_project_name("ABS Köln-Mülheim - Hagen (Westf) Hbf") == (
        ["ABS Köln-Mülheim", "Köln-Mülheim"],
        ["Hagen Hbf", "Hagen"],
    )
    assert place_names_from_project_name("2-gleisiger Ausbau Grötzingen–Bretten")[1] == ["Bretten"]
    assert place_names_from_project_name("740m Seebergen") == ([], [])
    assert place_names_from_project_name(None) == ([], [])


def test_routed_line_without_findings():
    feature = _routed([9.0, 48.0], [9.0, 48.5])
    assert check_features([feature], stored_length_km=55.6) == []


def test_chords_are_reported():
    # Five straight two-point segments, each about 11 km.
    coords = [[9.0, 48.0 + 0.1 * i] for i in range(6)]
    features = [_line(a, b) for a, b in zip(coords, coords[1:])]
    findings = check_features(features, stored_length_km=55.6)
    assert _checks(findings) == ["chords"]
    assert findings[0]["chord_segments"] == 5
    assert findings[0]["chord_share"] == 1.0


def test_short_two_point_pieces_are_no_chords():
    # A routed line plus a tiny two-point connector stays below the threshold.
    features = [_routed([9.0, 48.0], [9.0, 48.5]), _line([9.0, 48.5], [9.0001, 48.5001])]
    assert "chords" not in _checks(check_features(features, stored_length_km=None))


def test_gaps_between_parts():
    features = [_routed([9.0, 48.0], [9.0, 48.2]), _routed([9.0, 48.3], [9.0, 48.5])]
    findings = check_features(features, stored_length_km=44.5)
    [gap] = [f for f in findings if f["check"] == "gaps"]
    assert gap["components"] == 2
    assert 11 < gap["largest_gaps"][0]["distance_km"] < 11.2
    assert gap["largest_gaps"][0]["from"] == [9.0, 48.2]


def test_touching_parts_are_connected():
    features = [_routed([9.0, 48.0], [9.0, 48.2]), _routed([9.0, 48.5], [9.0, 48.2])]
    assert "gaps" not in _checks(check_features(features, stored_length_km=55.6))


def test_station_far_from_line():
    feature = _routed([9.3, 48.74], [10.0, 48.40])
    stations = [
        Station("start", "Stuttgart", "Stuttgart Hbf", "TS", 9.18, 48.784),
        Station("end", "Ulm", "Ulm Hbf", "TU", 9.98, 48.399),
    ]
    findings = check_features([feature], stored_length_km=None, stations=stations)
    far = [f for f in findings if f["check"].startswith("far_from")]
    assert [f["check"] for f in far] == ["far_from_start"]
    assert far[0]["op_id"] == "TS"
    assert 9 < far[0]["distance_km"] < 11


def test_length_mismatch_and_missing():
    feature = _routed([9.0, 48.0], [9.0, 48.5])  # ~55.6 km
    assert _checks(check_features([feature], stored_length_km=55.9)) == []
    mismatch = check_features([feature], stored_length_km=40.0)
    assert _checks(mismatch) == ["length_mismatch"]
    assert mismatch[0]["computed_length_km"] == 55.6
    assert _checks(check_features([feature], stored_length_km=None)) == ["length_missing"]


def test_no_geometry_and_points_only():
    assert _checks(check_features([], stored_length_km=None)) == ["no_geometry"]
    point = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [9.0, 48.0]}}
    assert _checks(check_features([point], stored_length_km=None)) == ["no_line"]


# --- overlaps -----------------------------------------------------------------


def _partner(pid, km, share_self, share_other):
    return {"project_id": pid, "name": f"P{pid}", "shared_km": km, "share_self": share_self, "share_other": share_other}


def test_overlap_finding_none_without_partners():
    assert overlap_finding([]) is None


def test_overlap_finding_lists_largest_first_and_caps():
    partners = [_partner(i, float(i), 0.2, 0.2) for i in range(1, 8)]
    finding = overlap_finding(partners)
    assert finding["check"] == "overlaps"
    assert finding["total"] == 7
    assert [p["project_id"] for p in finding["partners"]] == [7, 6, 5, 4, 3]
    assert "und 6 weiteren" in finding["message"]


def test_overlap_finding_flags_near_identical_pair():
    finding = overlap_finding([_partner(3, 12.0, 0.97, 0.95), _partner(4, 2.0, 0.2, 1.0)])
    by_id = {p["project_id"]: p for p in finding["partners"]}
    assert by_id[3]["possible_duplicate"] is True
    assert "possible_duplicate" not in by_id[4]
    assert "merge_projects" in finding["message"]
