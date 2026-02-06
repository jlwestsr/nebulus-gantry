# Development Setup

Complete guide for setting up a local development environment for Nebulus Gantry, including hot reload, debugging tools, and development workflows.

---

## Prerequisites

### Required Software

- **Python 3.12+** - [Download](https://www.python.org/downloads/)
- **Node.js 20+** - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **Docker & Docker Compose** - [Download](https://www.docker.com/products/docker-desktop/)

### Recommended Tools

- **VS Code** - Primary editor
- **Python extension** - For Python debugging
- **ESLint extension** - For JavaScript/TypeScript linting
- **Prettier** - Code formatting
- **REST Client** or **Postman** - API testing

---

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/jlwestsr/nebulus-gantry.git
cd nebulus-gantry
```

### 2. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Test hooks
pre-commit run --all-files
```

Hooks configured:

- Trailing whitespace removal
- End of file fixing
- YAML validation
- Markdown linting
- Python linting (flake8)
- JavaScript linting (ESLint)
- Python testing (pytest)

### 3. Configure Environment Variables

```bash
# Create .env file in project root
cat > .env << 'EOF'
# Database
DATABASE_URL=sqlite:///./data/gantry.db

# External Services
CHROMA_HOST=http://localhost:8001
TABBY_HOST=http://localhost:5000

# Security
SECRET_KEY=dev-secret-key-change-in-production
SESSION_EXPIRE_HOURS=24

# Frontend (used at build time)
VITE_API_URL=http://localhost:8000

# Development
DEBUG=true
LOG_LEVEL=DEBUG
EOF
```

---

## Backend Development

### Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov black flake8 ipython
```

### Run Development Server

```bash
# With hot reload (recommended)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# With specific log level
uvicorn backend.main:app --reload --log-level debug

# Alternative: use the convenience script
python -m backend.main
```

**Hot reload:** Server automatically restarts when you modify Python files.

### Project Structure

```text
backend/
├── routers/           # API endpoints
├── services/          # Business logic
├── models/            # Database models
├── schemas/           # Pydantic schemas
├── tests/             # Test files
├── main.py            # Application entry
├── config.py          # Configuration
├── database.py        # Database setup
└── dependencies.py    # FastAPI dependencies
```

### Database Management

#### Initialize Database

```bash
# Database auto-creates on first run
# Or manually initialize:
python -c "
from backend.database import get_engine, Base
from backend.models import *  # Import all models
engine = get_engine()
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

#### Create Test User

```bash
python -c "
from backend.services.auth_service import AuthService
from backend.database import get_engine, get_session_maker

engine = get_engine()
Session = get_session_maker(engine)
db = Session()
auth = AuthService(db)

user = auth.create_user(
    email='dev@localhost',
    password='dev123',
    role='admin',
    display_name='Dev User'
)

print(f'Created: {user.email}')
db.close()
"
```

#### Database Migrations

Currently using SQLAlchemy metadata for schema creation. For production, consider Alembic:

```bash
# Install Alembic
pip install alembic

# Initialize
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

### Code Style

#### Python Formatting

```bash
# Format with black
black backend/

# Check with flake8
flake8 backend/

# Type checking (optional)
pip install mypy
mypy backend/
```

#### Configuration

`.flake8`:

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, E266, E501, W503
exclude = .git,__pycache__,venv
```

### Debugging

#### VS Code Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI Backend",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.main:app",
        "--reload",
        "--port", "8000"
      ],
      "jinja": true,
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  ]
}
```

#### Interactive Debugging

```python
# Add breakpoint in code
import ipdb; ipdb.set_trace()

# Or use built-in
breakpoint()
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use throughout code
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### API Testing

#### Using httpie

```bash
# Install
pip install httpie

# Login
http POST localhost:8000/api/auth/login \
  email=dev@localhost password=dev123 \
  --session=dev

# Use session
http GET localhost:8000/api/chat/conversations \
  --session=dev
```

#### Using VS Code REST Client

Create `api-tests.http`:

```http
### Login
POST http://localhost:8000/api/auth/login
Content-Type: application/json

{
  "email": "dev@localhost",
  "password": "dev123"
}

### Get Conversations
GET http://localhost:8000/api/chat/conversations

### Create Conversation
POST http://localhost:8000/api/chat/conversations
Content-Type: application/json

{
  "title": "Test Conversation"
}
```

---

## Frontend Development

### Setup

```bash
cd frontend

# Install dependencies
npm install

# Install dev dependencies (if not in package.json)
npm install -D @types/node @types/react @types/react-dom
```

### Run Development Server

```bash
# Start dev server (hot reload enabled)
npm run dev

# Server will start on http://localhost:5173
```

**Hot reload:** Browser automatically updates when you modify files.

### Project Structure

```text
frontend/
├── src/
│   ├── components/    # Reusable components
│   ├── pages/         # Page components
│   ├── stores/        # Zustand state
│   ├── services/      # API client
│   ├── types/         # TypeScript types
│   ├── hooks/         # Custom hooks
│   ├── utils/         # Utilities
│   ├── App.tsx        # Root component
│   └── main.tsx       # Entry point
├── public/            # Static assets
├── vite.config.ts     # Vite config
└── tsconfig.json      # TypeScript config
```

### Code Style

#### TypeScript Formatting

```bash
# Format with Prettier
npm run format

# Check formatting
npm run format:check

# Lint with ESLint
npm run lint

# Fix lint errors
npm run lint:fix
```

#### ESLint Configuration

`.eslintrc.cjs`:

```javascript
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  parser: '@typescript-eslint/parser',
  plugins: ['@typescript-eslint', 'react'],
  rules: {
    'react/react-in-jsx-scope': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
  },
};
```

### State Management

Using Zustand:

```typescript
// stores/exampleStore.ts
import { create } from 'zustand';

interface ExampleStore {
  count: number;
  increment: () => void;
  decrement: () => void;
}

export const useExampleStore = create<ExampleStore>((set) => ({
  count: 0,
  increment: () => set((state) => ({ count: state.count + 1 })),
  decrement: () => set((state) => ({ count: state.count - 1 })),
}));

// Usage in component
import { useExampleStore } from '@/stores/exampleStore';

function Counter() {
  const { count, increment } = useExampleStore();
  return <button onClick={increment}>{count}</button>;
}
```

### Debugging

#### Browser DevTools

- **React DevTools** - Inspect component tree
- **Redux DevTools** - Works with Zustand
- **Network tab** - Monitor API calls

#### VS Code Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Chrome",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend/src",
      "sourceMapPathOverrides": {
        "webpack:///src/*": "${webRoot}/*"
      }
    }
  ]
}
```

### Component Development

#### Creating New Component

```typescript
// components/Example/Example.tsx
import { FC } from 'react';

interface ExampleProps {
  title: string;
  onClick?: () => void;
}

export const Example: FC<ExampleProps> = ({ title, onClick }) => {
  return (
    <div className="p-4 bg-gray-800 rounded">
      <h2 className="text-xl font-bold">{title}</h2>
      {onClick && (
        <button onClick={onClick} className="mt-2 px-4 py-2 bg-blue-600 rounded">
          Click Me
        </button>
      )}
    </div>
  );
};

// components/Example/index.ts
export { Example } from './Example';
```

#### Styling with Tailwind

```typescript
// Use Tailwind classes
<div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
  <h1 className="text-2xl font-bold text-white">Title</h1>
  <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded">
    Action
  </button>
</div>

// Custom classes in CSS if needed
// globals.css
@layer components {
  .btn-primary {
    @apply px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white;
  }
}
```

---

## Full-Stack Development

### Running Both Backend and Frontend

#### Option 1: Separate Terminals

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn backend.main:app --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

#### Option 2: Docker Compose

```bash
# Run entire stack
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

#### Option 3: Process Manager

```bash
# Install concurrently
npm install -g concurrently

# Add to package.json scripts
"scripts": {
  "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\"",
  "dev:backend": "cd backend && uvicorn backend.main:app --reload",
  "dev:frontend": "cd frontend && npm run dev"
}

# Run both
npm run dev
```

### API Development Workflow

1. **Define Schema** (`backend/schemas/`)

   ```python
   # schemas/example.py
   from pydantic import BaseModel

   class ExampleRequest(BaseModel):
       name: str
       value: int

   class ExampleResponse(BaseModel):
       id: int
       name: str
       value: int
   ```

2. **Create Service** (`backend/services/`)

   ```python
   # services/example_service.py
   class ExampleService:
       def __init__(self, db: Session):
           self.db = db

       def create(self, request: ExampleRequest):
           # Business logic
           pass
   ```

3. **Add Router** (`backend/routers/`)

   ```python
   # routers/example.py
   @router.post("/example", response_model=ExampleResponse)
   def create_example(
       request: ExampleRequest,
       service: ExampleService = Depends()
   ):
       return service.create(request)
   ```

4. **Update Frontend Types** (`frontend/src/types/`)

   ```typescript
   // types/example.ts
   export interface ExampleRequest {
     name: string;
     value: number;
   }

   export interface ExampleResponse {
     id: number;
     name: string;
     value: number;
   }
   ```

5. **Add API Client Method** (`frontend/src/services/`)

   ```typescript
   // services/api.ts
   async createExample(data: ExampleRequest): Promise<ExampleResponse> {
     return this.post('/example', data);
   }
   ```

6. **Use in Component**

   ```typescript
   // components/ExampleForm.tsx
   const handleSubmit = async () => {
     const result = await api.createExample({ name: 'test', value: 42 });
     console.log(result);
   };
   ```

---

## Testing Development

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest backend/tests/test_auth.py

# Run specific test
pytest backend/tests/test_auth.py::test_login

# Run with verbose output
pytest -v

# Run with print output
pytest -s
```

### Frontend Tests

```bash
# Run tests (if configured)
npm test

# Run with coverage
npm test -- --coverage
```

### Writing Tests

See [Testing](Testing) documentation for detailed guide.

---

## Common Development Tasks

### Adding a New Feature

1. Create feature branch

   ```bash
   git checkout -b feat/new-feature
   ```

2. Implement backend

   - Add models
   - Add schemas
   - Add service
   - Add router
   - Add tests

3. Implement frontend

   - Add types
   - Add API method
   - Add components
   - Add store (if needed)

4. Test locally

   ```bash
   pytest
   npm run lint
   ```

5. Commit and push

   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feat/new-feature
   ```

### Debugging Common Issues

#### Backend not starting

```bash
# Check Python path
python --version

# Check dependencies
pip list

# Check database
ls -la data/gantry.db

# Check logs
uvicorn backend.main:app --reload --log-level debug
```

#### Frontend not connecting

```bash
# Check API URL
echo $VITE_API_URL

# Check CORS in backend
# backend/main.py should allow http://localhost:5173

# Check browser console for errors
```

#### Database locked

```bash
# Stop all processes using database
docker compose down

# Delete database and recreate
rm data/gantry.db
# Restart backend to recreate
```

---

## IDE Setup

### VS Code Extensions

**Required:**

- Python (ms-python.python)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)

**Recommended:**

- GitLens (eamodio.gitlens)
- REST Client (humao.rest-client)
- Docker (ms-azuretools.vscode-docker)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)
- Error Lens (usernamehw.errorlens)

### Settings

`.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

---

## Performance Tips

### Backend

- Use async/await for I/O operations
- Enable connection pooling
- Use database indexes
- Profile slow endpoints with `cProfile`

### Frontend

- Use React.memo for expensive components
- Lazy load routes
- Debounce user input
- Virtual scrolling for long lists

---

## Environment Variables Reference

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./data/gantry.db` |
| `CHROMA_HOST` | ChromaDB URL | `http://localhost:8001` |
| `TABBY_HOST` | LLM API URL | `http://localhost:5000` |
| `SECRET_KEY` | Session signing key | (required) |
| `SESSION_EXPIRE_HOURS` | Session lifetime | `24` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

---

## Related Documentation

- **[Testing](Testing)** - Running and writing tests
- **[Contributing](Contributing)** - Contribution guidelines
- **[API Reference](API-Reference)** - Complete API documentation

---

**[← Back to API Reference](API-Reference)** | **[Next: Testing →](Testing)**
