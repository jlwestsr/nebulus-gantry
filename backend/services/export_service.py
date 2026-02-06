"""Service for exporting conversations in various formats."""
import io
import json
import zipfile
from datetime import datetime, timezone
from typing import BinaryIO

from sqlalchemy.orm import Session as DBSession

from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.user import User


class ExportService:
    """Service for exporting conversations to JSON and PDF formats."""

    def __init__(self, db: DBSession):
        self.db = db

    def _get_conversation_with_messages(
        self, conversation_id: int, user_id: int
    ) -> tuple[Conversation, list[Message]] | None:
        """Get conversation and its messages if owned by user."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )
        if not conversation:
            return None

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        return conversation, messages

    def _get_user_name(self, user_id: int) -> str:
        """Get user's display name."""
        user = self.db.query(User).filter(User.id == user_id).first()
        return user.display_name if user else "Unknown"

    def export_json(self, conversation_id: int, user_id: int) -> dict | None:
        """Export a conversation as a JSON dict.

        Returns:
            Dict with conversation data and messages, or None if not found.
        """
        result = self._get_conversation_with_messages(conversation_id, user_id)
        if not result:
            return None

        conversation, messages = result

        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "pinned": conversation.pinned,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
            },
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_pdf(self, conversation_id: int, user_id: int) -> bytes | None:
        """Export a conversation as a PDF document.

        Returns:
            PDF bytes, or None if conversation not found.
        """
        result = self._get_conversation_with_messages(conversation_id, user_id)
        if not result:
            return None

        conversation, messages = result
        user_name = self._get_user_name(user_id)

        # Lazy import to avoid loading fpdf2 if not needed
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Header
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, conversation.title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(128, 128, 128)
        date_range = ""
        if messages:
            first_date = messages[0].created_at.strftime("%Y-%m-%d %H:%M")
            last_date = messages[-1].created_at.strftime("%Y-%m-%d %H:%M")
            date_range = f"{first_date} - {last_date}"
        pdf.cell(0, 6, f"User: {user_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        if date_range:
            pdf.cell(0, 6, date_range, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(5)

        # Reset text color
        pdf.set_text_color(0, 0, 0)

        # Messages
        for msg in messages:
            # Role header
            if msg.role == "user":
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(34, 139, 34)  # Green
                label = "You:"
            else:
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(65, 105, 225)  # Royal Blue
                label = "Assistant:"

            timestamp = msg.created_at.strftime("%H:%M")
            pdf.cell(0, 8, f"{label} ({timestamp})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            # Message content
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            # Use multi_cell for word-wrapped content
            pdf.multi_cell(0, 5, msg.content)
            pdf.ln(3)

        # Footer
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(128, 128, 128)
        export_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        pdf.cell(0, 5, f"Exported from Nebulus Gantry on {export_time}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        return bytes(pdf.output())

    def bulk_export(
        self,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> BinaryIO:
        """Export multiple conversations as a ZIP file of JSON exports.

        Args:
            user_id: Filter by specific user (None = all users)
            date_from: Filter conversations created after this date
            date_to: Filter conversations created before this date

        Returns:
            BytesIO buffer containing the ZIP file.
        """
        query = self.db.query(Conversation)

        if user_id is not None:
            query = query.filter(Conversation.user_id == user_id)
        if date_from is not None:
            query = query.filter(Conversation.created_at >= date_from)
        if date_to is not None:
            query = query.filter(Conversation.created_at <= date_to)

        conversations = query.order_by(Conversation.created_at.desc()).all()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for conv in conversations:
                messages = (
                    self.db.query(Message)
                    .filter(Message.conversation_id == conv.id)
                    .order_by(Message.created_at.asc())
                    .all()
                )

                export_data = {
                    "conversation": {
                        "id": conv.id,
                        "title": conv.title,
                        "user_id": conv.user_id,
                        "pinned": conv.pinned,
                        "created_at": conv.created_at.isoformat(),
                        "updated_at": conv.updated_at.isoformat(),
                    },
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                        }
                        for msg in messages
                    ],
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                }

                # Filename: conversation-{id}-{sanitized_title}.json
                safe_title = "".join(
                    c if c.isalnum() or c in (" ", "-", "_") else "_"
                    for c in conv.title[:30]
                ).strip()
                filename = f"conversation-{conv.id}-{safe_title}.json"
                zf.writestr(filename, json.dumps(export_data, indent=2))

        zip_buffer.seek(0)
        return zip_buffer
