import pytest
from starlette.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db, init_db
from main import app
from routers.auth_routes import get_current_user

# Setup in-memory DB for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Mock user for auth dependency
    def override_get_current_user():
        from database import User
        return User(id=1, username="testuser", email="test@example.com")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    from unittest.mock import patch
    # Mock middleware checks (verify_token=True, user_count=1)
    with patch("middleware.verify_token", return_value={"sub": "testuser"}), \
         patch("middleware.get_user_count", return_value=1):
        with TestClient(app) as c:
            c.cookies["access_token"] = "dummy_token"
            yield c
    
    app.dependency_overrides.clear()
