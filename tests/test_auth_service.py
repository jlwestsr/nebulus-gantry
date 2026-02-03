import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.user import User
from backend.services.auth_service import AuthService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def auth_service(db_session):
    return AuthService(db_session)


def test_create_user(auth_service, db_session):
    user = auth_service.create_user("test@example.com", "password123", "Test User")
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.password_hash != "password123"  # Should be hashed


def test_authenticate_user_success(auth_service):
    auth_service.create_user("test@example.com", "password123", "Test User")
    user = auth_service.authenticate("test@example.com", "password123")
    assert user is not None
    assert user.email == "test@example.com"


def test_authenticate_user_wrong_password(auth_service):
    auth_service.create_user("test@example.com", "password123", "Test User")
    user = auth_service.authenticate("test@example.com", "wrongpassword")
    assert user is None


def test_create_session(auth_service):
    user = auth_service.create_user("test@example.com", "password123", "Test User")
    token = auth_service.create_session(user.id)
    assert token is not None
    assert len(token) > 20


def test_validate_session(auth_service):
    user = auth_service.create_user("test@example.com", "password123", "Test User")
    token = auth_service.create_session(user.id)
    validated_user = auth_service.validate_session(token)
    assert validated_user is not None
    assert validated_user.id == user.id
