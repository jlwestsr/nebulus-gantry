# Admin Dashboard

Complete guide to Gantry's admin control plane for managing users, switching models, monitoring services, and viewing system logs.

---

## Overview

The **Admin Dashboard** provides comprehensive system management tools for administrators:

- **User Management** - Create, update, delete user accounts
- **Model Switching** - Hot-swap LLMs without restarting (TabbyAPI)
- **Service Monitoring** - View Docker container status
- **Log Streaming** - Real-time logs from all services
- **System Personas** - Create shared AI personas for all users
- **Bulk Export** - Download all conversations for backup/compliance

**Access requirement:** Admin role only

---

## Accessing the Dashboard

### Login as Admin

1. **Log in** to Gantry with admin credentials
2. **Click profile icon** in top-right corner
3. Select **Admin Dashboard** from dropdown
4. Dashboard opens in new view

**Tabs available:**

- 👥 **Users** - User account management
- 🤖 **Models** - LLM model switching
- 🐳 **Services** - Docker container monitoring
- 📋 **Logs** - Real-time log streaming
- 🎭 **Personas** - System-wide AI personas
- 📦 **Export** - Bulk conversation export

---

## User Management

### Overview Tab

**View all users:**

- Email address
- Display name
- Role (admin/user)
- Account creation date
- Last login timestamp
- Active sessions count

**Actions:**

- ✏️ **Edit** - Modify user details
- 🔑 **Reset Password** - Change user password
- 🗑️ **Delete** - Remove user account

### Create New User

1. **Click "Create User"** button
2. **Fill in form:**
   - **Email** (required): User's email address
   - **Password** (required): Initial password (min 8 chars)
   - **Display Name** (required): Shown in UI
   - **Role** (required): `user` or `admin`
3. **Click "Create"**

**Example:**

```text
Email: alice@company.com
Password: SecurePass123!
Display Name: Alice Johnson
Role: user
```

**User receives:**

- Account created
- Can log in immediately
- Email notifications (future feature)

### Edit User

1. **Click edit icon** next to user
2. **Modify fields:**
   - Display name
   - Role (user ↔ admin)
   - Password (leave blank to keep current)
3. **Click "Save Changes"**

**Note:** Cannot edit email address (immutable)

### Delete User

**Warning:** Deletion is permanent!

1. **Click delete icon** next to user
2. **Confirm in dialog**
3. **User removed:**
   - Account deleted from database
   - All conversations deleted
   - All sessions invalidated
   - All documents deleted
   - All memories erased from ChromaDB

**Cannot delete:**

- Yourself (logged-in admin)
- Must have at least one admin account

**Best practice:** Export user's conversations before deletion if needed for records.

### Reset Password

1. **Click "Reset Password"** for user
2. **Enter new password** (min 8 chars)
3. **Click "Update"**
4. **User's password changed immediately**

**User impact:**

- All existing sessions invalidated
- Must log in again with new password

### Role Permissions

**Admin role can:**

- ✅ Access admin dashboard
- ✅ Create/edit/delete users
- ✅ Switch models
- ✅ View all services
- ✅ Stream logs
- ✅ Create system personas
- ✅ Bulk export conversations

**User role can:**

- ✅ Use chat interface
- ✅ Upload documents
- ✅ Create personal personas
- ✅ Export own conversations
- ❌ Access admin dashboard
- ❌ Manage other users
- ❌ Switch models
- ❌ View system logs

---

## Model Management

### Supported Backends

**Model switching requires:**

- **TabbyAPI** as LLM backend
- TabbyAPI accessible at `TABBY_HOST`
- Multiple models available in TabbyAPI's `models/` directory

**Not supported:**

- Ollama (no hot-swap API)
- vLLM (requires restart)
- Other backends (no standard model switching API)

### View Available Models

**Models tab shows:**

- Model ID (directory name in TabbyAPI)
- Model name (display name)
- Active status (✓ if currently loaded)
- Load status indicator

**Example:**

```text
Models:
✓ Qwen2.5-Coder-7B-Instruct    (Active)
  Llama-3.1-8B-Instruct
  Mistral-7B-Instruct-v0.3
  DeepSeek-Coder-6.7B
```

### Switch Model

1. **Click "Switch" button** next to model
2. **Confirm action** in dialog
3. **Wait for model loading** (10-60 seconds)
4. **Status updates:**
   - "Unloading current model..."
   - "Loading new model..."
   - "Model switched successfully"

**What happens:**

- TabbyAPI unloads current model from VRAM
- Loads new model into VRAM
- All existing conversations continue
- New messages use new model

**Switching time:**

| Model Size | Load Time |
|------------|-----------|
| 3B params | 5-10 seconds |
| 7B params | 10-30 seconds |
| 13B params | 30-60 seconds |
| 34B+ params | 60-120 seconds |

**During switch:**

- Chat interface remains accessible
- New messages queued until model ready
- Streaming responses resume after load

### Unload Model

**Free VRAM** without loading a new model:

1. **Click "Unload Model"** button
2. **Confirm action**
3. **Current model unloaded from VRAM**

**Use cases:**

- Free memory for other tasks
- Prepare for manual model change
- Troubleshoot model issues

**Impact:**

- Chat unavailable until new model loaded
- Users see "Model not available" message

### Model Metadata

**Future feature:** Display model details

- Parameter count
- Context window size
- Quantization (Q4, Q5, Q8)
- VRAM usage
- Supported features (function calling, etc.)

---

## Service Monitoring

### Docker Integration

**Gantry monitors services via Docker API:**

- Backend container
- Frontend container
- ChromaDB container
- TabbyAPI container (if on same network)
- Any other containers on `nebulus-prime_ai-network`

**Requirements:**

- Docker socket mounted: `/var/run/docker.sock`
- Backend has Docker API access
- Services on same Docker network

### View Service Status

**Services tab shows:**

| Service | Status | Container ID | Uptime | Actions |
|---------|--------|--------------|--------|---------|
| backend | Running | a1b2c3d4 | 2 hours | Restart |
| frontend | Running | e5f6g7h8 | 2 hours | Restart |
| chromadb | Running | i9j0k1l2 | 5 days | Restart |
| tabbyapi | Running | m3n4o5p6 | 1 day | Restart |

**Status indicators:**

- 🟢 **Running** - Service healthy
- 🔴 **Stopped** - Service not running
- 🟡 **Restarting** - Service restarting
- ⚪ **Unknown** - Cannot determine status

### Restart Service

**Restart individual services:**

1. **Click "Restart"** next to service
2. **Confirm action**
3. **Service restarts** (5-30 seconds)

**Common use cases:**

- Apply configuration changes
- Recover from crash
- Clear stuck state

**Impact by service:**

**Backend restart:**

- Active chat sessions interrupted
- Users must refresh page
- Sessions preserved (cookie-based)

**Frontend restart:**

- UI briefly unavailable
- Browsers automatically reconnect
- No data loss

**ChromaDB restart:**

- Memory/document search temporarily unavailable
- Resumes automatically when service recovers
- No data loss (persistent storage)

**TabbyAPI restart:**

- LLM unavailable during restart
- Current model must reload (~30 seconds)
- Chat queue pauses

### Service Health Checks

**Automatic monitoring:**

- Services polled every 30 seconds
- Status updates in real-time
- Alerts shown for unhealthy services

**Manual refresh:**

- Click **Refresh** button
- Updates all service statuses

---

## Log Streaming

### Access Logs

**Logs tab provides:**

- Real-time log streaming via Server-Sent Events (SSE)
- Filter by service
- Search within logs
- Download logs as file

### Stream Service Logs

1. **Select service** from dropdown:
   - backend
   - frontend
   - chromadb
   - tabbyapi
   - (any container on network)

2. **Click "Start Streaming"**

3. **Logs appear** in console view:

```text
[2026-02-06 10:45:32] INFO: User 'admin@example.com' logged in
[2026-02-06 10:45:40] INFO: Conversation 42 created
[2026-02-06 10:45:42] INFO: Message sent to LLM API
[2026-02-06 10:45:45] INFO: Streaming response started
```

**Log levels:**

- 🔵 **DEBUG** - Detailed diagnostic info
- 🟢 **INFO** - Normal operation events
- 🟡 **WARNING** - Non-critical issues
- 🔴 **ERROR** - Errors requiring attention
- ⚫ **CRITICAL** - Severe failures

### Filter Logs

**By log level:**

- Click level badges (INFO, WARNING, ERROR)
- Filters out other levels

**By search term:**

- Enter text in search box
- Highlights matching lines
- Hides non-matching lines

**Example searches:**

```text
"User 5" - All events for user ID 5
"ChromaDB" - All ChromaDB-related logs
"ERROR" - All error messages
"conversation_42" - Specific conversation logs
```

### Download Logs

1. **Click "Download Logs"** button
2. **Choose time range:**
   - Last 1 hour
   - Last 24 hours
   - Last 7 days
   - Custom range

3. **Logs downloaded** as `.log` file

**Format:**

```text
gantry-backend-2026-02-06.log
```

**Use cases:**

- Debugging issues
- Audit trails
- Compliance records

### Log Rotation

**Backend logs:**

- Docker logs auto-rotate (10MB per file, 3 files max)
- Older logs discarded
- Configure in `docker-compose.yml`

**Persistent logging:**

Add to `docker-compose.yml`:

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "10"
```

---

## System Personas

### What Are Personas?

**Personas** are pre-configured AI personalities with:

- Custom system prompts
- Temperature settings
- Model preferences
- Default behaviors

**Types:**

- **System personas:** Created by admins, available to all users
- **Personal personas:** Created by users, private to creator

### Create System Persona

1. **Navigate to Personas tab**
2. **Click "Create System Persona"**
3. **Fill in form:**

   - **Name** (required): "Python Expert"
   - **Description**: "Specialized in Python development"
   - **System Prompt**: "You are an expert Python developer with deep knowledge of..."
   - **Temperature** (0.0-1.0): 0.7
   - **Model ID** (optional): Specific model to use

4. **Click "Create"**

**System persona created!** All users can now select it in chat.

### Edit System Persona

1. **Click edit icon** next to persona
2. **Modify fields**
3. **Click "Save Changes"**

**Changes apply immediately** to all users.

### Delete System Persona

1. **Click delete icon**
2. **Confirm deletion**
3. **Persona removed** from all users' lists

**Impact:**

- Conversations using this persona continue normally
- Persona no longer selectable for new conversations

### Example Personas

**Python Expert:**

```text
System Prompt: "You are an expert Python developer with deep knowledge
of the Python ecosystem, best practices, and common libraries. You
provide clear, concise code examples and explain concepts thoroughly."

Temperature: 0.5 (focused, consistent)
```

**Creative Writer:**

```text
System Prompt: "You are a creative writing assistant specializing in
fiction, poetry, and storytelling. You help writers develop characters,
plots, and vivid descriptions."

Temperature: 0.9 (creative, varied)
```

**Technical Documenter:**

```text
System Prompt: "You are a technical documentation expert. You write
clear, structured documentation with proper formatting, code examples,
and troubleshooting sections."

Temperature: 0.3 (precise, consistent)
```

---

## Bulk Export

### Export All Conversations

**Use cases:**

- Backup before major update
- Compliance requirements
- Data migration
- Audit archives

### Perform Bulk Export

1. **Navigate to Export tab**
2. **Set filters** (optional):
   - **User ID:** Export specific user's conversations
   - **Date from:** Start date
   - **Date to:** End date
3. **Click "Export"**
4. **ZIP file downloads** containing JSON exports

**Export format:**

```text
conversations-export.zip
├── conversation-1.json
├── conversation-2.json
├── conversation-3.json
└── ...
```

**Each JSON file contains:**

```json
{
  "id": 1,
  "user_id": 5,
  "title": "Python Best Practices",
  "created_at": "2026-02-01T10:00:00Z",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "What are Python best practices?",
      "timestamp": "2026-02-01T10:00:05Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "Here are key Python best practices...",
      "timestamp": "2026-02-01T10:00:10Z"
    }
  ]
}
```

### Filter Options

**By user:**

```text
User ID: 5
→ Exports only conversations from user 5
```

**By date range:**

```text
Date from: 2026-01-01
Date to: 2026-02-01
→ Exports conversations created in January 2026
```

**All conversations:**

```text
(Leave filters empty)
→ Exports entire conversation database
```

### Export Size

**Typical sizes:**

- 100 conversations (1000 messages): ~1 MB
- 1000 conversations (10K messages): ~10 MB
- 10K conversations (100K messages): ~100 MB

**Large exports:**

- May take 30-60 seconds
- Browser shows download progress
- ZIP compression reduces size by ~50%

---

## Troubleshooting

### Cannot Access Dashboard

**Issue:** "Admin access required" error

**Fix:**

Verify admin role in database:

```bash
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models import User

engine = get_engine()
Session = get_session_maker(engine)
db = Session()

user = db.query(User).filter(User.email == 'admin@example.com').first()
print(f'User: {user.email}, Role: {user.role}')
"
```

If role is 'user', update to 'admin':

```bash
docker compose exec backend python -c "
from backend.database import get_engine, get_session_maker
from backend.models import User

engine = get_engine()
Session = get_session_maker(engine)
db = Session()

user = db.query(User).filter(User.email == 'admin@example.com').first()
user.role = 'admin'
db.commit()
print('Updated to admin role')
"
```

### Model Switching Fails

**Error:** "Failed to switch model"

**Checks:**

```bash
# 1. Verify TabbyAPI is running
curl http://your-tabby-host:5000/v1/models

# 2. Check model exists in TabbyAPI
curl http://your-tabby-host:5000/v1/models | jq

# 3. Check backend logs
docker compose logs backend | grep -i model

# 4. Verify TABBY_HOST in .env
cat .env | grep TABBY_HOST
```

**Common causes:**

- TabbyAPI unreachable
- Model name incorrect
- Insufficient VRAM
- Model loading timeout

### Service Monitoring Not Working

**Error:** "Docker is not available"

**Fix:**

Verify Docker socket is mounted:

```bash
# Check docker-compose.yml
cat docker-compose.yml | grep docker.sock

# Should see:
# volumes:
#   - /var/run/docker.sock:/var/run/docker.sock

# Test Docker access from container
docker compose exec backend docker ps
```

If error persists, restart backend:

```bash
docker compose restart backend
```

### Log Streaming Disconnects

**Issue:** Logs stop streaming after a few minutes.

**Causes:**

- Network timeout
- SSE connection limit
- Backend restart

**Solutions:**

- Click "Restart Streaming"
- Refresh browser page
- Check network connection

---

## Security Best Practices

### Admin Account Security

**Strong passwords:**

- Minimum 12 characters
- Mixed case letters
- Numbers and symbols
- Unique (not reused)

**Example strong password:**

```text
Gantry@2026!AdminSecure
```

**Generate secure password:**

```bash
# Linux/macOS
openssl rand -base64 24

# Python
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

### Session Management

**Admin sessions:**

- Expire after configured time (default: 24 hours)
- Invalidated on logout
- Separate from user sessions

**Best practices:**

- Log out when done
- Don't share admin credentials
- Use separate admin and user accounts

### Audit Trail

**Log all admin actions:**

- User creation/deletion
- Model switches
- Service restarts
- Bulk exports

**Check audit logs:**

```bash
docker compose logs backend | grep -i admin
```

**Example audit entries:**

```text
[2026-02-06 10:30:00] INFO: Admin 'admin@example.com' created user 'alice@company.com'
[2026-02-06 11:15:00] INFO: Admin 'admin@example.com' switched model to 'Llama-3.1-8B'
[2026-02-06 14:20:00] INFO: Admin 'admin@example.com' performed bulk export
```

---

## Advanced Configuration

### Customize Admin UI

**Future feature:** Admin UI customization

- Brand colors
- Logo upload
- Custom dashboard widgets
- Personalized metrics

### Admin API Access

**All admin functions available via REST API:**

**Example: Create user via API**

```bash
curl -X POST http://localhost:8000/api/admin/users \
  -H "Cookie: session_id=admin-session" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@company.com",
    "password": "SecurePass456!",
    "display_name": "Bob Smith",
    "role": "user"
  }'
```

**See:** [API Reference](API-Reference) for full admin API docs

### Multi-Admin Setup

**Multiple admin accounts:**

- Create additional admin users
- Each has full admin access
- Actions logged separately

**Best practice:**

- One admin per team member
- No shared admin credentials
- Track who performed each action

---

## Next Steps

- **[Model Switching](Model-Switching)** - Deep dive into model management
- **[Configuration](Configuration)** - Environment variables and settings
- **[API Reference](API-Reference)** - Admin API endpoints

---

**[← Back to Home](Home)** | **[Model Switching →](Model-Switching)**
