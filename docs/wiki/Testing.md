# Testing

Comprehensive testing guide for Nebulus Gantry, covering unit tests, integration tests, test writing best practices, coverage reporting, and CI/CD integration.

---

## Test Stack

- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **httpx** - HTTP client for API testing
- **SQLAlchemy testing** - Database fixtures

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest backend/tests/test_auth_service.py

# Run specific test function
pytest backend/tests/test_auth_service.py::test_create_user

# Run tests matching pattern
pytest -k "test_auth"

# Run with print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=backend

# Generate HTML report
pytest --cov=backend --cov-report=html

# Open report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Generate terminal report with missing lines
pytest --cov=backend --cov-report=term-missing

# Set minimum coverage threshold
pytest --cov=backend --cov-fail-under=80
```

### Docker Testing

```bash
# Run tests in Docker
docker compose exec backend pytest

# With coverage
docker compose exec backend pytest --cov=backend

# Watch mode (requires pytest-watch)
docker compose exec backend ptw
```

---

## Test Organization

### Directory Structure

```text
backend/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_auth_service.py     # Auth tests
├── test_chat_service.py     # Chat tests
├── test_memory_service.py   # Memory tests
├── test_documents.py        # Document tests
├── test_model_switching.py  # Model tests
├── test_search.py           # Search tests
├── test_export.py           # Export tests
└── test_api/                # API endpoint tests
    ├── test_auth.py
    ├── test_chat.py
    └── test_admin.py
```

### Test Naming

- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

Example:

```python
# test_auth_service.py

def test_create_user():
    """Test user creation."""
    pass

def test_create_user_duplicate_email():
    """Test user creation with duplicate email fails."""
    pass

class TestUserAuthentication:
    def test_valid_login(self):
        """Test login with valid credentials."""
        pass

    def test_invalid_password(self):
        """Test login with invalid password fails."""
        pass
```

---

## Writing Tests

### Basic Test Structure

```python
# test_example.py
import pytest
from backend.services.example_service import ExampleService

def test_example_function():
    """Test that example function returns expected result."""
    # Arrange
    input_data = {"value": 42}

    # Act
    result = example_function(input_data)

    # Assert
    assert result == 42
    assert isinstance(result, int)
```

### Using Fixtures

Fixtures provide reusable test data and setup.

#### Defining Fixtures

```python
# conftest.py
import pytest
from backend.database import get_engine, Base
from sqlalchemy.orm import Session

@pytest.fixture
def db_session():
    """Create test database session."""
    engine = get_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    session = Session(bind=engine)
    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db_session):
    """Create test user."""
    from backend.models.user import User
    from backend.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        email="test@example.com",
        password="test123",
        display_name="Test User",
        role="user"
    )
    return user

@pytest.fixture
def admin_user(db_session):
    """Create admin user."""
    from backend.models.user import User
    from backend.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    user = auth_service.create_user(
        email="admin@example.com",
        password="admin123",
        display_name="Admin User",
        role="admin"
    )
    return user
```

#### Using Fixtures

```python
# test_auth_service.py
def test_create_user(db_session):
    """Test user creation."""
    auth_service = AuthService(db_session)

    user = auth_service.create_user(
        email="newuser@example.com",
        password="password123",
        display_name="New User",
        role="user"
    )

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.display_name == "New User"
    assert user.role == "user"
    assert user.password_hash != "password123"  # Should be hashed

def test_authenticate_user(db_session, test_user):
    """Test user authentication with valid credentials."""
    auth_service = AuthService(db_session)

    # Valid credentials
    user = auth_service.authenticate(
        email="test@example.com",
        password="test123"
    )

    assert user is not None
    assert user.email == test_user.email

def test_authenticate_invalid_password(db_session, test_user):
    """Test authentication fails with invalid password."""
    auth_service = AuthService(db_session)

    # Invalid password
    user = auth_service.authenticate(
        email="test@example.com",
        password="wrong-password"
    )

    assert user is None
```

### Testing Async Functions

```python
# test_chat_service.py
import pytest

@pytest.mark.asyncio
async def test_send_message_async(db_session, test_user):
    """Test async message sending."""
    from backend.services.chat_service import ChatService

    chat_service = ChatService(db_session)

    # Create conversation
    conversation = chat_service.create_conversation(
        user_id=test_user.id,
        title="Test Conversation"
    )

    # Send message
    message = await chat_service.send_message_async(
        conversation_id=conversation.id,
        content="Hello, world!",
        role="user"
    )

    assert message.id is not None
    assert message.content == "Hello, world!"
    assert message.role == "user"
```

### Testing Exceptions

```python
def test_create_user_duplicate_email(db_session, test_user):
    """Test creating user with duplicate email raises error."""
    auth_service = AuthService(db_session)

    with pytest.raises(ValueError, match="Email already exists"):
        auth_service.create_user(
            email=test_user.email,  # Duplicate
            password="password",
            display_name="Another User",
            role="user"
        )

def test_get_nonexistent_conversation(db_session, test_user):
    """Test getting nonexistent conversation raises 404."""
    from backend.services.chat_service import ChatService
    from fastapi import HTTPException

    chat_service = ChatService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        chat_service.get_conversation(
            conversation_id=999,
            user_id=test_user.id
        )

    assert exc_info.value.status_code == 404
```

### Parametrized Tests

Test multiple inputs:

```python
@pytest.mark.parametrize("email,password,should_fail", [
    ("valid@example.com", "GoodPass123!", False),
    ("invalid-email", "GoodPass123!", True),
    ("valid@example.com", "short", True),
    ("valid@example.com", "NoNumbers!", True),
])
def test_user_validation(email, password, should_fail):
    """Test user input validation."""
    if should_fail:
        with pytest.raises(ValueError):
            validate_user_input(email, password)
    else:
        result = validate_user_input(email, password)
        assert result is True
```

### Mocking External Services

```python
from unittest.mock import Mock, patch, AsyncMock

def test_llm_service_with_mock(db_session):
    """Test chat service with mocked LLM."""
    from backend.services.chat_service import ChatService
    from backend.services.llm_service import LLMService

    # Mock LLM response
    mock_llm = Mock(spec=LLMService)
    mock_llm.generate.return_value = "Mocked AI response"

    chat_service = ChatService(db_session)
    chat_service.llm_service = mock_llm

    # Test chat
    response = chat_service.send_message(
        conversation_id=1,
        content="Test message"
    )

    # Verify mock was called
    mock_llm.generate.assert_called_once()
    assert response.content == "Mocked AI response"

@pytest.mark.asyncio
async def test_chromadb_unavailable():
    """Test memory service handles ChromaDB unavailability."""
    from backend.services.memory_service import MemoryService

    with patch('chromadb.HttpClient') as mock_client:
        mock_client.side_effect = ConnectionError("ChromaDB unavailable")

        memory_service = MemoryService(user_id=1)

        # Should handle gracefully
        result = memory_service.search_similar("test query")
        assert result == []  # Empty results when unavailable
```

---

## API Testing

### Testing Endpoints

```python
# test_api/test_auth.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_login_success():
    """Test successful login."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "test123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "session_id" in response.cookies

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrong-password"
        }
    )

    assert response.status_code == 401
    assert "Unauthorized" in response.text

def test_protected_endpoint_without_auth():
    """Test accessing protected endpoint without auth."""
    response = client.get("/api/chat/conversations")

    assert response.status_code == 401

def test_protected_endpoint_with_auth(test_user):
    """Test accessing protected endpoint with auth."""
    # Login first
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "test123"
        }
    )

    # Use session cookie
    cookies = login_response.cookies

    # Access protected endpoint
    response = client.get(
        "/api/chat/conversations",
        cookies=cookies
    )

    assert response.status_code == 200
```

### Testing SSE Streaming

```python
@pytest.mark.asyncio
async def test_chat_streaming():
    """Test SSE chat streaming."""
    import httpx

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # Login
        login_response = await client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "test123"}
        )
        cookies = login_response.cookies

        # Stream chat
        async with client.stream(
            "GET",
            "/api/chat/stream/1",
            cookies=cookies
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"

            # Read first few events
            count = 0
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    count += 1
                    if count >= 3:
                        break

            assert count >= 3  # Received multiple events
```

---

## Database Testing

### In-Memory Database

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base

@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)
```

### Testing Migrations

```python
def test_database_schema():
    """Test that all models create tables correctly."""
    engine = create_engine("sqlite:///:memory:")

    # Should not raise
    Base.metadata.create_all(bind=engine)

    # Check tables exist
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "users" in tables
    assert "conversations" in tables
    assert "messages" in tables
    assert "documents" in tables
    assert "sessions" in tables
```

---

## Coverage Goals

### Target Coverage

- **Overall:** 80%+
- **Services:** 90%+
- **Models:** 70%+
- **Routers:** 80%+

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=backend --cov-report=term-missing

# Sample output:
# Name                              Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------
# backend/services/auth_service.py     45      2    96%   78-79
# backend/services/chat_service.py     67      8    88%   45, 67-73
# backend/routers/auth.py              32      0   100%
# ---------------------------------------------------------------
# TOTAL                               456     28    94%
```

### Improving Coverage

Focus on:

1. **Untested branches** - Add tests for all if/else paths
2. **Exception handling** - Test error cases
3. **Edge cases** - Test boundary conditions
4. **Async code** - Test all async functions

---

## Test Best Practices

### 1. Arrange-Act-Assert Pattern

```python
def test_example():
    # Arrange - Set up test data
    user = create_test_user()
    service = UserService(db_session)

    # Act - Execute the function
    result = service.get_user(user.id)

    # Assert - Verify result
    assert result.email == user.email
```

### 2. One Assertion Per Test (Guideline)

```python
# Good - focused test
def test_user_email():
    user = create_user()
    assert user.email == "test@example.com"

def test_user_role():
    user = create_user()
    assert user.role == "user"

# Acceptable - related assertions
def test_user_creation():
    user = create_user()
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == "user"
```

### 3. Test Independence

```python
# Bad - tests depend on order
def test_create_user():
    user = create_user()
    assert user.id == 1

def test_get_user():
    user = get_user(1)  # Depends on previous test!
    assert user is not None

# Good - tests are independent
@pytest.fixture
def test_user(db_session):
    return create_user(db_session)

def test_create_user(db_session):
    user = create_user(db_session)
    assert user.id is not None

def test_get_user(db_session, test_user):
    user = get_user(db_session, test_user.id)
    assert user is not None
```

### 4. Descriptive Test Names

```python
# Bad
def test_user():
    pass

# Good
def test_create_user_with_valid_email_succeeds():
    pass

def test_authenticate_user_with_invalid_password_fails():
    pass

def test_admin_can_delete_any_conversation():
    pass
```

### 5. Use Fixtures for Setup

```python
# Bad - duplicate setup
def test_a():
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    # test code

def test_b():
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    # test code

# Good - fixture
@pytest.fixture
def test_user(db_session):
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()
    return user

def test_a(test_user):
    # test code

def test_b(test_user):
    # test code
```

---

## Continuous Integration

### GitHub Actions

`.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          cd backend
          pytest --cov=backend --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          fail_ci_if_error: true
```

### Pre-commit Hook

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: bash -c 'cd backend && pytest'
        language: system
        pass_filenames: false
        always_run: true
```

---

## Performance Testing

### Load Testing with Locust

```python
# tests/load_test.py
from locust import HttpUser, task, between

class GantryUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login before tests."""
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "test123"
        })
        self.session_id = response.cookies.get("session_id")

    @task(3)
    def list_conversations(self):
        """List conversations (common operation)."""
        self.client.get("/api/chat/conversations")

    @task(1)
    def send_message(self):
        """Send chat message (less frequent)."""
        self.client.post("/api/chat/send", json={
            "conversation_id": 1,
            "content": "Test message"
        })

    @task(1)
    def search(self):
        """Search conversations."""
        self.client.get("/api/chat/search?q=test")
```

```bash
# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

---

## Debugging Failed Tests

### Verbose Output

```bash
# Show print statements
pytest -s

# Show full diff on assertion errors
pytest -vv

# Show local variables on failure
pytest -l

# Drop into debugger on failure
pytest --pdb
```

### Using Debugger

```python
def test_something():
    user = create_user()

    # Add breakpoint
    import pdb; pdb.set_trace()

    result = some_function(user)
    assert result is not None
```

### Logging in Tests

```python
import logging

def test_with_logging(caplog):
    """Test with log capture."""
    caplog.set_level(logging.INFO)

    # Run code that logs
    result = function_that_logs()

    # Check logs
    assert "Expected log message" in caplog.text
```

---

## Related Documentation

- **[Development Setup](Development-Setup)** - Setting up dev environment
- **[Contributing](Contributing)** - Contribution guidelines
- **[Debugging Guide](Debugging-Guide)** - Troubleshooting and debugging

---

**[← Back to Development Setup](Development-Setup)** | **[Next: Contributing →](Contributing)**
