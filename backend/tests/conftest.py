import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Disable simulation mode during testing
os.environ["SIMULATION_MODE"] = "false"
os.environ["DEVICE_API_KEY"] = "test-device-key-123"
os.environ["FRONTEND_API_TOKEN"] = "test-frontend-token-456"

from app.config import settings
settings.SIMULATION_MODE = False
settings.DEVICE_API_KEY = "test-device-key-123"
settings.FRONTEND_API_TOKEN = "test-frontend-token-456"

from app.database import Base, get_db
from app.main import app

# Shared in-memory test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def device_headers():
    return {"X-API-Key": "test-device-key-123"}


@pytest.fixture
def frontend_headers():
    return {"Authorization": "Bearer test-frontend-token-456"}
