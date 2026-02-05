from datetime import datetime
from pydantic import BaseModel


class ConversationResponse(BaseModel):
    id: int
    title: str
    pinned: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str
    model: str | None = None


class SearchResult(BaseModel):
    conversation_id: int
    conversation_title: str
    message_snippet: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    results: list[SearchResult]
