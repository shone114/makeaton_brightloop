import os
import sys

os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, get_db
from app.main import app


@pytest.fixture(scope="function")
def db_session():
    from app.models import Base
    from app.core.database import engine
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    with TestClient(app) as test_client:
        yield test_client
