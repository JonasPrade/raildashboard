# tests/db/test_database_fixtures.py
from sqlalchemy.orm import Session
from dashboard_backend.models.railway_infrastructure import OperationalPoint, SectionOfLine  # Passen Sie diesen Import an Ihr Modell an
from dashboard_backend.core.config import settings

def test_show_database_url():
    """Dieser Test gibt die verwendete Datenbank-URL aus."""
    db_url = settings.database_url
    print(f"Die verwendete Test-Datenbank-URL ist: {db_url}")
    # Sie können auch eine Assertion hinzufügen, um sicherzustellen,
    # dass die Test-Datenbank verwendet wird.
    assert "test" in str(db_url)

def test_data_creation_in_transaction(db_session: Session):
    """
    Test 2: Erstellt einen Datensatz und prüft, ob er innerhalb derselben Transaktion/Session existiert.
    """
    # Annahme: Ihr OperationalPoint-Modell hat diese Felder. Passen Sie es entsprechend an.
    new_op = OperationalPoint(
        op_id="TEST_OP",
        name="Testpunkt",
        latitude=47.0,
        longitude=8.0
    )
    db_session.add(new_op)
    db_session.commit() # Schreibt die Änderung in die laufende Transaktion

    # Überprüfen, ob der Punkt in der DB gefunden wird (innerhalb dieser Session)
    op_in_db = db_session.query(OperationalPoint).filter_by(op_id="TEST_OP").first()
    assert op_in_db is not None
    assert op_in_db.name == "Testpunkt"

def test_transaction_rollback_isolation(db_session: Session):
    """
    Test 3: Überprüft, ob die Daten aus dem vorherigen Test nicht mehr vorhanden sind.
    Dies beweist, dass der Rollback der Fixture funktioniert hat.
    """
    # Versuchen, den im vorherigen Test erstellten Punkt zu finden
    op_in_db = db_session.query(OperationalPoint).filter_by(op_id="TEST_OP").first()

    # Der Punkt darf nicht gefunden werden, da die vorherige Transaktion zurückgerollt wurde
    assert op_in_db is None




