"""
CSV Parser and Chunking Module for MVA appliance.

Parses CSV files into LLM-friendly chunks with repeated headers,
auto-detects delimiters, handles encoding fallbacks, and generates
summary statistics for dealership data analysis.
"""
import csv
import io
import logging
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 50
DEFAULT_MAX_ROWS = 10_000
ENCODINGS = ("utf-8", "latin-1", "cp1252")
DELIMITERS = (",", "\t", ";", "|")


@dataclass
class CSVChunk:
    """A single chunk of CSV data with metadata."""

    chunk_index: int
    total_chunks: int
    total_rows: int
    columns: list[str]
    rows: list[list[str]]
    text: str


@dataclass
class NumericStats:
    """Summary statistics for a numeric column."""

    min: float
    max: float
    mean: float
    count: int


@dataclass
class CSVSummary:
    """Summary statistics for an entire CSV file."""

    total_rows: int
    total_columns: int
    columns: list[str]
    numeric_stats: dict[str, NumericStats] = field(default_factory=dict)
    categorical_counts: dict[str, dict[str, int]] = field(default_factory=dict)


class CSVParseError(Exception):
    """Raised when CSV parsing fails validation."""


def detect_encoding(raw: bytes) -> str:
    """Detect file encoding by trying common encodings in order.

    Args:
        raw: Raw file bytes.

    Returns:
        The encoding name that successfully decoded the bytes.

    Raises:
        CSVParseError: If no encoding works.
    """
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, ValueError):
            continue
    raise CSVParseError("Unable to decode file with any supported encoding")


def detect_delimiter(sample: str) -> str:
    """Auto-detect CSV delimiter from a text sample.

    Args:
        sample: First few lines of CSV text.

    Returns:
        Detected delimiter character.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(DELIMITERS))
        return dialect.delimiter
    except csv.Error:
        # Fallback: count occurrences in first line
        first_line = sample.split("\n", 1)[0]
        counts = {d: first_line.count(d) for d in DELIMITERS}
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        return best if counts[best] > 0 else ","


def read_csv_bytes(
    raw: bytes,
) -> tuple[str, str, list[list[str]]]:
    """Decode raw bytes and parse CSV rows.

    Args:
        raw: Raw file bytes.

    Returns:
        Tuple of (encoding, delimiter, all_rows_including_header).

    Raises:
        CSVParseError: On empty or unreadable files.
    """
    if not raw or not raw.strip():
        raise CSVParseError("CSV file is empty")

    encoding = detect_encoding(raw)
    text = raw.decode(encoding)

    # Strip BOM if present
    if text.startswith("\ufeff"):
        text = text[1:]

    delimiter = detect_delimiter(text[:4096])
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        raise CSVParseError("CSV file contains no data")
    if len(rows) < 2:
        raise CSVParseError("CSV file has headers but no data rows")

    return encoding, delimiter, rows


def read_csv_file(
    path: str | Path,
) -> tuple[str, str, list[list[str]]]:
    """Read a CSV file from disk and parse it.

    Args:
        path: Path to the CSV file.

    Returns:
        Tuple of (encoding, delimiter, all_rows_including_header).

    Raises:
        CSVParseError: On missing, empty, or unreadable files.
        FileNotFoundError: If the file doesn't exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    raw = p.read_bytes()
    return read_csv_bytes(raw)


def chunk_csv(
    headers: list[str],
    data_rows: list[list[str]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    delimiter: str = ",",
) -> list[CSVChunk]:
    """Split CSV data into chunks with headers repeated in each.

    Args:
        headers: Column header names.
        data_rows: Data rows (list of lists).
        chunk_size: Maximum rows per chunk.
        delimiter: Delimiter for text rendering.

    Returns:
        List of CSVChunk objects.
    """
    if not data_rows:
        text = delimiter.join(headers)
        return [
            CSVChunk(
                chunk_index=0,
                total_chunks=1,
                total_rows=0,
                columns=headers,
                rows=[],
                text=text,
            )
        ]

    total_rows = len(data_rows)
    total_chunks = (total_rows + chunk_size - 1) // chunk_size
    chunks: list[CSVChunk] = []
    header_line = delimiter.join(headers)

    for i in range(0, total_rows, chunk_size):
        batch = data_rows[i : i + chunk_size]
        lines = [header_line]
        for row in batch:
            lines.append(delimiter.join(row))
        chunks.append(
            CSVChunk(
                chunk_index=len(chunks),
                total_chunks=total_chunks,
                total_rows=total_rows,
                columns=headers,
                rows=batch,
                text="\n".join(lines),
            )
        )

    return chunks


def parse_csv(
    source: str | Path | bytes,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> list[CSVChunk]:
    """Parse a CSV file or bytes into LLM-friendly chunks.

    Args:
        source: File path or raw bytes.
        chunk_size: Maximum rows per chunk.
        max_rows: Maximum total rows to process.

    Returns:
        List of CSVChunk objects with headers repeated per chunk.

    Raises:
        CSVParseError: On validation failure.
        FileNotFoundError: If file path doesn't exist.
    """
    if isinstance(source, bytes):
        encoding, delimiter, rows = read_csv_bytes(source)
    else:
        encoding, delimiter, rows = read_csv_file(source)

    headers = rows[0]
    data_rows = rows[1:]

    if len(data_rows) > max_rows:
        logger.warning(
            "CSV has %d rows, capping at %d", len(data_rows), max_rows
        )
        data_rows = data_rows[:max_rows]

    return chunk_csv(headers, data_rows, chunk_size=chunk_size, delimiter=delimiter)


def generate_summary(
    headers: list[str],
    data_rows: list[list[str]],
    max_categorical_values: int = 20,
) -> CSVSummary:
    """Generate summary statistics for CSV data.

    Args:
        headers: Column header names.
        data_rows: Data rows.
        max_categorical_values: Max unique values before skipping
            categorical counts.

    Returns:
        CSVSummary with numeric stats and categorical value counts.
    """
    summary = CSVSummary(
        total_rows=len(data_rows),
        total_columns=len(headers),
        columns=list(headers),
    )

    for col_idx, col_name in enumerate(headers):
        values: list[str] = []
        numeric_values: list[float] = []

        for row in data_rows:
            if col_idx < len(row):
                val = row[col_idx].strip()
                if val:
                    values.append(val)
                    try:
                        numeric_values.append(float(val.replace(",", "")))
                    except ValueError:
                        pass

        # If >50% of non-empty values are numeric, treat as numeric
        if numeric_values and len(numeric_values) >= len(values) * 0.5:
            summary.numeric_stats[col_name] = NumericStats(
                min=min(numeric_values),
                max=max(numeric_values),
                mean=statistics.mean(numeric_values),
                count=len(numeric_values),
            )
        elif values:
            unique = set(values)
            if len(unique) <= max_categorical_values:
                counts: dict[str, int] = {}
                for v in values:
                    counts[v] = counts.get(v, 0) + 1
                summary.categorical_counts[col_name] = counts

    return summary


def parse_and_summarize(
    source: str | Path | bytes,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> tuple[list[CSVChunk], CSVSummary]:
    """Parse CSV into chunks and generate summary statistics.

    Args:
        source: File path or raw bytes.
        chunk_size: Maximum rows per chunk.
        max_rows: Maximum total rows to process.

    Returns:
        Tuple of (chunks, summary).
    """
    if isinstance(source, bytes):
        _, delimiter, rows = read_csv_bytes(source)
    else:
        _, delimiter, rows = read_csv_file(source)

    headers = rows[0]
    data_rows = rows[1:]

    if len(data_rows) > max_rows:
        logger.warning(
            "CSV has %d rows, capping at %d", len(data_rows), max_rows
        )
        data_rows = data_rows[:max_rows]

    chunks = chunk_csv(
        headers, data_rows, chunk_size=chunk_size, delimiter=delimiter
    )
    summary = generate_summary(headers, data_rows)
    return chunks, summary
