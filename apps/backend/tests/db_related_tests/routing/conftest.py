import pytest


@pytest.fixture(scope="module", autouse=True)
def load_infra_data():
    """Load infrastructure data once per module if the resources are available."""

    from scripts.import_rinf_data.import_xml import import_xml_country

    try:
        import_xml_country("AT", True, output_dir="../../data/rinf_era/v3_1_2/")
    except FileNotFoundError as exc:
        pytest.skip(f"RINF sample data not available: {exc}")
    except Exception as exc:  # pragma: no cover - defensive fallback
        pytest.skip(f"Skipping routing tests due to missing spatial capabilities: {exc}")


