import sys
from pathlib import Path
import pytest

# Ensure workspace root and test dir are first in sys.path to avoid shadowing site-packages
root_dir = Path(__file__).resolve().parent.parent
test_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))

from app import database, security
from app.routes import auth, admin
from mock_db import MockDatabase


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture(autouse=True)
def setup_mock_db(monkeypatch):
    mock_db = MockDatabase()
    monkeypatch.setattr(database, "get_database", lambda: mock_db)
    monkeypatch.setattr(database, "db", mock_db)

    # Use fast hashing for instant unit testing
    fast_hash = lambda p: f"hashed_{p}"
    fast_verify = lambda p, h: h == f"hashed_{p}"

    monkeypatch.setattr(security, "hash_password", fast_hash)
    monkeypatch.setattr(security, "verify_password", fast_verify)
    monkeypatch.setattr(auth, "hash_password", fast_hash)
    monkeypatch.setattr(auth, "verify_password", fast_verify)
    monkeypatch.setattr(admin, "hash_password", fast_hash)

    return mock_db
