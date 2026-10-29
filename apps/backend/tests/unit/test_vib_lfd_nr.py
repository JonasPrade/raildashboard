"""``extract_vib_lfd_nr``: the printed Vorhaben number from ``vib_name_raw``,
not the last component of the section number."""

import pytest

from dashboard_backend.tasks.vib_matching import extract_vib_lfd_nr


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Lfd. Vorhaben Nr. 2 – ABS Lübeck/Hagenow Land–Rostock–Stralsund (VDE Nr. 1)", "2"),
        ("Lfd. Vorhaben Nr. 14 – ABS Berlin–Frankfurt (Oder)", "14"),
        ("Lfd. Vorhaben Projekt Nr. 37 – ABS Foo", "37"),
        ("Neue Vorhaben Nr. 7 – ABS/NBS München-Rosenheim", "7"),
        ("Neues Vorhaben Nr. 12 – ABS Foo", "12"),
        ("Neue Vorhaben/Potentieller Bedarf Nr. 06 – ABS Nürnberg", "06"),
        ("Neue Vorhaben/Potentieller Bedarf Nr. 15 ABS Foo–Bar", "15"),
        ("Neue Vorhaben Nr. 7a – ABS Foo", "7a"),
        ("Neue Vorhaben Nr.7 – ABS Foo", "7"),
        # Only the first number counts.
        ("Lfd. Vorhaben Nr. 3 – ABS Foo / Neue Vorhaben Nr. 8 – ABS Bar", "3"),
        ("Neue Vorhaben Nr. 4 – ABS Foo inklusive Anteile Potenzieller Bedarf Nr. 16", "4"),
        # No Vorhaben number in the prefix.
        ("ABS Foo (VDE Nr. 1)", None),
        ("ABS Foo – Potenzieller Bedarf Nr. 16", None),
        ("", None),
        (None, None),
    ],
)
def test_extract_vib_lfd_nr(name, expected):
    assert extract_vib_lfd_nr(name) == expected
