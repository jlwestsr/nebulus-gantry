# Gantry v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild Nebulus Gantry as a React + FastAPI application with Claude.AI-like chat experience, hybrid long-term memory, and admin control panel.

**Architecture:** Monorepo with `backend/` (FastAPI + SQLite + ChromaDB + NetworkX) and `frontend/` (React + TypeScript + Vite + Tailwind). Session-based auth, SSE streaming for chat and logs.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, React 18, TypeScript, Vite, Tailwind CSS, ChromaDB, NetworkX

---

## Phase 1: Project Scaffolding

### Task 1: Clean Slate

**Files:**
- Delete: All existing Python files in root
- Delete: `public/`, `ui/`, `routers/`, `ops/`, `exec/`, `metrics/`, `agent/`, `.agent/`
- Keep: `docs/`, `tests/`, `.gitignore`, `README.md`, `CONTEXT.md`

**Step 1: Remove old codebase**

```bash
cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/.worktrees/gantry-v2
rm -rf auth.py chat.py database.py main.py middleware.py version.py __init__.py
rm -rf public ui routers ops exec metrics agent .agent .chainlit
rm -rf docker-compose.yml Dockerfile requirements.txt
rm -rf tests/*
```

**Step 2: Verify clean state**

```bash
ls -la
```

Expected: Only `docs/`, `README.md`, `CONTEXT.md`, `.gitignore`, hidden files

**Step 3: Commit clean slate**

```bash
git add -A
git commit -m "chore: clean slate for Gantry v2 rebuild"
```

---

### Task 2: Create Backend Structure

**Files:**
- Create: `backend/` directory structure
- Create: `backend/requirements.txt`
- Create: `backend/.flake8`

**Step 1: Create directory structure**

```bash
mkdir -p backend/{models,services,routers}
touch backend/__init__.py
touch backend/models/__init__.py
touch backend/services/__init__.py
touch backend/routers/__init__.py
```

**Step 2: Create requirements.txt**

Create `backend/requirements.txt`:

```text
# Core
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.0
aiosqlite>=0.19.0

# Auth
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0

# LLM & Memory
httpx>=0.26.0
chromadb>=0.4.0
networkx>=3.2

# Dev
pytest>=8.0.0
pytest-asyncio>=0.23.0
flake8>=7.0.0
```

**Step 3: Create .flake8**

Create `backend/.flake8`:

```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,venv,.venv
```

**Step 4: Commit**

```bash
git add backend/
git commit -m "chore: scaffold backend directory structure"
```

---

### Task 3: Create Frontend Structure

**Files:**
- Create: `frontend/` via Vite scaffold

**Step 1: Scaffold React + TypeScript project**

```bash
cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/.worktrees/gantry-v2
npm create vite@latest frontend -- --template react-ts
```

**Step 2: Install dependencies**

```bash
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

**Step 3: Install additional dependencies**

```bash
npm install react-router-dom zustand
npm install -D @types/react-router-dom
```

**Step 4: Configure Tailwind**

Update `frontend/tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

**Step 5: Add Tailwind to CSS**

Replace `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

**Step 6: Verify frontend runs**

```bash
npm run dev
```

Expected: Vite dev server starts on http://localhost:5173

**Step 7: Stop dev server and commit**

```bash
# Ctrl+C to stop
git add frontend/
git commit -m "chore: scaffold frontend with React + TypeScript + Tailwind"
```

---

### Task 4: Create Docker Configuration

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

**Step 1: Create docker-compose.yml**

Create `docker-compose.yml`:

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/gantry.db
      - CHROMA_HOST=http://host.docker.internal:8001
      - TABBY_HOST=http://host.docker.internal:5000
      - SECRET_KEY=dev-secret-change-in-production
    volumes:
      - ./data:/app/data
      - ./backend:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev -- --host 0.0.0.0 --port 3000

volumes:
  data:
```

**Step 2: Create backend Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create frontend Dockerfile**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

**Step 4: Create data directory**

```bash
mkdir -p data
touch data/.gitkeep
```

**Step 5: Commit**

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile data/
git commit -m "chore: add Docker configuration"
```

---

## Phase 2: Backend Core

### Task 5: Database Models

**Files:**
- Create: `backend/database.py`
- Create: `backend/models/user.py`
- Create: `backend/models/conversation.py`
- Create: `backend/models/message.py`
- Test: `tests/test_models.py`

**Step 1: Create test file**

Create `tests/__init__.py`:

```python
```

Create `tests/test_models.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_user(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.role == "user"


def test_create_conversation(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="Test Chat")
    db_session.add(conv)
    db_session.commit()
    assert conv.id is not None


def test_create_message(db_session):
    user = User(email="test@example.com", password_hash="hash", display_name="Test")
    db_session.add(user)
    db_session.commit()

    conv = Conversation(user_id=user.id, title="Test Chat")
    db_session.add(conv)
    db_session.commit()

    msg = Message(conversation_id=conv.id, role="user", content="Hello")
    db_session.add(msg)
    db_session.commit()
    assert msg.id is not None
```

**Step 2: Run test to verify it fails**

```bash
cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/.worktrees/gantry-v2
python -m pytest tests/test_models.py -v
```

Expected: FAIL (imports don't exist)

**Step 3: Create database.py**

Create `backend/database.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


def get_engine(database_url: str = "sqlite:///./data/gantry.db"):
    return create_engine(database_url, connect_args={"check_same_thread": False})


def get_session_maker(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Step 4: Create user model**

Create `backend/models/user.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(String, default="user")  # "user" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Step 5: Create conversation model**

Create `backend/models/conversation.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
```

**Step 6: Create message model**

Create `backend/models/message.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
```

**Step 7: Update models __init__.py**

Update `backend/models/__init__.py`:

```python
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message

__all__ = ["User", "Conversation", "Message"]
```

**Step 8: Run tests to verify they pass**

```bash
python -m pytest tests/test_models.py -v
```

Expected: 3 passed

**Step 9: Commit**

```bash
git add backend/ tests/
git commit -m "feat: add database models (User, Conversation, Message)"
```

---

### Task 6: Configuration

**Files:**
- Create: `backend/config.py`
- Test: `tests/test_config.py`

**Step 1: Create test**

Create `tests/test_config.py`:

```python
import os
from backend.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.database_url == "sqlite:///./data/gantry.db"
    assert settings.secret_key is not None


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    settings = Settings()
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.secret_key == "test-secret"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_config.py -v
```

Expected: FAIL

**Step 3: Create config.py**

Create `backend/config.py`:

```python
import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/gantry.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    chroma_host: str = os.getenv("CHROMA_HOST", "http://localhost:8001")
    tabby_host: str = os.getenv("TABBY_HOST", "http://localhost:5000")
    session_expire_hours: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))


settings = Settings()
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_config.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add backend/config.py tests/test_config.py
git commit -m "feat: add configuration management"
```

---

### Task 7: Auth Service

**Files:**
- Create: `backend/services/auth_service.py`
- Test: `tests/test_auth_service.py`

**Step 1: Create test**

Create `tests/test_auth_service.py`:

```python
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
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_auth_service.py -v
```

Expected: FAIL

**Step 3: Create Session model**

Create `backend/models/session.py`:

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="sessions")
```

**Step 4: Update models __init__.py**

Update `backend/models/__init__.py`:

```python
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.session import Session

__all__ = ["User", "Conversation", "Message", "Session"]
```

**Step 5: Create auth_service.py**

Create `backend/services/auth_service.py`:

```python
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy.orm import Session as DBSession

from backend.models.user import User
from backend.models.session import Session
from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: DBSession):
        self.db = db

    def create_user(self, email: str, password: str, display_name: str, role: str = "user") -> User:
        password_hash = pwd_context.hash(password)
        user = User(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            role=role
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not pwd_context.verify(password, user.password_hash):
            return None
        return user

    def create_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
        session = Session(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(session)
        self.db.commit()
        return token

    def validate_session(self, token: str) -> User | None:
        session = self.db.query(Session).filter(Session.token == token).first()
        if not session:
            return None
        if session.expires_at < datetime.utcnow():
            self.db.delete(session)
            self.db.commit()
            return None
        return session.user

    def delete_session(self, token: str) -> bool:
        session = self.db.query(Session).filter(Session.token == token).first()
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
```

**Step 6: Run tests**

```bash
python -m pytest tests/test_auth_service.py -v
```

Expected: 5 passed

**Step 7: Commit**

```bash
git add backend/ tests/
git commit -m "feat: add auth service with session management"
```

---

### Task 8: FastAPI App Entry Point

**Files:**
- Create: `backend/main.py`
- Create: `backend/dependencies.py`
- Test: `tests/test_main.py`

**Step 1: Create test**

Create `tests/test_main.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_main.py -v
```

Expected: FAIL

**Step 3: Create dependencies.py**

Create `backend/dependencies.py`:

```python
from typing import Generator
from sqlalchemy.orm import Session as DBSession

from backend.database import get_engine, get_session_maker, Base
from backend.config import settings

engine = get_engine(settings.database_url)
SessionLocal = get_session_maker(engine)

# Create tables
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[DBSession, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 4: Create main.py**

Create `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Nebulus Gantry", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Step 5: Run tests**

```bash
python -m pytest tests/test_main.py -v
```

Expected: 1 passed

**Step 6: Commit**

```bash
git add backend/ tests/
git commit -m "feat: add FastAPI app entry point"
```

---

### Task 9: Auth Routes

**Files:**
- Create: `backend/routers/auth.py`
- Create: `backend/schemas/auth.py`
- Modify: `backend/main.py`
- Test: `tests/test_auth_routes.py`

**Step 1: Create test**

Create `tests/test_auth_routes.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base
from backend.dependencies import get_db
from backend.services.auth_service import AuthService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
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
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_auth_routes.py -v
```

Expected: FAIL

**Step 3: Create schemas directory and auth schemas**

```bash
mkdir -p backend/schemas
touch backend/schemas/__init__.py
```

Create `backend/schemas/auth.py`:

```python
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str

    class Config:
        from_attributes = True
```

**Step 4: Create auth router**

Create `backend/routers/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.services.auth_service import AuthService
from backend.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(db: DBSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(request: Request, auth: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = auth.validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return user


@router.post("/login")
def login(data: LoginRequest, response: Response, auth: AuthService = Depends(get_auth_service)):
    user = auth.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_session(user.id)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400  # 24 hours
    )
    return {"message": "Login successful"}


@router.post("/logout")
def logout(request: Request, response: Response, auth: AuthService = Depends(get_auth_service)):
    token = request.cookies.get("session_token")
    if token:
        auth.delete_session(token)
    response.delete_cookie("session_token")
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_me(user=Depends(get_current_user)):
    return user
```

**Step 5: Update main.py to include router**

Update `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth

app = FastAPI(title="Nebulus Gantry", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

**Step 6: Run tests**

```bash
python -m pytest tests/test_auth_routes.py -v
```

Expected: 5 passed

**Step 7: Commit**

```bash
git add backend/ tests/
git commit -m "feat: add auth routes (login, logout, me)"
```

---

## Phase 3: Frontend Core

### Task 10: Frontend Project Structure

**Files:**
- Create: `frontend/src/` directory structure
- Delete: Vite boilerplate files

**Step 1: Clean up Vite boilerplate**

```bash
cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/.worktrees/gantry-v2/frontend
rm -f src/App.css src/assets/react.svg
rm -rf public/vite.svg
```

**Step 2: Create directory structure**

```bash
mkdir -p src/{components,pages,hooks,services,stores,types}
touch src/components/.gitkeep
touch src/pages/.gitkeep
touch src/hooks/.gitkeep
touch src/services/.gitkeep
touch src/stores/.gitkeep
touch src/types/.gitkeep
```

**Step 3: Commit**

```bash
git add -A
git commit -m "chore: set up frontend directory structure"
```

---

### Task 11: API Client

**Files:**
- Create: `frontend/src/services/api.ts`
- Create: `frontend/src/types/api.ts`

**Step 1: Create types**

Create `frontend/src/types/api.ts`:

```typescript
export interface User {
  id: number;
  email: string;
  display_name: string;
  role: 'user' | 'admin';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ApiError {
  detail: string;
}
```

**Step 2: Create API client**

Create `frontend/src/services/api.ts`:

```typescript
import type { User, LoginRequest, Conversation, Message } from '../types/api';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const authApi = {
  login: (data: LoginRequest) =>
    fetchApi<{ message: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  logout: () =>
    fetchApi<{ message: string }>('/api/auth/logout', {
      method: 'POST',
    }),

  me: () => fetchApi<User>('/api/auth/me'),
};

export const chatApi = {
  getConversations: () => fetchApi<Conversation[]>('/api/chat/conversations'),

  getConversation: (id: number) =>
    fetchApi<{ conversation: Conversation; messages: Message[] }>(
      `/api/chat/conversations/${id}`
    ),

  createConversation: () =>
    fetchApi<Conversation>('/api/chat/conversations', {
      method: 'POST',
    }),

  deleteConversation: (id: number) =>
    fetchApi<{ message: string }>(`/api/chat/conversations/${id}`, {
      method: 'DELETE',
    }),

  sendMessage: async function* (conversationId: number, content: string) {
    const response = await fetch(
      `${API_URL}/api/chat/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield decoder.decode(value);
    }
  },
};
```

**Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add API client with auth and chat services"
```

---

### Task 12: Auth Store

**Files:**
- Create: `frontend/src/stores/authStore.ts`

**Step 1: Create auth store**

Create `frontend/src/stores/authStore.ts`:

```typescript
import { create } from 'zustand';
import type { User } from '../types/api';
import { authApi } from '../services/api';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.login({ email, password });
      const user = await authApi.me();
      set({ user, isLoading: false });
    } catch (err) {
      set({ error: (err as Error).message, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } finally {
      set({ user: null });
    }
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await authApi.me();
      set({ user, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },
}));
```

**Step 2: Commit**

```bash
git add frontend/src/stores/
git commit -m "feat: add auth store with Zustand"
```

---

### Task 13: Login Page

**Files:**
- Create: `frontend/src/pages/Login.tsx`
- Create: `frontend/src/components/Input.tsx`
- Create: `frontend/src/components/Button.tsx`

**Step 1: Create Input component**

Create `frontend/src/components/Input.tsx`:

```typescript
import { InputHTMLAttributes, forwardRef } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, ...props }, ref) => {
    return (
      <div className="space-y-1">
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
        <input
          ref={ref}
          className={`
            w-full px-3 py-2 border rounded-lg
            focus:outline-none focus:ring-2 focus:ring-blue-500
            ${error ? 'border-red-500' : 'border-gray-300'}
          `}
          {...props}
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
    );
  }
);

Input.displayName = 'Input';
```

**Step 2: Create Button component**

Create `frontend/src/components/Button.tsx`:

```typescript
import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary';
  isLoading?: boolean;
}

export function Button({
  children,
  variant = 'primary',
  isLoading,
  disabled,
  ...props
}: ButtonProps) {
  const baseStyles = 'px-4 py-2 rounded-lg font-medium transition-colors';
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300',
    secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300 disabled:bg-gray-100',
  };

  return (
    <button
      className={`${baseStyles} ${variants[variant]}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? 'Loading...' : children}
    </button>
  );
}
```

**Step 3: Create Login page**

Create `frontend/src/pages/Login.tsx`:

```typescript
import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Input } from '../components/Input';
import { Button } from '../components/Button';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-lg">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Nebulus Gantry</h1>
          <p className="mt-2 text-gray-600">Sign in to continue</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg">
              {error}
            </div>
          )}

          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <Button type="submit" className="w-full" isLoading={isLoading}>
            Sign in
          </Button>
        </form>
      </div>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Login page with Input and Button components"
```

---

### Task 14: App Layout and Routing

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1: Create Layout component**

Create `frontend/src/components/Layout.tsx`:

```typescript
import { ReactNode } from 'react';
import { useAuthStore } from '../stores/authStore';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">
            Nebulus Gantry
          </h1>

          {user && (
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">{user.display_name}</span>
              <button
                onClick={() => logout()}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main content */}
      <main>{children}</main>
    </div>
  );
}
```

**Step 2: Create ProtectedRoute component**

Create `frontend/src/components/ProtectedRoute.tsx`:

```typescript
import { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

**Step 3: Create placeholder Chat page**

Create `frontend/src/pages/Chat.tsx`:

```typescript
export function Chat() {
  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar placeholder */}
      <div className="w-64 bg-gray-100 border-r border-gray-200 p-4">
        <button className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg">
          + New Chat
        </button>
        <div className="mt-4 text-sm text-gray-500">
          Conversations will appear here
        </div>
      </div>

      {/* Chat area placeholder */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <h2 className="text-2xl font-semibold text-gray-700">
          Welcome to Nebulus Gantry
        </h2>
        <p className="mt-2 text-gray-500">
          Start a new conversation or select an existing one
        </p>
      </div>
    </div>
  );
}
```

**Step 4: Update App.tsx**

Replace `frontend/src/App.tsx`:

```typescript
import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useAuthStore } from './stores/authStore';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Chat } from './pages/Chat';

function App() {
  const checkAuth = useAuthStore((state) => state.checkAuth);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Chat />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

**Step 5: Verify frontend compiles**

```bash
cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry/.worktrees/gantry-v2/frontend
npm run build
```

Expected: Build succeeds

**Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app layout, routing, and protected routes"
```

---

## Phase 4: Chat Implementation

### Task 15: Chat Routes (Backend)

**Files:**
- Create: `backend/routers/chat.py`
- Create: `backend/schemas/chat.py`
- Create: `backend/services/chat_service.py`
- Modify: `backend/main.py`
- Test: `tests/test_chat_routes.py`

*[Continue with similar detailed steps for remaining tasks...]*

---

## Remaining Tasks (Summary)

### Phase 4: Chat Implementation
- Task 15: Chat Routes (Backend)
- Task 16: Chat Service with streaming
- Task 17: Conversation Sidebar (Frontend)
- Task 18: Chat View (Frontend)
- Task 19: Message Input and Streaming

### Phase 5: Long-Term Memory
- Task 20: Memory Service (ChromaDB integration)
- Task 21: Graph Service (NetworkX integration)
- Task 22: LTM Context Injection

### Phase 6: Admin Panel
- Task 23: Admin Routes (Backend)
- Task 24: User Management API
- Task 25: Service Control API (Docker)
- Task 26: Model Management API
- Task 27: Admin Panel UI (Frontend)

### Phase 7: Polish
- Task 28: Error handling and toasts
- Task 29: Search functionality
- Task 30: Settings page
- Task 31: Final styling pass
- Task 32: Documentation update

---

## Verification Checklist

After each phase:
- [ ] All tests pass
- [ ] Frontend builds without errors
- [ ] Docker compose up works
- [ ] Manual smoke test passes
