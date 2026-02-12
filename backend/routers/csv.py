"""
CSV Upload Router for Nebulus Gantry.

Endpoints for uploading and analyzing CSV files via the csv_parser service.

To register in main.py, add:
    from backend.routers import csv
    app.include_router(csv.router)
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.routers.auth import get_current_user
from backend.utils.csv_rate_limit import (
    check_csv_analyze_rate_limit,
    check_csv_upload_rate_limit,
)
from backend.services.csv_parser import (
    CSVChunk,
    CSVParseError,
    CSVSummary,
    NumericStats,
    parse_and_summarize,
)

logger = logging.getLogger(__name__)

# Configurable max file size (bytes). Default 10 MB.
MAX_FILE_SIZE: int = 10 * 1024 * 1024

ALLOWED_EXTENSIONS: set[str] = {".csv", ".tsv", ".txt"}

router = APIRouter(prefix="/api/csv", tags=["csv"])


# ========== Response Models ==========


class NumericStatsResponse(BaseModel):
    """Numeric column statistics."""

    min: float
    max: float
    mean: float
    count: int


class CSVSummaryResponse(BaseModel):
    """Summary statistics for a CSV file."""

    total_rows: int
    total_columns: int
    columns: list[str]
    numeric_stats: dict[str, NumericStatsResponse] = Field(default_factory=dict)
    categorical_counts: dict[str, dict[str, int]] = Field(default_factory=dict)


class CSVChunkResponse(BaseModel):
    """A single chunk of CSV data."""

    chunk_index: int
    total_chunks: int
    total_rows: int
    columns: list[str]
    rows: list[list[str]]
    text: str


class CSVUploadResponse(BaseModel):
    """Response for CSV upload endpoint."""

    filename: str
    chunks: list[CSVChunkResponse]
    summary: CSVSummaryResponse


class CSVAnalyzeResponse(BaseModel):
    """Response for CSV analyze endpoint."""

    filename: str
    question: str
    chunks: list[CSVChunkResponse]
    summary: CSVSummaryResponse


# ========== Helpers ==========


def _validate_extension(filename: str | None) -> str:
    """Validate file extension and return the cleaned filename.

    Args:
        filename: Original filename from the upload.

    Returns:
        The filename string.

    Raises:
        HTTPException: 400 if extension is not allowed.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return filename


async def _read_and_validate_size(file: UploadFile) -> bytes:
    """Read upload content and enforce size limit.

    Args:
        file: The uploaded file.

    Returns:
        Raw file bytes.

    Raises:
        HTTPException: 413 if file exceeds MAX_FILE_SIZE.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )
    return content


def _build_summary_response(summary: CSVSummary) -> CSVSummaryResponse:
    """Convert a CSVSummary dataclass to a Pydantic response model."""
    numeric = {
        k: NumericStatsResponse(min=v.min, max=v.max, mean=v.mean, count=v.count)
        for k, v in summary.numeric_stats.items()
    }
    return CSVSummaryResponse(
        total_rows=summary.total_rows,
        total_columns=summary.total_columns,
        columns=summary.columns,
        numeric_stats=numeric,
        categorical_counts=summary.categorical_counts,
    )


def _build_chunks_response(chunks: list[CSVChunk]) -> list[CSVChunkResponse]:
    """Convert CSVChunk dataclasses to Pydantic response models."""
    return [
        CSVChunkResponse(
            chunk_index=c.chunk_index,
            total_chunks=c.total_chunks,
            total_rows=c.total_rows,
            columns=c.columns,
            rows=c.rows,
            text=c.text,
        )
        for c in chunks
    ]


# ========== Endpoints ==========


@router.post("/upload", response_model=CSVUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a CSV file and return parsed chunks with summary statistics.

    Args:
        file: The CSV file to upload.
        user: Authenticated user (injected).

    Returns:
        Parsed chunks and summary statistics.
    """
    check_csv_upload_rate_limit(user.email)
    filename = _validate_extension(file.filename)
    content = await _read_and_validate_size(file)

    try:
        chunks, summary = parse_and_summarize(content)
    except CSVParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error parsing CSV: %s", e)
        raise HTTPException(status_code=422, detail="Failed to parse CSV file.")

    return CSVUploadResponse(
        filename=filename,
        chunks=_build_chunks_response(chunks),
        summary=_build_summary_response(summary),
    )


@router.post("/analyze", response_model=CSVAnalyzeResponse)
async def analyze_csv(
    file: UploadFile = File(...),
    question: str = Form(...),
    user=Depends(get_current_user),
):
    """Upload a CSV file with a question for downstream LLM analysis.

    Args:
        file: The CSV file to analyze.
        question: The analysis question to answer.
        user: Authenticated user (injected).

    Returns:
        Parsed chunks, summary statistics, and the question for LLM integration.
    """
    check_csv_analyze_rate_limit(user.email)
    filename = _validate_extension(file.filename)
    content = await _read_and_validate_size(file)

    try:
        chunks, summary = parse_and_summarize(content)
    except CSVParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error parsing CSV: %s", e)
        raise HTTPException(status_code=422, detail="Failed to parse CSV file.")

    return CSVAnalyzeResponse(
        filename=filename,
        question=question,
        chunks=_build_chunks_response(chunks),
        summary=_build_summary_response(summary),
    )
