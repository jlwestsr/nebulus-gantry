"""Tests for backend.services.secret_key_manager."""

from __future__ import annotations

import os
import stat
import threading
from pathlib import Path

import pytest

from backend.services.secret_key_manager import (
    _KEY_FILENAME,
    _generate_key,
    _key_path,
    _read_key,
    _write_key,
    get_secret_key,
    rotate_secret_key,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_mode(p: Path) -> int:
    """Return the permission bits of *p*."""
    return stat.S_IMODE(p.stat().st_mode)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateKey:
    """Unit tests for raw key generation."""

    def test_length(self) -> None:
        """Generated key should be 64 hex characters (32 bytes)."""
        key = _generate_key()
        assert len(key) == 64

    def test_hex_encoding(self) -> None:
        """Key must be valid hex."""
        key = _generate_key()
        int(key, 16)  # raises ValueError if not hex

    def test_uniqueness(self) -> None:
        """Two generated keys must differ."""
        assert _generate_key() != _generate_key()


class TestKeyPath:
    """Tests for _key_path helper."""

    def test_returns_expected_path(self, tmp_path: Path) -> None:
        assert _key_path(tmp_path) == tmp_path / _KEY_FILENAME


class TestWriteAndRead:
    """Tests for low-level write/read helpers."""

    def test_write_creates_file(self, tmp_path: Path) -> None:
        key_file = tmp_path / _KEY_FILENAME
        _write_key(key_file, "aabbccdd")
        assert key_file.exists()

    def test_write_sets_permissions(self, tmp_path: Path) -> None:
        key_file = tmp_path / _KEY_FILENAME
        _write_key(key_file, "aabbccdd")
        assert _file_mode(key_file) == 0o600

    def test_read_returns_none_missing(self, tmp_path: Path) -> None:
        assert _read_key(tmp_path / "nope") is None

    def test_read_returns_none_empty(self, tmp_path: Path) -> None:
        key_file = tmp_path / _KEY_FILENAME
        key_file.write_text("")
        assert _read_key(key_file) is None

    def test_round_trip(self, tmp_path: Path) -> None:
        key_file = tmp_path / _KEY_FILENAME
        _write_key(key_file, "deadbeef01")
        assert _read_key(key_file) == "deadbeef01"


class TestGetSecretKey:
    """Integration tests for get_secret_key."""

    def test_generates_when_absent(self, tmp_path: Path) -> None:
        key = get_secret_key(tmp_path)
        assert len(key) == 64

    def test_persists_to_disk(self, tmp_path: Path) -> None:
        key = get_secret_key(tmp_path)
        assert (tmp_path / _KEY_FILENAME).read_text().strip() == key

    def test_reloads_existing(self, tmp_path: Path) -> None:
        first = get_secret_key(tmp_path)
        second = get_secret_key(tmp_path)
        assert first == second

    def test_file_permissions(self, tmp_path: Path) -> None:
        get_secret_key(tmp_path)
        assert _file_mode(tmp_path / _KEY_FILENAME) == 0o600

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b"
        key = get_secret_key(nested)
        assert len(key) == 64
        assert (nested / _KEY_FILENAME).exists()


class TestRotateSecretKey:
    """Tests for rotate_secret_key."""

    def test_returns_new_key(self, tmp_path: Path) -> None:
        original = get_secret_key(tmp_path)
        rotated = rotate_secret_key(tmp_path)
        assert rotated != original

    def test_persists_rotated_key(self, tmp_path: Path) -> None:
        get_secret_key(tmp_path)
        rotated = rotate_secret_key(tmp_path)
        assert get_secret_key(tmp_path) == rotated

    def test_file_permissions_after_rotation(self, tmp_path: Path) -> None:
        get_secret_key(tmp_path)
        rotate_secret_key(tmp_path)
        assert _file_mode(tmp_path / _KEY_FILENAME) == 0o600


class TestConcurrentAccess:
    """Verify no corruption under concurrent writes."""

    def test_concurrent_rotations(self, tmp_path: Path) -> None:
        """Multiple threads rotating simultaneously must each produce a valid key."""
        get_secret_key(tmp_path)
        results: list[str] = []
        errors: list[Exception] = []

        def _rotate() -> None:
            try:
                results.append(rotate_secret_key(tmp_path))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=_rotate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Unexpected errors: {errors}"
        # The file must contain a valid 64-char hex key.
        final = get_secret_key(tmp_path)
        assert len(final) == 64
        int(final, 16)

    def test_concurrent_reads(self, tmp_path: Path) -> None:
        """Concurrent reads must all return the same key."""
        expected = get_secret_key(tmp_path)
        results: list[str] = []

        def _read() -> None:
            results.append(get_secret_key(tmp_path))

        threads = [threading.Thread(target=_read) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r == expected for r in results)
