# Admin Log Streaming Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement SSE-based live log streaming from Docker containers to the Admin panel's Logs tab.

**Architecture:** Add a `stream_logs(service_name)` method to `DockerService` that yields Docker container log lines as an async generator. The existing placeholder endpoint in `admin.py` calls this method and returns an SSE `StreamingResponse`. The frontend `LogsTab.tsx` connects via `EventSource`, renders log lines in a scrollable terminal-style viewer with auto-scroll, and provides pause/clear controls.

**Tech Stack:** Docker SDK (`container.logs(stream=True)`), FastAPI `StreamingResponse` (SSE), React `useEffect` + `EventSource`, Tailwind CSS

---

### Task 1: Add `stream_logs` to DockerService

**Files:**

- Modify: `backend/services/docker_service.py`
- Test: `backend/tests/test_docker_service.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_docker_service.py`:

```python
class TestStreamLogs:
    """Test log streaming from Docker containers."""

    def test_stream_logs_returns_lines(self, mock_docker):
        """stream_logs yields log lines from a matching container."""
        mock_container = MagicMock()
        mock_container.name = "nebulus-gantry-api"
        mock_container.logs.return_value = [
            b"2026-02-03 INFO Starting server\n",
            b"2026-02-03 INFO Listening on :8000\n",
        ]
        mock_docker.return_value.containers.list.return_value = [mock_container]

        service = DockerService()
        lines = list(service.stream_logs("nebulus-gantry-api"))

        assert len(lines) == 2
        assert "Starting server" in lines[0]
        mock_container.logs.assert_called_once_with(
            stream=True, follow=True, tail=100, timestamps=True
        )

    def test_stream_logs_not_found_returns_empty(self, mock_docker):
        """stream_logs yields nothing when the container doesn't exist."""
        mock_docker.return_value.containers.list.return_value = []

        service = DockerService()
        lines = list(service.stream_logs("nonexistent"))

        assert lines == []

    def test_stream_logs_docker_unavailable(self):
        """stream_logs yields nothing when Docker is unavailable."""
        with patch("backend.services.docker_service.docker") as mock:
            mock.from_env.side_effect = Exception("Docker not available")
            service = DockerService()
            lines = list(service.stream_logs("any"))
            assert lines == []
```

**Step 2: Run test to verify it fails**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_docker_service.py::TestStreamLogs -v`
Expected: FAIL — `DockerService` has no `stream_logs` method

**Step 3: Write minimal implementation**

Add to `DockerService` in `backend/services/docker_service.py`:

```python
from typing import Generator

def stream_logs(
    self, service_name: str, tail: int = 100
) -> Generator[str, None, None]:
    """Stream log lines from a Docker container by name.

    Args:
        service_name: Container name to stream logs from.
        tail: Number of historical lines to include before following.

    Yields:
        Decoded log lines as strings.
    """
    if not self.available:
        return
    try:
        containers = self.client.containers.list(
            all=True, filters={"name": service_name}
        )
        if not containers:
            return
        for chunk in containers[0].logs(
            stream=True, follow=True, tail=tail, timestamps=True
        ):
            yield chunk.decode("utf-8", errors="replace").rstrip("\n")
    except Exception as e:
        logger.warning(f"Failed to stream logs for {service_name}: {e}")
```

**Step 4: Run test to verify it passes**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_docker_service.py::TestStreamLogs -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/services/docker_service.py backend/tests/test_docker_service.py
git commit -m "feat: add stream_logs method to DockerService"
```

---

### Task 2: Implement the SSE log streaming endpoint

**Files:**

- Modify: `backend/routers/admin.py`
- Test: `backend/tests/test_admin_routes.py`

**Step 1: Write the failing test**

Add to `TestAdminAccess` in `backend/tests/test_admin_routes.py`:

```python
def test_stream_logs_returns_sse_data(self, client, admin_user):
    """GET /admin/logs/{name} streams SSE-formatted log lines."""
    _, token = admin_user
    with patch("backend.routers.admin._docker_service") as mock_ds:
        mock_ds.available = True

        def fake_stream(name, tail=100):
            yield "2026-02-03 INFO Starting server"
            yield "2026-02-03 INFO Ready"

        mock_ds.stream_logs = fake_stream

        response = client.get(
            "/api/admin/logs/gantry-api",
            cookies={"session_token": token},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        body = response.text
        assert "data: " in body
        assert "Starting server" in body

def test_stream_logs_docker_unavailable(self, client, admin_user):
    """GET /admin/logs/{name} returns 503 when Docker is unavailable."""
    _, token = admin_user
    with patch("backend.routers.admin._docker_service") as mock_ds:
        mock_ds.available = False

        response = client.get(
            "/api/admin/logs/gantry-api",
            cookies={"session_token": token},
        )
        assert response.status_code == 503
```

**Step 2: Run test to verify it fails**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_admin_routes.py::TestAdminAccess::test_stream_logs_returns_sse_data -v`
Expected: FAIL — endpoint still returns placeholder

**Step 3: Replace the placeholder endpoint**

Replace the log streaming section in `backend/routers/admin.py`:

```python
@router.get("/logs/{service_name}")
async def stream_logs(
    service_name: str,
    admin=Depends(require_admin),
):
    """Stream service logs via SSE.

    Returns real-time log output from the named Docker container.
    Returns 503 if Docker is not available.
    """
    if not _docker_service.available:
        raise HTTPException(status_code=503, detail="Docker is not available")

    def generate() -> Generator[str, None, None]:
        for line in _docker_service.stream_logs(service_name):
            yield f"data: {line}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

Also add `Generator` to the typing import at the top of the file.

**Step 4: Run tests to verify they pass**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/test_admin_routes.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/routers/admin.py backend/tests/test_admin_routes.py
git commit -m "feat: implement SSE log streaming endpoint"
```

---

### Task 3: Add `streamLogs` to frontend API client

**Files:**

- Modify: `frontend/src/services/api.ts`

**Step 1: Add the streaming method**

Add to the `adminApi` object in `frontend/src/services/api.ts`:

```typescript
// Logs
streamLogs: (serviceName: string): EventSource => {
  return new EventSource(`${API_URL}/api/admin/logs/${serviceName}`, {
    withCredentials: true,
  });
},
```

Note: `EventSource` does not support custom headers but does support `withCredentials` for cookie-based auth, which is what Gantry uses.

**Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat: add streamLogs to admin API client"
```

---

### Task 4: Implement live LogsTab component

**Files:**

- Modify: `frontend/src/components/admin/LogsTab.tsx`

**Step 1: Implement the component**

Replace the placeholder `LogsTab` with a full implementation that:

- Connects to the SSE endpoint via `adminApi.streamLogs(selectedService)`
- Stores log lines in state (capped at 1000 lines to prevent memory issues)
- Auto-scrolls to bottom unless user has scrolled up (pause behavior)
- Provides Clear and Pause/Resume buttons
- Shows connection status indicator (connected/disconnected/error)
- Reconnects on service selection change
- Cleans up `EventSource` on unmount and service change
- Updates the service list to use actual Docker container names

**Step 2: Commit**

```bash
git add frontend/src/components/admin/LogsTab.tsx
git commit -m "feat: implement live log streaming in admin LogsTab"
```

---

### Task 5: Run full validation and final commit

**Step 1: Run all backend tests**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && python -m pytest backend/tests/ -v`
Expected: ALL PASS

**Step 2: Run pre-commit validation**

Run: `cd /home/jlwestsr/projects/west_ai_labs/nebulus-gantry && bin/gantry validate`
Expected: All hooks pass

**Step 3: Fix any linting issues found in Step 2, then re-run validation**

**Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "chore: fix linting issues from validation"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `backend/services/docker_service.py` | Add `stream_logs()` generator method |
| `backend/routers/admin.py` | Replace placeholder with real SSE endpoint |
| `backend/tests/test_docker_service.py` | Add `TestStreamLogs` test class |
| `backend/tests/test_admin_routes.py` | Add SSE data and Docker-unavailable tests |
| `frontend/src/services/api.ts` | Add `streamLogs` method to `adminApi` |
| `frontend/src/components/admin/LogsTab.tsx` | Full implementation with live streaming UI |
