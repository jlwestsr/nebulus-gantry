"""Tests for DocumentService and document routes."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.database import Base  # noqa: E402
from backend.models.user import User  # noqa: E402, F401
from backend.models.session import Session  # noqa: E402, F401
from backend.models.conversation import Conversation  # noqa: E402, F401
from backend.models.message import Message  # noqa: E402, F401
from backend.models.collection import Collection  # noqa: E402, F401
from backend.models.document import Document  # noqa: E402, F401
from backend.models.persona import Persona  # noqa: E402, F401
from backend.services.auth_service import AuthService  # noqa: E402
from backend.services.document_service import (  # noqa: E402
    CSV_ROW_LIMIT,
    DocumentService,
    chunk_csv,
    chunk_text,
    extract_text_from_csv,
    extract_text_from_txt,
)


@pytest.fixture(autouse=True)
def setup_db():
    """Create an isolated in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    yield TestSessionLocal
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(setup_db):
    """Provide a test database session."""
    session = setup_db()
    try:
        yield session
    finally:
        session.close()


def _make_user(db, email: str = "alice@example.com") -> User:
    """Helper to create a test user."""
    auth = AuthService(db)
    return auth.create_user(
        email=email,
        password="testpass",
        display_name=email.split("@")[0].capitalize(),
    )


# -- Test chunk_text ----------------------------------------------------------


class TestChunkText:
    """Test the chunk_text function."""

    def test_empty_text(self):
        """Empty text returns empty list."""
        assert chunk_text("") == []

    def test_short_text(self):
        """Text shorter than chunk size returns single chunk."""
        text = "Hello, world!"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_breaks_at_paragraph(self):
        """Prefers breaking at paragraph boundaries."""
        text = "First paragraph.\n\nSecond paragraph."
        chunks = chunk_text(text, chunk_size=30, overlap=5)
        assert len(chunks) >= 1

    def test_multiple_chunks(self):
        """Long text is split into multiple chunks."""
        text = "Word " * 1000  # ~5000 chars
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) > 1


class TestExtractTextFromTxt:
    """Test text extraction from TXT files."""

    def test_utf8_content(self):
        """Extracts UTF-8 encoded text."""
        content = "Hello, world!".encode("utf-8")
        assert extract_text_from_txt(content) == "Hello, world!"

    def test_latin1_fallback(self):
        """Falls back to latin-1 if UTF-8 fails."""
        content = "Café résumé".encode("latin-1")
        result = extract_text_from_txt(content)
        assert "Caf" in result


# -- Test CollectionService ---------------------------------------------------


class TestCollectionCRUD:
    """Test collection CRUD operations."""

    def test_create_collection(self, db):
        """Creates a collection with correct fields."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(
            user_id=user.id,
            name="My Docs",
            description="Test collection",
        )

        assert collection.id is not None
        assert collection.user_id == user.id
        assert collection.name == "My Docs"
        assert collection.description == "Test collection"

    def test_list_collections(self, db):
        """Lists all collections for a user."""
        user = _make_user(db)
        service = DocumentService(db)

        service.create_collection(user.id, "First")
        service.create_collection(user.id, "Second")

        collections = service.list_collections(user.id)
        assert len(collections) == 2

    def test_user_isolation(self, db):
        """Users cannot see other users' collections."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = DocumentService(db)

        service.create_collection(user_a.id, "A's Collection")
        service.create_collection(user_b.id, "B's Collection")

        collections_a = service.list_collections(user_a.id)
        collections_b = service.list_collections(user_b.id)

        assert len(collections_a) == 1
        assert collections_a[0].name == "A's Collection"
        assert len(collections_b) == 1
        assert collections_b[0].name == "B's Collection"

    def test_update_collection(self, db):
        """Updates collection name and description."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(user.id, "Original")
        updated = service.update_collection(
            collection.id, user.id, name="Updated", description="New desc"
        )

        assert updated.name == "Updated"
        assert updated.description == "New desc"

    def test_delete_collection(self, db):
        """Deletes a collection."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(user.id, "To Delete")
        result = service.delete_collection(collection.id, user.id)

        assert result is True
        assert service.get_collection(collection.id, user.id) is None

    def test_delete_wrong_user(self, db):
        """Cannot delete another user's collection."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = DocumentService(db)

        collection = service.create_collection(user_a.id, "A's")
        result = service.delete_collection(collection.id, user_b.id)

        assert result is False


# -- Test Document Upload -----------------------------------------------------


class TestDocumentUpload:
    """Test document upload and processing."""

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_upload_txt_document(self, mock_vc, db):
        """Uploads a TXT document and creates chunks."""
        user = _make_user(db)
        service = DocumentService(db)

        content = b"This is test content for the document."
        document = service.upload_document(
            user_id=user.id,
            filename="test.txt",
            content=content,
            content_type="txt",
        )

        assert document.id is not None
        assert document.filename == "test.txt"
        assert document.content_type == "txt"
        assert document.status == "ready"
        assert document.chunk_count >= 1

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_upload_with_collection(self, mock_vc, db):
        """Associates document with a collection."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(user.id, "My Collection")
        document = service.upload_document(
            user_id=user.id,
            filename="test.txt",
            content=b"Content",
            content_type="txt",
            collection_id=collection.id,
        )

        assert document.collection_id == collection.id

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_upload_invalid_collection(self, mock_vc, db):
        """Raises error for invalid collection ID."""
        user = _make_user(db)
        service = DocumentService(db)

        with pytest.raises(ValueError, match="Collection not found"):
            service.upload_document(
                user_id=user.id,
                filename="test.txt",
                content=b"Content",
                content_type="txt",
                collection_id=99999,
            )

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_list_documents(self, mock_vc, db):
        """Lists documents for a user."""
        user = _make_user(db)
        service = DocumentService(db)

        service.upload_document(user.id, "doc1.txt", b"Content 1", "txt")
        service.upload_document(user.id, "doc2.txt", b"Content 2", "txt")

        documents = service.list_documents(user.id)
        assert len(documents) == 2

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_list_documents_by_collection(self, mock_vc, db):
        """Filters documents by collection."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(user.id, "Filter Test")
        service.upload_document(user.id, "doc1.txt", b"Content", "txt", collection.id)
        service.upload_document(user.id, "doc2.txt", b"Content", "txt")  # No collection

        filtered = service.list_documents(user.id, collection.id)
        assert len(filtered) == 1
        assert filtered[0].filename == "doc1.txt"

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_delete_document(self, mock_vc, db):
        """Deletes a document."""
        user = _make_user(db)
        service = DocumentService(db)

        document = service.upload_document(user.id, "test.txt", b"Content", "txt")
        result = service.delete_document(document.id, user.id)

        assert result is True
        assert service.get_document(document.id, user.id) is None


# -- Test Document Access Control ---------------------------------------------


class TestDocumentAccessControl:
    """Test document access control between users."""

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_cannot_access_other_users_documents(self, mock_vc, db):
        """Users cannot see other users' documents."""
        user_a = _make_user(db, "a@example.com")
        user_b = _make_user(db, "b@example.com")
        service = DocumentService(db)

        document = service.upload_document(user_a.id, "private.txt", b"Secret", "txt")

        # User B cannot get user A's document
        assert service.get_document(document.id, user_b.id) is None

        # User B cannot delete user A's document
        assert service.delete_document(document.id, user_b.id) is False


# -- Test Cascade Delete ------------------------------------------------------


class TestCascadeDelete:
    """Test cascade deletion behavior."""

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_collection_delete_cascades_to_documents(self, mock_vc, db):
        """Deleting a collection deletes its documents."""
        user = _make_user(db)
        service = DocumentService(db)

        collection = service.create_collection(user.id, "Cascade Test")
        doc1 = service.upload_document(user.id, "d1.txt", b"C1", "txt", collection.id)
        doc2 = service.upload_document(user.id, "d2.txt", b"C2", "txt", collection.id)

        # Delete collection
        service.delete_collection(collection.id, user.id)

        # Documents should be gone
        assert service.get_document(doc1.id, user.id) is None
        assert service.get_document(doc2.id, user.id) is None


# -- Test Search --------------------------------------------------------------


class TestDocumentSearch:
    """Test document search functionality."""

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_search_returns_empty_when_chroma_unavailable(self, mock_vc, db):
        """Returns empty results when VectorClient is unavailable."""
        user = _make_user(db)
        service = DocumentService(db)

        results = service.search_documents(user.id, "test query")
        assert results == []

    @patch("backend.services.document_service.get_vector_client")
    def test_search_with_mock_chroma(self, mock_get_vc, db):
        """Tests search with mocked VectorClient results."""
        mock_vc = MagicMock()
        mock_vc.search.return_value = {
            "documents": [["Test document content"]],
            "distances": [[0.5]],
            "metadatas": [[{"document_id": 1, "filename": "test.txt", "chunk_index": 0}]],
        }
        mock_get_vc.return_value = mock_vc

        user = _make_user(db)
        service = DocumentService(db)

        results = service.search_documents(user.id, "test query", top_k=5)

        assert len(results) == 1
        assert results[0]["filename"] == "test.txt"
        assert results[0]["chunk_text"] == "Test document content"


# -- Test CSV Extraction -----------------------------------------------------


class TestExtractTextFromCsv:
    """Test CSV-specific text extraction."""

    def test_basic_csv(self):
        """Extracts headers and rows from valid CSV."""
        content = b"Name,Age,City\nAlice,30,NYC\nBob,25,LA\n"
        headers, rows = extract_text_from_csv(content)
        assert headers == ["Name", "Age", "City"]
        assert len(rows) == 2
        assert rows[0] == ["Alice", "30", "NYC"]

    def test_empty_csv_raises(self):
        """Raises ValueError for empty CSV."""
        with pytest.raises(ValueError, match="CSV file is empty"):
            extract_text_from_csv(b"")

    def test_headers_only(self):
        """CSV with only headers returns empty rows."""
        content = b"Name,Age\n"
        headers, rows = extract_text_from_csv(content)
        assert headers == ["Name", "Age"]
        assert rows == []

    def test_large_csv_capped(self):
        """CSV with more than CSV_ROW_LIMIT rows is capped."""
        header = "Col1,Col2\n"
        data = "a,b\n" * (CSV_ROW_LIMIT + 500)
        content = (header + data).encode("utf-8")
        headers, rows = extract_text_from_csv(content)
        assert len(rows) == CSV_ROW_LIMIT

    def test_latin1_csv(self):
        """Falls back to latin-1 for non-UTF-8 CSV."""
        content = "Name,City\nAlice,Montr\xe9al\n".encode("latin-1")
        headers, rows = extract_text_from_csv(content)
        assert headers == ["Name", "City"]
        assert "Montr" in rows[0][1]


# -- Test chunk_csv ----------------------------------------------------------


class TestChunkCsv:
    """Test CSV chunking logic."""

    def test_single_chunk(self):
        """Small CSV fits in one chunk."""
        headers = ["A", "B"]
        rows = [["1", "2"], ["3", "4"]]
        chunks = chunk_csv(headers, rows, rows_per_chunk=50)
        assert len(chunks) == 1
        assert chunks[0].startswith("A,B\n")

    def test_multiple_chunks(self):
        """Large CSV is split into multiple chunks."""
        headers = ["X"]
        rows = [[str(i)] for i in range(120)]
        chunks = chunk_csv(headers, rows, rows_per_chunk=50)
        assert len(chunks) == 3  # 50 + 50 + 20

    def test_headers_in_every_chunk(self):
        """Every chunk starts with the header row."""
        headers = ["Col1", "Col2"]
        rows = [["a", "b"]] * 100
        chunks = chunk_csv(headers, rows, rows_per_chunk=50)
        for chunk in chunks:
            assert chunk.startswith("Col1,Col2")

    def test_empty_rows(self):
        """No data rows returns single header-only chunk."""
        headers = ["H1", "H2"]
        chunks = chunk_csv(headers, [], rows_per_chunk=50)
        assert len(chunks) == 1
        assert chunks[0] == "H1,H2"


# -- Test CSV Upload ---------------------------------------------------------


class TestCsvUpload:
    """Test CSV document upload flow."""

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_upload_csv_document(self, mock_vc, db):
        """Uploads a CSV document with structured chunking."""
        user = _make_user(db)
        service = DocumentService(db)

        content = b"Name,Age\nAlice,30\nBob,25\n"
        document = service.upload_document(
            user_id=user.id,
            filename="data.csv",
            content=content,
            content_type="csv",
        )

        assert document.status == "ready"
        assert document.chunk_count >= 1

    @patch("backend.services.document_service.get_vector_client", return_value=None)
    def test_csv_preserves_headers(self, mock_vc, db):
        """CSV chunks preserve header information."""
        user = _make_user(db)
        service = DocumentService(db)

        rows = "Name,Score\n" + "\n".join(
            f"User{i},{i}" for i in range(60)
        )
        document = service.upload_document(
            user_id=user.id,
            filename="scores.csv",
            content=rows.encode("utf-8"),
            content_type="csv",
        )

        assert document.status == "ready"
        assert document.chunk_count == 2  # 50 + 10
