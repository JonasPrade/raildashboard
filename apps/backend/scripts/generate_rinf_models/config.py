from pathlib import Path

# Basisverzeichnis, das die .ttl-Datei enthält
BASE_DIR = Path("data/rinf_era/v3_1_2")

# Pfad zur Turtle-Datei der ERA RINF Ontologie
TTL_FILE = BASE_DIR / "era_rinf_ontology.ttl"

# Verzeichnis für generierte Ausgaben
OUTPUT_DIR = BASE_DIR / "generated_models"

# Pfad zur generierten SQLAlchemy-Stubs-Datei
STUB_FILE = OUTPUT_DIR / "sqlalchemy_stubs.py"

# Pfad zur Markdown-Dokumentation der Klassen
DOC_FILE = OUTPUT_DIR / "classes.md"
