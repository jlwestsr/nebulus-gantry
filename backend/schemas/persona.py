from datetime import datetime
from pydantic import BaseModel, Field


class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    system_prompt: str = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    model_id: str | None = None


class PersonaUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    system_prompt: str | None = Field(None, min_length=1)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    model_id: str | None = None


class PersonaResponse(BaseModel):
    id: int
    user_id: int | None
    name: str
    description: str | None
    system_prompt: str
    temperature: float
    model_id: str | None
    is_default: bool
    is_system: bool = False  # Computed: user_id is None
    created_at: datetime

    model_config = {"from_attributes": True}

    def __init__(self, **data):
        # Compute is_system based on user_id
        if "user_id" in data:
            data["is_system"] = data["user_id"] is None
        super().__init__(**data)


class SetConversationPersonaRequest(BaseModel):
    persona_id: int | None = None
