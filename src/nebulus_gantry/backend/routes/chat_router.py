from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..dependencies import get_chat_service
from ..services.chat_service import ChatService
#  Legacy Auth import
from ...routers.auth_routes import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/history", response_model=List[dict])
async def get_chat_history(
    user=Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    chats = chat_service.get_chats_for_user(user.id)
    # Manual serialization matching legacy format for now
    result = []
    for chat in chats:
        result.append(
            {
                "id": chat.id,
                "title": chat.title or "New Chat",
                "folder_id": chat.folder_id,
                "created_at": chat.created_at.isoformat(),
            }
        )
    return result


@router.delete("/chats/{chat_id}")
async def delete_chat(
    chat_id: str,
    user=Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    success = chat_service.delete_chat(chat_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}


@router.delete("/chats")
async def delete_all_chats(
    user=Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        chat_service.delete_all_chats(user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success"}
