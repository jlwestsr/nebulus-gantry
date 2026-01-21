from fastapi import APIRouter, Depends, HTTPException, Body
from ..database import Chat, Message, User, get_db
from sqlalchemy.orm import Session
import uuid

router = APIRouter(prefix="/api/conversations", tags=["ltm"])


@router.post("")
async def create_conversation(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation.
    Expected Payload: {"topic": "string", "user_id": int, "metadata": dict}
    """
    topic = data.get("topic")
    user_id = data.get("user_id")
    metadata = data.get("metadata")

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create Chat compatible with Gantry (String ID (UUID) is standard here)
    chat_id = str(uuid.uuid4())
    new_chat = Chat(
        id=chat_id,
        user_id=user_id,
        title=topic or "New Chat",
        metadata_json=metadata
    )

    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)

    return {
        "id": new_chat.id,
        "topic": new_chat.title,
        "user_id": new_chat.user_id,
        "metadata": new_chat.metadata_json
    }


@router.get("/{conv_id}")
async def get_conversation(
    conv_id: str,
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == conv_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.query(Message).filter(Message.chat_id ==
                                        conv_id).order_by(Message.created_at).all()

    msg_list = []
    for m in messages:
        msg_list.append({
            "role": m.author,
            "content": m.content,
            "entities": m.entities,
            "created_at": m.created_at.isoformat()
        })

    return {
        "id": chat.id,
        "topic": chat.title,
        "user_id": chat.user_id,
        "metadata": chat.metadata_json,
        "created_at": chat.created_at.isoformat(),
        "messages": msg_list
    }


@router.put("/{conv_id}")
async def update_conversation(
    conv_id: str,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == conv_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found")

    topic = data.get("topic")
    metadata = data.get("metadata")

    if topic:
        chat.title = topic

    if metadata is not None:
        chat.metadata_json = metadata

    db.commit()
    return {
        "status": "success",
        "id": chat.id,
        "topic": chat.title,
        "metadata": chat.metadata_json
    }


@router.delete("/{conv_id}")
async def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db)
):
    chat = db.query(Chat).filter(Chat.id == conv_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Cascade delete is handled by relationship, but explicit is safe
    db.delete(chat)
    db.commit()
    return {"status": "success"}
