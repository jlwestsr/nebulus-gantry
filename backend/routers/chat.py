import logging

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def get_chat_service(db: DBSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


def build_ltm_context(similar_messages: list, related_facts: list) -> str:
    """Build a context string from long-term memory results.

    Args:
        similar_messages: List of dicts from MemoryService.search_similar,
            each containing 'content', 'score', and 'metadata'.
        related_facts: List of dicts from GraphService.get_related,
            each containing 'entity', 'relationship', and 'connected_entity'.

    Returns:
        A formatted string to inject into the system prompt, or empty string
        if no relevant context is available.
    """
    parts = []
    if similar_messages:
        parts.append("Relevant past context:")
        for msg in similar_messages[:3]:
            parts.append(f"- {msg['content'][:200]}")

    if related_facts:
        parts.append("\nKnown facts:")
        for fact in related_facts[:5]:
            parts.append(
                f"- {fact['entity']} {fact['relationship']} {fact['connected_entity']}"
            )

    return "\n".join(parts) if parts else ""


def _create_memory_service(user_id: int):
    """Factory for MemoryService. Lazy import to handle missing chromadb gracefully."""
    from backend.services.memory_service import MemoryService
    return MemoryService(user_id)


def _create_graph_service(user_id: int):
    """Factory for GraphService. Lazy import to handle missing networkx gracefully."""
    from backend.services.graph_service import GraphService
    return GraphService(user_id)


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
    user_msg = chat.add_message(conversation_id, "user", request.content)

    # --- LTM: Query long-term memory for context ---
    memory_service = None
    graph_service = None
    similar_messages = []
    related_facts = []

    try:
        memory_service = _create_memory_service(user.id)
        similar_messages = await memory_service.search_similar(
            request.content, limit=3
        )
    except Exception as e:
        logger.warning(f"MemoryService query failed: {e}")
        similar_messages = []

    try:
        graph_service = _create_graph_service(user.id)
        entities = graph_service.extract_entities(request.content)
        related_facts = []
        for entity_info in entities:
            facts = graph_service.get_related(entity_info["value"])
            related_facts.extend(facts)
    except Exception as e:
        logger.warning(f"GraphService query failed: {e}")
        related_facts = []

    ltm_context = build_ltm_context(similar_messages, related_facts)

    # Build system message with LTM context
    system_content = "You are Nebulus, a helpful AI assistant."
    if ltm_context:
        system_content = f"{system_content}\n\n{ltm_context}"

    # Get conversation history for context
    messages = chat.get_messages(conversation_id)
    llm_messages = [
        {"role": "system", "content": system_content},
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
        assistant_msg = chat.add_message(conversation_id, "assistant", full_response)

        # --- LTM: Update long-term memory asynchronously ---
        # Embed user message into ChromaDB
        if memory_service is not None:
            try:
                await memory_service.embed_message(
                    message_id=user_msg.id,
                    content=request.content,
                    metadata={
                        "conversation_id": str(conversation_id),
                        "role": "user",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to embed user message: {e}")

            # Embed assistant message into ChromaDB
            try:
                await memory_service.embed_message(
                    message_id=assistant_msg.id,
                    content=full_response,
                    metadata={
                        "conversation_id": str(conversation_id),
                        "role": "assistant",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to embed assistant message: {e}")

        # Extract entities and update knowledge graph
        if graph_service is not None:
            try:
                for entity in graph_service.extract_entities(full_response):
                    graph_service.add_fact(
                        entity1=entity["value"],
                        relationship="mentioned_in",
                        entity2=f"conversation_{conversation_id}",
                    )
                graph_service.save()
            except Exception as e:
                logger.warning(f"Failed to update knowledge graph: {e}")

    return StreamingResponse(generate(), media_type="text/event-stream")
