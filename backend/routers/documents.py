"""
Documents Router for Knowledge Vault.

Endpoints for managing collections and documents.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.routers.auth import get_current_user
from backend.services.document_service import DocumentService
from backend.schemas.document import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def get_document_service(db: DBSession = Depends(get_db)) -> DocumentService:
    return DocumentService(db)


# ========== Collections ==========


@router.post("/collections", response_model=CollectionResponse)
def create_collection(
    data: CollectionCreate,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Create a new collection."""
    collection = service.create_collection(
        user_id=user.id,
        name=data.name,
        description=data.description,
    )
    return _collection_to_response(collection)


@router.get("/collections", response_model=list[CollectionResponse])
def list_collections(
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """List all collections for the current user."""
    collections = service.list_collections(user.id)
    return [_collection_to_response(c) for c in collections]


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
def get_collection(
    collection_id: int,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Get a single collection."""
    collection = service.get_collection(collection_id, user.id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _collection_to_response(collection)


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Update a collection."""
    collection = service.update_collection(
        collection_id=collection_id,
        user_id=user.id,
        name=data.name,
        description=data.description,
    )
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return _collection_to_response(collection)


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: int,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Delete a collection and all its documents."""
    if not service.delete_collection(collection_id, user.id):
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": "Collection deleted"}


# ========== Documents ==========


ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: int | None = Form(None),
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Upload a document to the knowledge vault."""
    # Validate content type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Try to infer from filename
        filename = file.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext == "pdf":
            doc_type = "pdf"
        elif ext in ("txt", "text"):
            doc_type = "txt"
        elif ext == "csv":
            doc_type = "csv"
        elif ext == "docx":
            doc_type = "docx"
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PDF, TXT, CSV, DOCX",
            )
    else:
        doc_type = ALLOWED_CONTENT_TYPES[content_type]

    # Read file content
    content = await file.read()

    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB.",
        )

    try:
        document = service.upload_document(
            user_id=user.id,
            filename=file.filename or "unnamed",
            content=content,
            content_type=doc_type,
            collection_id=collection_id,
        )
        return document
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    collection_id: int | None = None,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """List documents, optionally filtered by collection."""
    return service.list_documents(user.id, collection_id)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Get a single document."""
    document = service.get_document(document_id, user.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Delete a document."""
    if not service.delete_document(document_id, user.id):
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}


@router.post("/search", response_model=DocumentSearchResponse)
def search_documents(
    data: DocumentSearchRequest,
    user=Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
):
    """Search documents using semantic search."""
    results = service.search_documents(
        user_id=user.id,
        query=data.query,
        collection_ids=data.collection_ids,
        top_k=data.top_k,
    )
    return DocumentSearchResponse(
        results=[
            DocumentSearchResult(
                document_id=r["document_id"],
                filename=r["filename"],
                chunk_text=r["chunk_text"],
                similarity=r["similarity"],
            )
            for r in results
        ]
    )


def _collection_to_response(collection) -> CollectionResponse:
    """Convert a Collection model to response with document count."""
    return CollectionResponse(
        id=collection.id,
        name=collection.name,
        description=collection.description,
        is_default=collection.is_default,
        document_count=len(collection.documents) if collection.documents else 0,
        created_at=collection.created_at,
    )
