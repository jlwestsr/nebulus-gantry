import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from backend.dependencies import get_db
from backend.routers.auth import get_current_user
from backend.services.chat_service import ChatService
from backend.services.llm_service import LLMService
from backend.services.model_service import ModelService
from backend.schemas.chat import (
    ConversationResponse,
    ConversationDetailResponse,
    SendMessageRequest,
    SearchResult,
    SearchResponse,
)
from backend.schemas.persona import SetConversationPersonaRequest

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


def _create_document_service(db: DBSession):
    """Factory for DocumentService."""
    from backend.services.document_service import DocumentService
    return DocumentService(db)


def _create_persona_service(db: DBSession):
    """Factory for PersonaService."""
    from backend.services.persona_service import PersonaService
    return PersonaService(db)


@router.get("/search", response_model=SearchResponse)
def search_conversations(
    q: str,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    """Search messages and conversation titles across the user's conversations."""
    if not q or not q.strip():
        return SearchResponse(results=[])

    from sqlalchemy import or_
    from backend.models.message import Message
    from backend.models.conversation import Conversation

    # Search messages belonging to user's conversations (message content OR title match)
    results = (
        chat.db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.user_id == user.id,
            or_(
                Message.content.ilike(f"%{q.strip()}%"),
                Conversation.title.ilike(f"%{q.strip()}%"),
            ),
        )
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )

    # Build response with snippets
    search_results = []
    for msg in results:
        conversation = msg.conversation

        # Create a snippet around the matched text
        content = msg.content
        lower_content = content.lower()
        lower_q = q.strip().lower()
        idx = lower_content.find(lower_q)
        if idx != -1:
            start = max(0, idx - 60)
            end = min(len(content), idx + len(q.strip()) + 60)
            snippet = content[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(content):
                snippet = snippet + "..."
        else:
            snippet = content[:150]
            if len(content) > 150:
                snippet += "..."

        search_results.append(
            SearchResult(
                conversation_id=conversation.id,
                conversation_title=conversation.title,
                message_snippet=snippet,
                role=msg.role,
                created_at=msg.created_at.isoformat(),
            )
        )

    return SearchResponse(results=search_results)


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


@router.patch("/conversations/{conversation_id}/pin", response_model=ConversationResponse)
def toggle_pin_conversation(
    conversation_id: int,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    """Toggle the pinned status of a conversation."""
    conversation = chat.toggle_pin(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/conversations/{conversation_id}/export")
def export_conversation(
    conversation_id: int,
    format: str = Query(default="json", pattern="^(json|pdf)$"),
    user=Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Export a conversation as JSON or PDF.

    Args:
        conversation_id: The conversation to export.
        format: Export format - "json" or "pdf" (default: json).

    Returns:
        JSON data or PDF file download.
    """
    from backend.services.export_service import ExportService

    export_service = ExportService(db)

    if format == "json":
        data = export_service.export_json(conversation_id, user.id)
        if not data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return JSONResponse(
            content=data,
            headers={
                "Content-Disposition": f"attachment; filename=conversation-{conversation_id}.json"
            },
        )
    else:
        pdf_bytes = export_service.export_pdf(conversation_id, user.id)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=conversation-{conversation_id}.pdf"
            },
        )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(  # noqa: C901
    conversation_id: int,
    request: SendMessageRequest,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
    db: DBSession = Depends(get_db),
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

    # --- RAG: Query document knowledge vault ---
    rag_context = ""
    if conversation.document_scope:
        try:
            document_service = _create_document_service(db)
            document_scope = json.loads(conversation.document_scope)
            rag_context = document_service.build_rag_context(
                user_id=user.id,
                query=request.content,
                document_scope=document_scope,
                top_k=3,
            )
        except Exception as e:
            logger.warning(f"RAG context build failed: {e}")

    # --- Persona: Load persona system prompt if assigned ---
    persona = None
    persona_temperature = None
    if conversation.persona_id:
        try:
            persona_service = _create_persona_service(db)
            persona = persona_service.get_persona(conversation.persona_id, user.id)
            if persona:
                persona_temperature = persona.temperature
        except Exception as e:
            logger.warning(f"Failed to load persona: {e}")

    # Query active model name for system prompt
    model_service = ModelService()
    active_model = await model_service.get_active_model()
    model_name = active_model["name"] if active_model else "an AI assistant"

    # Build system message
    if persona:
        # Use persona's system prompt
        system_content = persona.system_prompt
    else:
        # Default system prompt
        system_content = (
            f"You are Nebulus Gantry, powered by {model_name}. "
            "You are a helpful AI assistant."
        )

    # Append context from LTM and RAG
    if ltm_context:
        system_content = f"{system_content}\n\n{ltm_context}"
    if rag_context:
        system_content = f"{system_content}\n\n{rag_context}"

    # Get conversation history for context
    messages = chat.get_messages(conversation_id)
    llm_messages = [
        {"role": "system", "content": system_content},
    ]
    for msg in messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    # Stream response from LLM — use requested model or default
    llm = LLMService()
    llm_model = request.model or "default"

    async def generate():
        full_response = ""
        start_time = time.monotonic()
        async for chunk in llm.stream_chat(
            llm_messages, model=llm_model, temperature=persona_temperature
        ):
            full_response += chunk
            yield chunk

        generation_time_ms = int((time.monotonic() - start_time) * 1000)

        # Emit metadata as a special suffix for the frontend to parse
        meta: dict = {"generation_time_ms": generation_time_ms}
        if isinstance(llm.last_usage, dict):
            meta["prompt_tokens"] = llm.last_usage.get("prompt_tokens", 0)
            meta["completion_tokens"] = llm.last_usage.get("completion_tokens", 0)
            meta["total_tokens"] = llm.last_usage.get("total_tokens", 0)
        yield f"\n\n__META__{json.dumps(meta)}"

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


@router.patch("/conversations/{conversation_id}/persona", response_model=ConversationResponse)
def set_conversation_persona(
    conversation_id: int,
    request: SetConversationPersonaRequest,
    user=Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Set the persona for a conversation."""
    persona_service = _create_persona_service(db)
    conversation = persona_service.set_conversation_persona(
        conversation_id=conversation_id,
        persona_id=request.persona_id,
        user_id=user.id,
    )
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation or persona not found",
        )
    return conversation


class SetDocumentScopeRequest(BaseModel):
    """Request to set document scope for RAG."""
    document_scope: list[dict] | None = None  # [{"type": "document"|"collection", "id": int}]


@router.patch("/conversations/{conversation_id}/document-scope", response_model=ConversationResponse)
def set_conversation_document_scope(
    conversation_id: int,
    request: SetDocumentScopeRequest,
    user=Depends(get_current_user),
    chat: ChatService = Depends(get_chat_service),
):
    """Set the document scope for RAG in a conversation."""
    conversation = chat.get_conversation(conversation_id, user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Serialize document scope as JSON
    if request.document_scope:
        conversation.document_scope = json.dumps(request.document_scope)
    else:
        conversation.document_scope = None

    chat.db.commit()
    chat.db.refresh(conversation)
    return conversation
