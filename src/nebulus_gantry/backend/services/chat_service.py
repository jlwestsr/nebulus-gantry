from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.entities import Chat, Message, Feedback
from ..models.dtos import MessageCreate


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_chat(self, chat_id: str, user_id: int) -> Chat:
        chat = self.db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            chat = Chat(id=chat_id, user_id=user_id, title="New Chat")
            self.db.add(chat)
            self.db.commit()
            self.db.refresh(chat)
        return chat

    def save_message(self, message_data: MessageCreate, user_id: Optional[int] = None) -> Message:
        # Check for existing message (Edit case)
        if message_data.cl_id:
            existing_msg = self.db.query(Message).filter(Message.cl_id == message_data.cl_id).first()
            if existing_msg:
                if existing_msg.content != message_data.content:
                    existing_msg.content = message_data.content
                    if message_data.entities:
                        existing_msg.entities = message_data.entities
                    # Truncate future history on edit
                    self._truncate_history_after(existing_msg)
                    self.db.commit()
                return existing_msg

        # Ensure Chat Exists
        chat = self.db.query(Chat).filter(Chat.id == message_data.chat_id).first()
        if not chat and user_id:
            chat = self.get_or_create_chat(message_data.chat_id, user_id)

        if not chat:
            # Fallback if no user_id provided (shouldn't happen in auth'd context)
            raise ValueError(f"Chat {message_data.chat_id} not found and no user_id provided.")

        new_msg = Message(
            chat_id=message_data.chat_id,
            author=message_data.author,
            content=message_data.content,
            cl_id=message_data.cl_id,
            entities=message_data.entities
        )
        self.db.add(new_msg)

        # Update title if first user message
        if message_data.author == "user" and chat.title == "New Chat":
            title = message_data.content[:30] + ".." if len(message_data.content) > 30 else message_data.content
            chat.title = title
            self.db.add(chat)

        self.db.commit()
        return new_msg

    def get_chats_for_user(self, user_id: int) -> List[Chat]:
        return (
            self.db.query(Chat)
            .filter(Chat.user_id == user_id)
            .order_by(desc(Chat.created_at))
            .all()
        )

    def get_chat_history(self, chat_id: str, limit: int = 20) -> List[Message]:
        self.db.expire_on_commit = False  # Optimization
        messages = (
            self.db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )
        return sorted(messages, key=lambda m: m.created_at)

    def delete_chat(self, chat_id: str, user_id: int) -> bool:
        chat = self.db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
        if not chat:
            return False
        self.db.delete(chat)
        self.db.commit()
        return True

    def delete_all_chats(self, user_id: int):
        self.db.query(Chat).filter(Chat.user_id == user_id).delete()
        self.db.commit()

    def save_feedback(self, message_id: str, score: int, comment: Optional[str] = None):
        msg = self.db.query(Message).filter(Message.cl_id == message_id).first()
        if not msg:
            return None

        existing = self.db.query(Feedback).filter(Feedback.message_id == msg.id).first()
        if existing:
            existing.score = score
            existing.comment = comment
        else:
            fb = Feedback(message_id=msg.id, score=score, comment=comment)
            self.db.add(fb)
        self.db.commit()

    def _truncate_history_after(self, target_message: Message):
        """Helper to delete messages strictly after the target (for edits)."""
        self.db.query(Message).filter(
            Message.chat_id == target_message.chat_id,
            Message.created_at > target_message.created_at
        ).delete()
