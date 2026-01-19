def test_read_root(client):
    response = client.get("/")
    # Should bypass auth and return 200 OK (Chainlit Index)
    # Actually, root "/" is mounted chainlit.
    assert response.status_code == 200
    # Content might be chainlit HTML, let's just check status.


def test_read_notes_page(client):
    response = client.get("/notes")
    assert response.status_code == 200
    assert "Nebulus - Notes" in response.text


def test_read_workspace_page(client):
    response = client.get("/workspace")
    assert response.status_code == 200
    assert "Nebulus - Workspace" in response.text

