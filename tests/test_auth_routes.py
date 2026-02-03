import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base
from backend.dependencies import get_db
from backend.services.auth_service import AuthService


@pytest.fixture
def test_db():
    # Use StaticPool to allow SQLite in-memory db to work across threads
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create test user
    auth = AuthService(session)
    auth.create_user("admin@test.com", "password123", "Admin", role="admin")

    yield session
    session.close()


@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "session_token" in response.cookies


def test_login_wrong_password(client):
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_me_authenticated(client):
    # Login first
    login_response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password123"
    })
    assert login_response.status_code == 200

    # Access /me
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "admin@test.com"


def test_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_logout(client):
    # Login first
    client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password123"
    })

    # Logout
    response = client.post("/api/auth/logout")
    assert response.status_code == 200

    # Verify logged out
    response = client.get("/api/auth/me")
    assert response.status_code == 401
