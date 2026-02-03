from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.routers.auth import get_current_user
from backend.services.chat_service import ChatService
from backend.services.llm_service import LLMService
from backend.schemas.chat import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
    SendMessageRequest,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chat_service(db: DBSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


@router.post("/conversations", response_model=ConversationResponse)
def create_conversation(
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    return chat.create_conversation(user.id)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    return chat.get_conversations(user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: int,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    conversation = chat.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = chat.get_messages(conversation_id)
    return {"conversation": conversation, "messages": messages}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    if not chat.delete_conversation(conversation_id, user.id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    request: SendMessageRequest,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    # Verify conversation exists and belongs to user
    conversation = chat.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Save user message
    chat.add_message(conversation_id, "user", request.content)

    # Get conversation history for context
    messages = chat.get_messages(conversation_id)
    llm_messages = [
        {"role": "system", "content": "You are Nebulus, a helpful AI assistant."},
    ]
    for msg in messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # Stream response from LLM
    llm = LLMService()

    async def generate():
        full_response = ""
        async for chunk in llm.stream_chat(llm_messages):
            full_response += chunk
            yield chunk
        # Save assistant response after streaming completes
        chat.add_message(conversation_id, "assistant", full_response)

    return StreamingResponse(generate(), media_type="text/event-stream")
