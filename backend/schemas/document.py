from datetime import datetime
from pydantic import BaseModel


class CollectionCreate(BaseModel):
    name: str
    description: str | None = None


class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    is_default: bool
    document_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None = None
    collection_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentSearchResult(BaseModel):
    document_id: int
    filename: str
    chunk_text: str
    similarity: float


class DocumentSearchRequest(BaseModel):
    query: str
    collection_ids: list[int] | None = None
    top_k: int = 5


class DocumentSearchResponse(BaseModel):
    results: list[DocumentSearchResult]
