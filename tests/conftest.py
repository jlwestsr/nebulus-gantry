import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import Base, get_db
from routers.auth_routes import get_current_user
from unittest.mock import patch

# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def db_engine():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(db_engine):
    # Create a new session for each test
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# --- Mock User ---
class MockUser:
    id = 1
    username = "testuser"
    email = "test@example.com"
    full_name = "Test User"
    role = "user"
    current_model = "Llama 3.1"


# --- Overrides ---
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return MockUser()


@pytest.fixture(scope="module", autouse=True)
def setup_overrides():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope="module", autouse=True)
def bypass_middleware():
    # Patch middleware to verify token successfully
    # We patch verify_token and get_user_count to bypass checks
    with patch("middleware.verify_token", return_value="testuser"), \
         patch("middleware.get_user_count", return_value=1), \
         patch("middleware.SessionLocal"):  # Mock DB used in middleware
        yield


@pytest.fixture(scope="module")
def client(db_engine):
    # Set a dummy cookie to pass middleware check existence
    with TestClient(app) as c:
        c.cookies.set("access_token", "mock_token")
        yield c
