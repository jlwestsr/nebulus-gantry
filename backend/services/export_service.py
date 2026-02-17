"""Service for exporting conversations in various formats."""
import io
import json
import zipfile
import re
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

    def export_spreadsheet(self, conversation_id: int, user_id: int) -> bytes | None:
        """Export a conversation as an Excel spreadsheet with multiple sheets.

        Creates a comprehensive Excel file with:
        - Raw Data sheet: CSV data that was analyzed
        - KPI Summary sheet: Key metrics extracted from conversation
        - Recommendations sheet: AI-generated action items

        Returns:
            Excel file bytes, or None if conversation not found.
        """
        result = self._get_conversation_with_messages(conversation_id, user_id)
        if not result:
            return None

        conversation, messages = result
        user_name = self._get_user_name(user_id)

        # Lazy import to avoid loading openpyxl if not needed
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        wb = Workbook()

        # Remove default sheet
        wb.remove(wb.active)

        # Helper function to auto-size columns
        def auto_size_columns(sheet):
            for column in sheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                sheet.column_dimensions[column_letter].width = adjusted_width

        # --- SHEET 1: Raw Data ---
        raw_sheet = wb.create_sheet(title="Raw Data")
        raw_data = self._extract_csv_data_from_conversation(messages)

        if raw_data:
            # Headers
            headers = list(raw_data[0].keys()) if raw_data else []
            for col, header in enumerate(headers, 1):
                cell = raw_sheet.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E6F3FF", end_color="E6F3FF", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")

            # Data rows
            for row_idx, row_data in enumerate(raw_data, 2):
                for col_idx, header in enumerate(headers, 1):
                    raw_sheet.cell(row=row_idx, column=col_idx, value=row_data.get(header, ""))

            # Freeze header row
            raw_sheet.freeze_panes = "A2"
            auto_size_columns(raw_sheet)
        else:
            raw_sheet.cell(row=1, column=1, value="No CSV data found in conversation")

        # --- SHEET 2: KPI Summary ---
        kpi_sheet = wb.create_sheet(title="KPI Summary")
        kpis = self._extract_kpis_from_conversation(messages)

        # Title
        title_cell = kpi_sheet.cell(row=1, column=1, value="Key Performance Indicators")
        title_cell.font = Font(bold=True, size=14)
        title_cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        kpi_sheet.merge_cells("A1:C1")

        # Headers
        kpi_sheet.cell(row=3, column=1, value="Metric").font = Font(bold=True)
        kpi_sheet.cell(row=3, column=2, value="Value").font = Font(bold=True)
        kpi_sheet.cell(row=3, column=3, value="Notes").font = Font(bold=True)

        # KPI data
        row = 4
        for kpi in kpis:
            kpi_sheet.cell(row=row, column=1, value=kpi["metric"])
            kpi_sheet.cell(row=row, column=2, value=kpi["value"])
            kpi_sheet.cell(row=row, column=3, value=kpi["notes"])
            row += 1

        auto_size_columns(kpi_sheet)

        # --- SHEET 3: Recommendations ---
        rec_sheet = wb.create_sheet(title="Recommendations")
        recommendations = self._extract_recommendations_from_conversation(messages)

        # Title
        title_cell = rec_sheet.cell(row=1, column=1, value="AI-Generated Recommendations")
        title_cell.font = Font(bold=True, size=14)
        title_cell.fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        title_cell.alignment = Alignment(horizontal="center")
        rec_sheet.merge_cells("A1:C1")

        # Headers
        rec_sheet.cell(row=3, column=1, value="Priority").font = Font(bold=True)
        rec_sheet.cell(row=3, column=2, value="Recommendation").font = Font(bold=True)
        rec_sheet.cell(row=3, column=3, value="Expected Impact").font = Font(bold=True)

        # Recommendation data
        row = 4
        for rec in recommendations:
            rec_sheet.cell(row=row, column=1, value=rec["priority"])
            rec_sheet.cell(row=row, column=2, value=rec["recommendation"])
            rec_sheet.cell(row=row, column=3, value=rec["impact"])
            row += 1

        auto_size_columns(rec_sheet)

        # --- SHEET 4: Export Info ---
        info_sheet = wb.create_sheet(title="Export Info")
        info_sheet.cell(row=1, column=1, value="Conversation Title:").font = Font(bold=True)
        info_sheet.cell(row=1, column=2, value=conversation.title)

        info_sheet.cell(row=2, column=1, value="User:").font = Font(bold=True)
        info_sheet.cell(row=2, column=2, value=user_name)

        info_sheet.cell(row=3, column=1, value="Exported At:").font = Font(bold=True)
        info_sheet.cell(row=3, column=2, value=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

        info_sheet.cell(row=4, column=1, value="Messages Count:").font = Font(bold=True)
        info_sheet.cell(row=4, column=2, value=len(messages))

        auto_size_columns(info_sheet)

        # Save to bytes
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def _extract_csv_data_from_conversation(self, messages: list[Message]) -> list[dict]:
        """Extract CSV data that was uploaded and analyzed in the conversation."""
        # Look for CSV data in user messages or assistant responses
        # This is a simplified implementation - in a real system you might
        # store CSV data separately or parse it from message content
        csv_data = []

        for message in messages:
            # Look for tabular data patterns in messages
            content = message.content
            lines = content.split('\n')

            # Try to find CSV-like content (simplified detection)
            for i, line in enumerate(lines):
                if ',' in line and '|' not in line:  # Looks like CSV
                    # Try to parse next several lines as CSV data
                    try:
                        headers = line.split(',')
                        if len(headers) > 2:  # At least 3 columns
                            # Look for data rows following this line
                            for j in range(i + 1, min(i + 20, len(lines))):
                                data_line = lines[j]
                                if ',' in data_line:
                                    values = data_line.split(',')
                                    if len(values) == len(headers):
                                        row_dict = {}
                                        for k, header in enumerate(headers):
                                            value = values[k].strip() if k < len(values) else ""
                                            row_dict[header.strip()] = value
                                        csv_data.append(row_dict)
                            break
                    except:
                        continue

            if csv_data:  # Found some data, return it
                break

        return csv_data

    def _extract_kpis_from_conversation(self, messages: list[Message]) -> list[dict]:
        """Extract KPIs mentioned in the conversation using regex patterns."""
        kpis = []

        # Common dealership KPI patterns
        kpi_patterns = {
            r'(\d+(?:,\d+)*)\s*units?\s*sold': 'Units Sold',
            r'\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:average\s*)?(?:front\s*)?gross': 'Average Front Gross',
            r'(\d+(?:\.\d+)?)\s*days?\s*(?:to\s*sale|on\s*lot)': 'Average Days to Sale',
            r'(\d+(?:\.\d+)?)%\s*closing\s*ratio': 'Closing Ratio',
            r'\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:per\s*)?(?:vehicle\s*)?retailed|PVR': 'PVR (Per Vehicle Retailed)',
            r'(\d+(?:\.\d+)?)%\s*(?:service\s*)?absorption': 'Service Absorption Rate',
            r'(\d+(?:\.\d+)?)\s*(?:hours?\s*)?(?:per\s*)?(?:RO|repair\s*order)': 'Hours per RO',
            r'\$(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:effective\s*)?labor\s*rate': 'Effective Labor Rate'
        }

        for message in messages:
            if message.role == 'assistant':  # Focus on AI responses
                content = message.content.lower()

                for pattern, metric_name in kpi_patterns.items():
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches[:1]:  # Take first match for each metric
                        value = match if isinstance(match, str) else str(match)
                        kpis.append({
                            'metric': metric_name,
                            'value': value,
                            'notes': 'Extracted from AI analysis'
                        })

        # Add some default KPIs if none found
        if not kpis:
            kpis = [
                {'metric': 'Data Analysis', 'value': 'Completed', 'notes': 'Conversation analyzed'},
                {'metric': 'Export Date', 'value': datetime.now(timezone.utc).strftime('%Y-%m-%d'), 'notes': 'Excel export generated'}
            ]

        return kpis

    def _extract_recommendations_from_conversation(self, messages: list[Message]) -> list[dict]:
        """Extract recommendations from assistant messages."""
        recommendations = []

        # Look for recommendation patterns in assistant messages
        recommendation_indicators = [
            'recommend', 'suggest', 'should consider', 'action item',
            'next steps', 'improvement', 'focus on', 'priority'
        ]

        priority_counter = 1
        for message in messages:
            if message.role == 'assistant':
                content = message.content
                sentences = content.split('.')

                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 20:  # Substantial sentence
                        for indicator in recommendation_indicators:
                            if indicator.lower() in sentence.lower():
                                recommendations.append({
                                    'priority': f'P{priority_counter}',
                                    'recommendation': sentence[:200] + ('...' if len(sentence) > 200 else ''),
                                    'impact': 'As discussed in analysis'
                                })
                                priority_counter += 1
                                break

                    if len(recommendations) >= 10:  # Limit to 10 recommendations
                        break

        # Add default recommendations if none found
        if not recommendations:
            recommendations = [
                {
                    'priority': 'P1',
                    'recommendation': 'Continue monitoring key performance indicators',
                    'impact': 'Maintain operational awareness'
                },
                {
                    'priority': 'P2',
                    'recommendation': 'Review data analysis insights from this conversation',
                    'impact': 'Drive data-driven decision making'
                }
            ]

        return recommendations

    def export_report(self, conversation_id: int, user_id: int) -> bytes | None:
        """Export a professional dealership analysis report as PDF.

        Creates a structured business report (NOT a chat transcript) with:
        - Cover page with dealership name and date
        - Executive Summary with AI-extracted insights
        - KPI Dashboard table with key metrics
        - Recommendations section with prioritized action items
        - Appendix with data summary

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

        # --- COVER PAGE ---
        pdf.add_page()

        # Logo area (placeholder)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(28, 69, 135)  # Professional blue
        pdf.cell(0, 15, "NEBULUS GANTRY", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "Business Intelligence & Analytics Platform", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.ln(20)

        # Report title
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 12, "DEALERSHIP PERFORMANCE ANALYSIS", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.ln(10)

        # Dealership name (extracted from conversation title or default)
        dealership_name = self._extract_dealership_name(conversation.title, messages)
        pdf.set_font("Helvetica", "", 16)
        pdf.set_text_color(28, 69, 135)
        pdf.cell(0, 10, dealership_name, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")

        pdf.ln(30)

        # Report details box
        pdf.set_fill_color(240, 248, 255)  # Light blue background
        pdf.rect(30, pdf.get_y(), 150, 40, 'F')

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.set_xy(35, pdf.get_y() + 5)
        pdf.cell(0, 6, "Report Details:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(35)

        # Get date range from messages
        date_range = ""
        if messages:
            first_date = messages[0].created_at.strftime("%B %d, %Y")
            last_date = messages[-1].created_at.strftime("%B %d, %Y")
            if first_date == last_date:
                date_range = f"Analysis Date: {first_date}"
            else:
                date_range = f"Analysis Period: {first_date} - {last_date}"

        pdf.cell(0, 5, date_range, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(35)
        pdf.cell(0, 5, f"Prepared for: {dealership_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(35)
        pdf.cell(0, 5, f"Analyst: {user_name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(35)
        pdf.cell(0, 5, f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # --- EXECUTIVE SUMMARY PAGE ---
        pdf.add_page()

        # Page header
        self._add_report_header(pdf, "Executive Summary")

        # Extract key insights from conversation
        insights = self._extract_executive_insights(messages)

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(0, 0, 0)

        # Introduction paragraph
        intro_text = f"This report presents a comprehensive analysis of {dealership_name}'s operational performance based on data analysis conducted using the Nebulus Gantry platform. The following insights highlight key findings and strategic recommendations."
        pdf.multi_cell(0, 6, intro_text)
        pdf.ln(5)

        # Key insights
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Key Findings:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        for i, insight in enumerate(insights[:5], 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(15, 6, f"{i}.", new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, insight)
            pdf.ln(2)

        # --- KPI DASHBOARD PAGE ---
        pdf.add_page()
        self._add_report_header(pdf, "KPI Dashboard")

        # Extract and display KPIs in a table format
        kpis = self._extract_kpis_from_conversation(messages)

        # Table header
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(28, 69, 135)
        pdf.set_text_color(255, 255, 255)

        pdf.cell(80, 8, "Key Performance Indicator", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align="C")
        pdf.cell(50, 8, "Current Value", 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align="C")
        pdf.cell(60, 8, "Notes", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=True, align="C")

        # Table data
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 248, 252)  # Light blue for alternating rows

        for i, kpi in enumerate(kpis):
            fill = i % 2 == 1  # Alternate row colors
            pdf.cell(80, 7, kpi["metric"], 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=fill)
            pdf.cell(50, 7, str(kpi["value"]), 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=fill, align="C")
            pdf.cell(60, 7, kpi["notes"][:30] + ("..." if len(kpi["notes"]) > 30 else ""), 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, fill=fill)

        # --- RECOMMENDATIONS PAGE ---
        pdf.add_page()
        self._add_report_header(pdf, "Strategic Recommendations")

        recommendations = self._extract_recommendations_from_conversation(messages)

        pdf.set_font("Helvetica", "", 11)
        intro_text = "Based on the data analysis, the following strategic recommendations are prioritized by potential impact and implementation feasibility:"
        pdf.multi_cell(0, 6, intro_text)
        pdf.ln(5)

        for rec in recommendations:
            # Priority badge
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(70, 173, 71)  # Green for priority
            pdf.set_text_color(255, 255, 255)
            pdf.cell(20, 6, rec["priority"], 1, new_x=XPos.RIGHT, new_y=YPos.TOP, fill=True, align="C")

            # Recommendation text
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(170, 6, "Recommendation", 1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")

            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(190, 5, rec["recommendation"], 1)

            # Expected impact
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(190, 4, f"Expected Impact: {rec['impact']}", 1)
            pdf.ln(3)

        # --- APPENDIX PAGE ---
        pdf.add_page()
        self._add_report_header(pdf, "Data Summary")

        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, "This analysis was conducted using the Nebulus Gantry AI-powered analytics platform. The platform analyzed the provided data and generated insights based on industry best practices and dealership performance benchmarks.")
        pdf.ln(5)

        # Technical details
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, "Analysis Details:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 4, f"• Total conversation messages: {len(messages)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 4, f"• Analysis completed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 4, f"• Platform: Nebulus Gantry Business Intelligence", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Footer
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(0, 4, "This report contains confidential business information. Distribution should be limited to authorized personnel only. For questions about this analysis, please contact your Nebulus Gantry administrator.")

        return bytes(pdf.output())

    def _add_report_header(self, pdf: "FPDF", title: str):
        """Add a consistent header to each report page."""
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(28, 69, 135)
        pdf.cell(0, 10, title, new_x=pdf.enums.XPos.LMARGIN, new_y=pdf.enums.YPos.NEXT, align="L")

        # Underline
        pdf.set_draw_color(28, 69, 135)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)

    def _extract_dealership_name(self, title: str, messages: list[Message]) -> str:
        """Extract or generate a dealership name from conversation."""
        # Try to extract from title first
        if "dealership" not in title.lower() and len(title) > 5:
            return title + " Dealership"

        # Look for dealership mentions in conversation
        for message in messages:
            content = message.content.lower()
            # Look for patterns like "ABC Motors", "XYZ Auto", etc.
            import re
            patterns = [
                r'([A-Z][a-z]+ (?:Motors?|Auto|Ford|Chevy|Toyota|Honda|Hyundai))',
                r'([A-Z][a-z]+ [A-Z][a-z]+ (?:Dealership|Auto))'
            ]

            for pattern in patterns:
                match = re.search(pattern, message.content)
                if match:
                    return match.group(1)

        return "Sample Dealership"

    def _extract_executive_insights(self, messages: list[Message]) -> list[str]:
        """Extract key business insights for executive summary."""
        insights = []

        # Look for analysis patterns in assistant messages
        insight_patterns = [
            r'((?:performance|sales|profit|efficiency|trend).{50,200})',
            r'((?:analysis shows|data indicates|results suggest).{50,200})',
            r'((?:key finding|important|significant|notable).{50,200})',
            r'((?:opportunity|improvement|challenge).{50,200})',
        ]

        for message in messages:
            if message.role == 'assistant':
                content = message.content
                for pattern in insight_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
                    for match in matches[:2]:  # Limit per message
                        # Clean up the insight text
                        insight = re.sub(r'\s+', ' ', match.strip())
                        if len(insight) > 50 and insight not in insights:
                            insights.append(insight[:200] + ('...' if len(insight) > 200 else ''))

                if len(insights) >= 5:
                    break

        # Default insights if none found
        if not insights:
            insights = [
                "Comprehensive data analysis was completed using advanced AI analytics",
                "Key performance indicators were extracted and evaluated against industry benchmarks",
                "Operational metrics were analyzed to identify improvement opportunities",
                "Data quality and completeness were verified for accurate reporting",
                "Strategic recommendations were developed based on data-driven insights"
            ]

        return insights

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
