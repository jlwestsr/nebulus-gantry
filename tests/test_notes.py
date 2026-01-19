def test_create_note(client):
    response = client.post("/api/notes", json={
        "title": "Test Note",
        "content": "This is a test note.",
        "category": "Testing"
    })

    # Debug if failed
    if response.status_code != 200:
        print(response.text)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Note"
    assert "id" in data
    return data["id"]


def test_get_notes(client):
    # Create one first
    test_create_note(client)

    response = client.get("/api/notes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["title"] == "Test Note"


def test_update_note(client):
    # We need an ID. Since tests run isolated by transaction rollback (if properly scoped),
    # but client fixture is module scope?
    # Actually my conftest db fixture is function scope, but client is module scope.
    # The client uses app, which uses get_db override.
    # The override creates a NEW session each time.
    # The session binds to... `engine` by default in my override logic `TestingSessionLocal()`.
    # Wait, `TestingSessionLocal` binds to `engine` (shared in-memory DB).
    # So if I want isolation, I should clean up tables or use transaction rollback.
    # The `override_get_db` in `conftest.py` just does `TestingSessionLocal()`.
    # It does NOT join the external transaction started in `db` fixture unless I structure it that way.
    # For now, In-memory DB persists across the module. Is acceptable for these simple tests.

    note_id = test_create_note(client)

    response = client.put(f"/api/notes/{note_id}", json={
        "title": "Updated Title",
        "content": "Updated content.",
        "category": "Updated Cat"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


def test_delete_note(client):
    note_id = test_create_note(client)

    response = client.delete(f"/api/notes/{note_id}")
    assert response.status_code == 200

    # Verify gone
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 404
