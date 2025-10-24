import os
import sys


os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("RINF_API_URL", "https://example.invalid")
os.environ.setdefault("RINF_USERNAME", "test-user")
os.environ.setdefault("RINF_PASSWORD", "test-password")


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

