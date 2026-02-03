from sqlalchemy.orm import Session as DBSession

from backend.models.conversation import Conversation
from backend.models.message import Message


class ChatService:
    def __init__(self, db: DBSession):
        self.db = db

    def create_conversation(self, user_id: int, title: str = "New Conversation") -> Conversation:
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def get_conversations(self, user_id: int) -> list[Conversation]:
        return (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    def get_conversation(self, conversation_id: int, user_id: int) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        self.db.delete(conversation)
        self.db.commit()
        return True

    def add_message(self, conversation_id: int, role: str, content: str) -> Message:
        message = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(message)

        # Update conversation's updated_at
        conversation = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation:
            from datetime import datetime
            conversation.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_messages(self, conversation_id: int) -> list[Message]:
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
