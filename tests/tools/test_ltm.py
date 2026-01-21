import pytest
from unittest.mock import MagicMock, patch
from nebulus_gantry.tools.ltm import LTMTool


@pytest.fixture
def mock_chroma():
    with patch("nebulus_gantry.tools.ltm.chromadb") as mock_chroma:
        yield mock_chroma


def test_ltm_initialization(mock_chroma):
    tool = LTMTool()
    mock_chroma.HttpClient.assert_called_once()
    assert tool.collection is not None


def test_search_chat_history_success(mock_chroma):
    tool = LTMTool()

    # Mock query result
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["Message 1", "Message 2"]],
        "metadatas": [[
            {"sender": "user", "timestamp": 123},
            {"sender": "assistant", "timestamp": 124}
        ]]
    }
    tool.collection = mock_collection

    result = tool.search_chat_history("test query")

    assert "Message 1" in result
    assert "Message 2" in result
    assert "[123] user:" in result
    assert "[124] assistant:" in result


def test_search_chat_history_no_results(mock_chroma):
    tool = LTMTool()
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [],
        "metadatas": []
    }
    tool.collection = mock_collection

    result = tool.search_chat_history("test query")
    assert result == "No relevant history found."


def test_search_chat_history_error(mock_chroma):
    tool = LTMTool()
    tool.collection = None  # Simulate connection failure
    result = tool.search_chat_history("test")
    assert "Error: LTM Database not connected" in result
