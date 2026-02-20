"""Router for welcome screen suggestions.

Provides quick-start prompt suggestions for the Gantry chat UI.
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


_DEFAULT_SUGGESTIONS: list[Suggestion] = [
    Suggestion(
        id="explain-code",
        label="Explain Code",
        prompt="Explain this code and suggest improvements",
        icon="code",
    ),
    Suggestion(
        id="brainstorm",
        label="Brainstorm Ideas",
        prompt="Help me brainstorm solutions for a technical challenge",
        icon="lightbulb",
    ),
    Suggestion(
        id="write-docs",
        label="Write Documentation",
        prompt="Help me write clear documentation for my project",
        icon="document-text",
    ),
    Suggestion(
        id="debug-help",
        label="Debug Something",
        prompt="Help me debug an issue I'm running into",
        icon="bug",
    ),
]


@router.get("/suggestions", response_model=SuggestionsResponse)
def get_suggestions() -> SuggestionsResponse:
    """Return quick-start prompt suggestions for the welcome screen."""
    return SuggestionsResponse(suggestions=_DEFAULT_SUGGESTIONS)
