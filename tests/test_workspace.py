from unittest.mock import patch, AsyncMock


def test_list_models_mocked(client):
    # Mock the Ollama list call to avoid dependency on running Ollama during test
    # Need to patch where main.py imports it or uses it.
    # main.py: `from main import client` -> client is AsyncOpenAI
    # But `client` is global in `main`.
    # We can patch `main.client.models.list`.

    with patch("nebulus_gantry.main.client.models.list", new_callable=AsyncMock) as mock_list:
        # Mock return structure
        mock_list.return_value.data = [
            type('obj', (object,), {'id': 'llama3:latest'}),
            type('obj', (object,), {'id': 'gpt-4'})
        ]

        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data


def test_tools_list(client):
    response = client.get("/api/workspace/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert isinstance(data["tools"], list)


def test_knowledge_list(client):
    response = client.get("/api/workspace/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert "collections" in data
    assert isinstance(data["collections"], list)
