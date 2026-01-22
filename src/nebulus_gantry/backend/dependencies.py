from fastapi import Depends
from sqlalchemy.orm import Session
from .database import get_db
from .services.chat_service import ChatService
from .services.user_service import UserService


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)
