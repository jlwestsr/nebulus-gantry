from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


# --- Shared Base ---
class BaseDTO(BaseModel):
    class Config:
        from_attributes = True


# --- User DTOs ---
class UserBase(BaseDTO):
    email: str
    username: str
    full_name: Optional[str] = None
    role: str = "user"
    current_model: str = "Llama 3.1"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    current_model: Optional[str] = None


class UserDTO(UserBase):
    id: int
    created_at: datetime


# --- Note DTOs ---
class NoteBase(BaseDTO):
    title: str = "Untitled"
    content: str = ""
    category: Optional[str] = "Uncategorized"


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None


class NoteDTO(NoteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


# --- Folder DTOs ---
class FolderBase(BaseDTO):
    name: str


class FolderDTO(FolderBase):
    id: int
    user_id: int
    created_at: datetime


# --- Message DTOs ---
class FeedbackDTO(BaseDTO):
    id: int
    score: int
    comment: Optional[str] = None
    created_at: datetime


class MessageBase(BaseDTO):
    content: str
    author: str  # "user" or "assistant"
    entities: Optional[List[Dict[str, Any]]] = None


class MessageCreate(MessageBase):
    chat_id: str
    cl_id: Optional[str] = None


class MessageDTO(MessageBase):
    id: int
    cl_id: Optional[str] = None
    chat_id: str
    created_at: datetime
    feedback: Optional[FeedbackDTO] = None


# --- Chat DTOs ---
class ChatBase(BaseDTO):
    title: Optional[str] = None
    folder_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ChatCreate(ChatBase):
    id: str  # Chainlit Session ID


class ChatDTO(ChatBase):
    id: str
    user_id: int
    created_at: datetime
    messages: List[MessageDTO] = []


# --- Usage Log DTOs ---
class UsageLogDTO(BaseDTO):
    id: int
    user_id: int
    chat_id: Optional[str] = None
    message_id: Optional[int] = None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: int
    created_at: datetime
