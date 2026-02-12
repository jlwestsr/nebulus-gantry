"""Router for welcome screen suggestions.

Provides quick-start prompt suggestions for the dealership chat UI.
No authentication required — this is pre-login content.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["suggestions"])


class Suggestion(BaseModel):
    """A single quick-start prompt suggestion."""

    id: str
    label: str
    prompt: str
    icon: str | None = None


class SuggestionsResponse(BaseModel):
    """Response model for the suggestions endpoint."""

    suggestions: list[Suggestion]


# Hardcoded dealership-specific suggestions. Structured for future
# configurability (e.g., per-tenant or database-driven).
_DEFAULT_SUGGESTIONS: list[Suggestion] = [
    Suggestion(
        id="sales-30d",
        label="Sales Analysis",
        prompt="Analyze my sales data for the last 30 days",
        icon="chart-bar",
    ),
    Suggestion(
        id="aged-inventory",
        label="Aged Inventory",
        prompt="Which vehicles have been on the lot longer than 60 days?",
        icon="clock",
    ),
    Suggestion(
        id="fi-benchmarks",
        label="F&I Benchmarks",
        prompt="Compare my F&I penetration rates to industry benchmarks",
        icon="scale",
    ),
    Suggestion(
        id="top-performers",
        label="Top Performers",
        prompt="Show me my top-performing salespeople this month",
        icon="trophy",
    ),
]


@router.get("/suggestions", response_model=SuggestionsResponse)
def get_suggestions() -> SuggestionsResponse:
    """Return quick-start prompt suggestions for the welcome screen.

    Returns:
        SuggestionsResponse: A list of dealership-specific prompt suggestions.
    """
    return SuggestionsResponse(suggestions=_DEFAULT_SUGGESTIONS)
