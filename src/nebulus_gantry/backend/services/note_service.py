from sqlalchemy.orm import Session
from nebulus_gantry.backend.models.entities import Note
from nebulus_gantry.backend.models.dtos import NoteCreate, NoteUpdate
from typing import List, Optional


class NoteService:
    def __init__(self, db: Session):
        self.db = db

    def create_note(self, user_id: int, note_in: NoteCreate) -> Note:
        note = Note(
            user_id=user_id,
            title=note_in.title,
            content=note_in.content,
            category=note_in.category
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_notes(self, user_id: int, skip: int = 0, limit: int = 100) -> List[Note]:
        return (
            self.db.query(Note)
            .filter(Note.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_note(self, user_id: int, note_id: int) -> Optional[Note]:
        return (
            self.db.query(Note)
            .filter(Note.user_id == user_id, Note.id == note_id)
            .first()
        )

    def update_note(self, user_id: int, note_id: int, note_in: NoteUpdate) -> Optional[Note]:
        note = self.get_note(user_id, note_id)
        if not note:
            return None

        update_data = note_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(note, field, value)

        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_note(self, user_id: int, note_id: int) -> bool:
        note = self.get_note(user_id, note_id)
        if not note:
            return False

        self.db.delete(note)
        self.db.commit()
        return True
