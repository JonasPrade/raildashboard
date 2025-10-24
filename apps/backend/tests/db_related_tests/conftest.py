# tests/conftest.py
import os
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

load_dotenv(dotenv_path='env.test', override=True)

# SCHRITT 1: Setze die Umgebungsvariable, BEVOR die Konfiguration importiert wird.
# Dies ist der wichtigste Schritt.
 # Lädt die Umgebungsvariablen aus der .env.test Datei
# os.environ['ENVIRONMENT'] = 'test'

# SCHRITT 2: Importiere jetzt die Konfiguration und andere App-Teile.
# `settings` wird nun die Werte aus `.env.test` enthalten.
from dashboard_backend.core.config import settings
from dashboard_backend.models.base import Base

# Die app_engine wird hier absichtlich nicht importiert. Für Tests erstellen wir
# eine dedizierte Engine, um eine vollständige Isolation zu gewährleisten.

# Erstelle eine Engine und eine Session-Klasse speziell für die Tests.
# Dies stellt sicher, dass Tests niemals die produktive DB berühren und
# gibt uns volle Kontrolle über den Test-Lebenszyklus der Datenbank.
test_engine = create_engine(settings.database_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database(request):
    """
    Erstellt die Test-Datenbank-Tabellen einmal pro Test-Session und löscht sie danach.
    """
    load_dotenv(".env.test")
    if 'test' not in settings.database_url:
        raise ValueError("the test database URL must contain 'test' to avoid accidental data loss")
    try:
        Base.metadata.create_all(bind=test_engine)
    except OperationalError as exc:
        if "RecoverGeometryColumn" in str(exc):
            pytest.skip("SpatiaLite extension not available for geometry-enabled tables")
        raise
    yield
    try:
        Base.metadata.drop_all(bind=test_engine)
    except OperationalError as exc:
        if "CheckSpatialIndex" not in str(exc):
            raise


@pytest.fixture(scope="function")
def db_session():
    """
    Stellt eine saubere Datenbank-Session für jeden einzelnen Test bereit.
    Diese Fixture verwendet ein "Transaction Rollback"-Muster:
    1. Eine Verbindung zur Test-DB wird geöffnet.
    2. Eine Transaktion wird gestartet.
    3. Der Test läuft innerhalb dieser Transaktion.
    4. Am Ende wird die Transaktion zurückgerollt.

    Ergebnis: Jeder Test startet mit einer leeren Datenbank und hinterlässt keine Daten,
    was die Tests voneinander unabhängig und wiederholbar macht.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)

    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()

