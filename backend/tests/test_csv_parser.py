"""Tests for the CSV parser/chunking module."""
import csv
import io
import tempfile
from pathlib import Path

import pytest

from backend.services.csv_parser import (
    CSVChunk,
    CSVParseError,
    CSVSummary,
    NumericStats,
    chunk_csv,
    detect_delimiter,
    detect_encoding,
    generate_summary,
    parse_and_summarize,
    parse_csv,
    read_csv_bytes,
)

FIXTURES = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"
SALES_CSV = FIXTURES / "sample_sales.csv"
SERVICE_CSV = FIXTURES / "sample_service.csv"
INVENTORY_CSV = FIXTURES / "sample_inventory.csv"


# ── Basic parsing ──────────────────────────────────────────────


class TestBasicParsing:
    def test_parse_sales_csv(self):
        chunks = parse_csv(SALES_CSV)
        assert len(chunks) >= 1
        assert chunks[0].columns[0] == "Date"
        assert chunks[0].total_rows > 0

    def test_parse_service_csv(self):
        chunks = parse_csv(SERVICE_CSV)
        assert chunks[0].columns[0] == "RONumber"

    def test_parse_inventory_csv(self):
        chunks = parse_csv(INVENTORY_CSV)
        assert "StockNo" in chunks[0].columns
        assert "VIN" in chunks[0].columns

    def test_parse_from_bytes(self):
        raw = SALES_CSV.read_bytes()
        chunks = parse_csv(raw)
        assert len(chunks) >= 1
        assert chunks[0].total_rows > 0


# ── Chunking ───────────────────────────────────────────────────


class TestChunking:
    def test_headers_repeat_in_every_chunk(self):
        chunks = parse_csv(SALES_CSV, chunk_size=5)
        header_line = ",".join(chunks[0].columns)
        for chunk in chunks:
            assert chunk.text.startswith(header_line)

    def test_chunk_size_respected(self):
        chunks = parse_csv(SALES_CSV, chunk_size=10)
        for chunk in chunks[:-1]:  # all but last
            assert len(chunk.rows) == 10
        assert len(chunks[-1].rows) <= 10

    def test_chunk_metadata_consistent(self):
        chunks = parse_csv(SALES_CSV, chunk_size=10)
        total = chunks[0].total_rows
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.total_chunks == len(chunks)
            assert chunk.total_rows == total

    def test_single_chunk_small_file(self):
        raw = b"a,b,c\n1,2,3\n4,5,6\n"
        chunks = parse_csv(raw, chunk_size=50)
        assert len(chunks) == 1
        assert chunks[0].total_rows == 2


# ── Delimiter detection ────────────────────────────────────────


class TestDelimiterDetection:
    def test_comma(self):
        assert detect_delimiter("a,b,c\n1,2,3") == ","

    def test_tab(self):
        assert detect_delimiter("a\tb\tc\n1\t2\t3") == "\t"

    def test_semicolon(self):
        assert detect_delimiter("a;b;c\n1;2;3") == ";"

    def test_pipe(self):
        assert detect_delimiter("a|b|c\n1|2|3") == "|"

    def test_tab_delimited_parsing(self):
        raw = "name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n".encode()
        chunks = parse_csv(raw)
        assert chunks[0].columns == ["name", "age", "city"]
        assert chunks[0].rows[0] == ["Alice", "30", "NYC"]


# ── Encoding handling ──────────────────────────────────────────


class TestEncoding:
    def test_utf8(self):
        raw = "name,city\nJosé,São Paulo\n".encode("utf-8")
        chunks = parse_csv(raw)
        assert chunks[0].rows[0][0] == "José"

    def test_latin1_fallback(self):
        raw = "name,city\nJosé,São Paulo\n".encode("latin-1")
        chunks = parse_csv(raw)
        assert "Jos" in chunks[0].rows[0][0]

    def test_detect_encoding_utf8(self):
        assert detect_encoding(b"hello") == "utf-8"

    def test_detect_encoding_latin1(self):
        raw = "café".encode("latin-1")
        enc = detect_encoding(raw)
        assert enc in ("utf-8", "latin-1")


# ── Max row cap ────────────────────────────────────────────────


class TestMaxRowCap:
    def test_cap_enforced(self):
        lines = ["a,b"] + [f"{i},{i+1}" for i in range(200)]
        raw = "\n".join(lines).encode()
        chunks = parse_csv(raw, max_rows=50)
        total = sum(len(c.rows) for c in chunks)
        assert total == 50

    def test_cap_default_allows_normal_files(self):
        chunks = parse_csv(SALES_CSV)
        assert chunks[0].total_rows <= 10_000


# ── Empty / malformed ──────────────────────────────────────────


class TestValidation:
    def test_empty_bytes(self):
        with pytest.raises(CSVParseError, match="empty"):
            parse_csv(b"")

    def test_whitespace_only(self):
        with pytest.raises(CSVParseError, match="empty"):
            parse_csv(b"   \n  \n  ")

    def test_header_only_no_data(self):
        with pytest.raises(CSVParseError, match="no data rows"):
            parse_csv(b"a,b,c\n")

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_csv("/nonexistent/path.csv")


# ── Summary statistics ─────────────────────────────────────────


class TestSummaryStats:
    def test_sales_summary(self):
        chunks, summary = parse_and_summarize(SALES_CSV)
        assert summary.total_rows > 0
        assert summary.total_columns > 0
        assert "SalePrice" in summary.numeric_stats
        stats = summary.numeric_stats["SalePrice"]
        assert stats.min <= stats.mean <= stats.max

    def test_inventory_summary(self):
        _, summary = parse_and_summarize(INVENTORY_CSV)
        assert "Mileage" in summary.numeric_stats
        assert summary.numeric_stats["Mileage"].count > 0

    def test_categorical_counts(self):
        _, summary = parse_and_summarize(INVENTORY_CSV)
        # Status or Source should be categorical
        has_cat = len(summary.categorical_counts) > 0
        assert has_cat

    def test_service_summary_numeric(self):
        _, summary = parse_and_summarize(SERVICE_CSV)
        assert "LaborHours" in summary.numeric_stats
        assert "TotalCost" in summary.numeric_stats

    def test_summary_from_bytes(self):
        raw = SALES_CSV.read_bytes()
        _, summary = parse_and_summarize(raw)
        assert summary.total_rows > 0
