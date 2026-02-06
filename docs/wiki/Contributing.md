# Contributing

Thank you for considering contributing to Nebulus Gantry! This guide covers our development workflow, code standards, pull request process, and commit conventions.

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Development environment set up** - See [Development Setup](Development-Setup)
2. **Tests passing locally** - Run `pytest` and verify all pass
3. **Familiarity with the architecture** - Read [Architecture](Architecture)

### First-Time Contributors

Great issues for getting started:

- Look for issues labeled `good first issue`
- Documentation improvements
- Test coverage improvements
- Bug fixes

---

## Git Workflow

Nebulus Gantry uses a **trunk-based development** workflow with feature branches.

### Branch Strategy

```text
main          ●────────────────●────────────────● (production releases)
               \              ↑                ↑
develop         ●──●──●──●──●──●──●──●──●──●──● (integration branch)
                 \       ↑   \       ↑
feature           ●──●──●     ●──●──● (short-lived branches)
```

**Branch Roles:**

| Branch | Purpose | Protected | Merges From | Merges To |
|--------|---------|-----------|-------------|-----------|
| `main` | Stable releases | Yes | `develop` | - |
| `develop` | Integration | Yes | Feature branches | `main` |
| `feat/*` | New features | No | `develop` | `develop` |
| `fix/*` | Bug fixes | No | `develop` | `develop` |
| `docs/*` | Documentation | No | `develop` | `develop` |
| `chore/*` | Maintenance | No | `develop` | `develop` |

### Creating a Feature Branch

```bash
# 1. Update develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feat/your-feature-name

# 3. Make changes and commit
git add .
git commit -m "feat: add new feature"

# 4. Push to remote
git push origin feat/your-feature-name

# 5. Create pull request on GitHub
```

### Branch Naming

Use conventional prefixes:

- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `chore/` - Maintenance tasks (deps, config, etc.)
- `refactor/` - Code refactoring
- `test/` - Test additions or changes
- `perf/` - Performance improvements

**Examples:**

```bash
feat/add-multi-modal-support
fix/conversation-delete-cascade
docs/update-api-reference
chore/upgrade-dependencies
refactor/simplify-auth-service
test/add-document-service-tests
perf/optimize-vector-search
```

---

## Commit Conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Commit Message Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add conversation export` |
| `fix` | Bug fix | `fix: resolve session expiration bug` |
| `docs` | Documentation only | `docs: update installation guide` |
| `style` | Code style (formatting, no logic change) | `style: format with black` |
| `refactor` | Code refactoring | `refactor: simplify auth logic` |
| `perf` | Performance improvement | `perf: optimize database queries` |
| `test` | Add or update tests | `test: add chat service tests` |
| `chore` | Maintenance | `chore: update dependencies` |
| `build` | Build system changes | `build: update Dockerfile` |
| `ci` | CI/CD changes | `ci: add coverage reporting` |

### Scope (Optional)

Component being modified:

- `backend` - Backend changes
- `frontend` - Frontend changes
- `docs` - Documentation
- `tests` - Test changes
- `deps` - Dependencies

### Subject

- Use imperative mood ("add" not "added")
- No period at end
- Keep under 72 characters

### Examples

**Simple commit:**

```bash
git commit -m "feat: add conversation search functionality"
```

**With scope:**

```bash
git commit -m "fix(backend): resolve database connection pooling issue"
```

**With body:**

```bash
git commit -m "feat: add conversation export

Implements JSON and PDF export formats for conversations.
Includes admin bulk export functionality.

Closes #42"
```

**Breaking change:**

```bash
git commit -m "feat!: change API authentication to OAuth2

BREAKING CHANGE: Session-based auth replaced with OAuth2.
Clients must update authentication flow."
```

### Co-Authorship

When pair programming or working with AI:

```bash
git commit -m "feat: add new feature

Co-Authored-By: Partner Name <partner@example.com>
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Code Standards

### Python (Backend)

#### Style Guide

- **PEP 8** compliance
- **Black** for formatting (line length: 88)
- **Type hints** on all function signatures
- **Docstrings** on all public functions (Google style)

#### Example

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.user import User


class UserService:
    """Service for managing users.

    Handles user creation, authentication, and profile management.

    Attributes:
        db: Database session.
    """

    def __init__(self, db: Session):
        """Initialize UserService.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email address.

        Args:
            email: User's email address.

        Returns:
            User object if found, None otherwise.

        Example:
            >>> service = UserService(db)
            >>> user = service.get_user_by_email("user@example.com")
            >>> print(user.display_name)
            "John Doe"
        """
        return self.db.query(User).filter(User.email == email).first()

    def create_user(
        self,
        email: str,
        password: str,
        display_name: str,
        role: str = "user"
    ) -> User:
        """Create new user account.

        Args:
            email: Unique email address.
            password: Plain text password (will be hashed).
            display_name: User's display name.
            role: User role ('user' or 'admin'). Defaults to 'user'.

        Returns:
            Created user object.

        Raises:
            ValueError: If email already exists or password is weak.

        Example:
            >>> user = service.create_user(
            ...     email="new@example.com",
            ...     password="SecurePass123!",
            ...     display_name="New User"
            ... )
        """
        # Implementation
        pass
```

#### Formatting

```bash
# Format code
black backend/

# Check formatting
black --check backend/

# Lint
flake8 backend/

# Type check
mypy backend/
```

### TypeScript/React (Frontend)

#### Style Guide

- **ESLint** for linting
- **Prettier** for formatting
- **Functional components** with hooks
- **Type safety** - No `any` types
- **Named exports** for components

#### Example

```typescript
// components/UserProfile/UserProfile.tsx
import { FC, useState, useEffect } from 'react';
import { api } from '@/services/api';
import type { User } from '@/types/api';

interface UserProfileProps {
  userId: number;
  onUpdate?: (user: User) => void;
}

/**
 * User profile component.
 *
 * Displays and allows editing of user profile information.
 *
 * @param userId - ID of user to display
 * @param onUpdate - Callback when profile is updated
 */
export const UserProfile: FC<UserProfileProps> = ({ userId, onUpdate }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await api.getUser(userId);
        setUser(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [userId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>;
  }

  if (!user) {
    return null;
  }

  return (
    <div className="p-4 bg-gray-800 rounded">
      <h2 className="text-xl font-bold">{user.display_name}</h2>
      <p className="text-gray-400">{user.email}</p>
      {/* More profile content */}
    </div>
  );
};
```

#### Formatting

```bash
# Format code
npm run format

# Check formatting
npm run format:check

# Lint
npm run lint

# Fix lint errors
npm run lint:fix
```

### Documentation

- **Markdown** for all documentation
- **Code examples** in all guides
- **Cross-references** between related docs
- **Keep docs up to date** with code changes

---

## Testing Requirements

### Coverage Standards

- **New features:** Must include tests (80%+ coverage)
- **Bug fixes:** Must include regression test
- **Refactoring:** Maintain or improve existing coverage

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if configured)
cd frontend
npm test

# Pre-commit hook tests
pre-commit run --all-files
```

### Test Requirements

**Every pull request must:**

1. Include tests for new functionality
2. Not decrease overall coverage
3. Pass all existing tests
4. Pass pre-commit hooks

---

## Pull Request Process

### Creating a Pull Request

1. **Ensure branch is up to date**

   ```bash
   git checkout develop
   git pull origin develop
   git checkout feat/your-feature
   git rebase develop
   ```

2. **Run tests locally**

   ```bash
   pytest
   npm run lint
   pre-commit run --all-files
   ```

3. **Push to remote**

   ```bash
   git push origin feat/your-feature
   ```

4. **Create PR on GitHub**

   - Base branch: `develop`
   - Title: Descriptive summary (50 chars max)
   - Description: Use template below

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing

Describe how changes were tested:

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests passing locally

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review performed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] Tests added with good coverage
- [ ] All tests passing
- [ ] No new warnings
- [ ] Dependent changes merged

## Screenshots (if applicable)

Add screenshots for UI changes.

## Related Issues

Closes #123
Relates to #456
```

### Review Process

1. **Automated checks run**
   - Tests
   - Linting
   - Coverage

2. **Code review by maintainers**
   - At least one approval required
   - Address all comments

3. **Merge**
   - Squash and merge for feature branches
   - Preserve history for important changes

### Addressing Review Comments

```bash
# Make requested changes
git add .
git commit -m "refactor: address review comments"

# Push updates
git push origin feat/your-feature

# PR automatically updates
```

---

## Code Review Guidelines

### As a Reviewer

**What to look for:**

- **Correctness** - Does it work as intended?
- **Tests** - Are there adequate tests?
- **Style** - Does it follow conventions?
- **Performance** - Are there obvious bottlenecks?
- **Security** - Any security concerns?
- **Documentation** - Is it documented?

**How to give feedback:**

- Be respectful and constructive
- Explain the "why" behind suggestions
- Distinguish between requirements and suggestions
- Use examples to clarify points

**Example comments:**

```markdown
<!-- Good -->
Consider using `async/await` here for better readability:
```python
async def get_user(user_id: int) -> User:
    return await db.fetch_one(...)
```

This makes the async flow clearer.

<!-- Not helpful -->
Bad code. Fix this.

```text

### As a Contributor

**Responding to feedback:**

- Address all comments
- Ask for clarification if unclear
- Discuss disagreements respectfully
- Mark resolved comments

---

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** (v1.0.0) - Breaking changes
- **MINOR** (v0.1.0) - New features (backward compatible)
- **PATCH** (v0.0.1) - Bug fixes

### Creating a Release

**Maintainers only:**

```bash
# 1. Update develop
git checkout develop
git pull origin develop

# 2. Run full test suite
pytest
npm test

# 3. Update version in package files
# - backend/pyproject.toml
# - frontend/package.json

# 4. Update CHANGELOG.md
# Add all changes since last release

# 5. Merge to main
git checkout main
git merge --no-ff develop -m "release: v0.2.0"

# 6. Tag release
git tag -a v0.2.0 -m "Release v0.2.0"

# 7. Push
git push origin main --tags

# 8. Create GitHub release
# - Go to Releases > New Release
# - Select tag v0.2.0
# - Copy changelog section
# - Publish release
```

---

## Communication

### Where to Ask Questions

- **GitHub Discussions** - General questions
- **GitHub Issues** - Bug reports and feature requests
- **Pull Request Comments** - Code-specific questions

### Issue Guidelines

**Bug Report:**

```markdown
## Bug Description

Clear description of the bug.

## Steps to Reproduce

1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior

What should happen.

## Actual Behavior

What actually happens.

## Environment

- OS: Ubuntu 24.04
- Python: 3.12
- Node: 20.10
- Docker: 24.0.7

## Additional Context

Screenshots, logs, etc.
```

**Feature Request:**

```markdown
## Feature Description

Clear description of proposed feature.

## Use Case

Why is this feature needed?

## Proposed Solution

How should it work?

## Alternatives Considered

Other approaches you've thought of.
```

---

## Development Tips

### Pre-commit Hooks

Pre-commit hooks automatically run before each commit:

```bash
# Install
pre-commit install

# Run manually
pre-commit run --all-files

# Skip hooks (emergency only)
git commit --no-verify
```

### Hot Reload

Both backend and frontend support hot reload:

```bash
# Backend (uvicorn --reload)
# Changes to .py files automatically restart server

# Frontend (Vite dev server)
# Changes to .tsx/.ts files automatically refresh browser
```

### Debugging

```python
# Python
import ipdb; ipdb.set_trace()  # or breakpoint()

# JavaScript
debugger;  // Browser stops here
```

---

## Recognition

Contributors are recognized in:

- `CONTRIBUTORS.md` file
- GitHub contributors page
- Release notes

Significant contributions may be featured in project documentation.

---

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the community

### Enforcement

Violations can be reported to: <jason@westailabs.com>

Consequences for violations:

1. Warning
2. Temporary ban
3. Permanent ban

---

## Getting Help

- **Documentation** - Start here for most questions
- **Discussions** - Community Q&A
- **Issues** - Bug reports and feature requests
- **Email** - <jason@westailabs.com> for private matters

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Related Documentation

- **[Development Setup](Development-Setup)** - Setting up dev environment
- **[Testing](Testing)** - Writing and running tests
- **[Architecture](Architecture)** - Understanding the codebase

---

**Thank you for contributing to Nebulus Gantry!**

**[← Back to Testing](Testing)** | **[Next: Common Issues →](Common-Issues)**
