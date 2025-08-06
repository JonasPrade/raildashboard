import pytest

@pytest.fixture(scope="module", autouse=True)
def load_infra_data():
    """
    Lädt die Infrastruktur-Daten einmal pro Testmodul.
    Diese Fixture wird nur einmal pro Modul ausgeführt, um redundante Datenbankoperationen zu vermeiden.
    """
    from scripts.import_rinf_data.import_xml import import_xml_country
    import_xml_country('AT', True, output_dir = "../../data/rinf_era/v3_1_2/")


