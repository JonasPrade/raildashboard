"""Haushalt import: archived projects take no new Sammel-FinVe year
(feature-project-archive.md → W5a) — the successor is suggested, or the row
stays open, with a review note."""

from dashboard_backend.tasks.haushalt import redirect_archived_projects

ARCHIVED = {1471: "Optimiertes Alpha-E mit Bremen", 1477: "ABS/NBS Hannover – Bielefeld (BVWP)"}


def test_archived_project_is_replaced_by_its_successor():
    links = {763: [1471, 2001], 1168: [1477]}
    notes = redirect_archived_projects(links, ARCHIVED, {1477: 1535})

    assert links == {763: [2001], 1168: [1535]}
    assert "1471" in notes[763][0] and "keinen Nachfolger" in notes[763][0]
    assert "Nachfolger 1535" in notes[1168][0]


def test_finve_left_without_projects_is_open_again():
    links = {763: [1471], 900: [2001]}
    notes = redirect_archived_projects(links, ARCHIVED, {})

    assert links == {900: [2001]}
    assert list(notes) == [763]


def test_successor_already_linked_is_not_doubled():
    links = {1168: [1535, 1477]}
    redirect_archived_projects(links, ARCHIVED, {1477: 1535})
    assert links == {1168: [1535]}
