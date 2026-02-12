"""Tests for password validation."""

import pytest
from pydantic import ValidationError

from backend.schemas.password import (
    BLOCKED_PASSWORDS,
    MAX_LENGTH,
    MIN_LENGTH,
    PasswordMixin,
    validate_password,
)


# ---------------------------------------------------------------------------
# Standalone function tests
# ---------------------------------------------------------------------------

class TestValidatePassword:
    """Tests for the validate_password() function."""

    def test_valid_password(self):
        """A reasonable password should pass with no errors."""
        assert validate_password("mySecret42") == []

    def test_valid_minimum_length(self):
        """Exactly MIN_LENGTH chars with letter + number should pass."""
        assert validate_password("abcdefg1") == []

    def test_too_short(self):
        """Passwords shorter than MIN_LENGTH should fail."""
        errors = validate_password("short1")
        assert any("at least" in e for e in errors)

    def test_too_long(self):
        """Passwords exceeding MAX_LENGTH should fail."""
        errors = validate_password("a1" * 100)
        assert any(str(MAX_LENGTH) in e for e in errors)

    def test_blocked_password(self):
        """Common passwords from the blocklist should fail."""
        errors = validate_password("password")
        assert any("too common" in e for e in errors)

    def test_blocked_password_case_insensitive(self):
        """Blocklist check should be case-insensitive."""
        errors = validate_password("Password")
        assert any("too common" in e for e in errors)

    def test_no_letter(self):
        """All-digit password should fail the letter requirement."""
        errors = validate_password("123456789")
        assert any("letter" in e for e in errors)

    def test_no_number(self):
        """All-letter password should fail the number requirement."""
        errors = validate_password("abcdefghi")
        assert any("number" in e for e in errors)

    def test_multiple_errors(self):
        """A truly bad password should return multiple errors."""
        errors = validate_password("abc")
        assert len(errors) >= 2  # too short + no number

    def test_spaces_allowed(self):
        """Passwords with spaces should be valid (passphrases)."""
        assert validate_password("my pass phrase 7") == []

    def test_unicode_allowed(self):
        """Unicode characters should be accepted."""
        assert validate_password("café2024!") == []

    def test_special_chars_not_required(self):
        """NIST 800-63B: special characters should NOT be required."""
        assert validate_password("simplepass1") == []

    def test_empty_string(self):
        """Empty string should fail."""
        errors = validate_password("")
        assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Pydantic mixin tests
# ---------------------------------------------------------------------------

class _TestSchema(PasswordMixin):
    """Concrete schema for testing the mixin."""
    username: str


class TestPasswordMixin:
    """Tests for the PasswordMixin Pydantic validator."""

    def test_valid_schema(self):
        """Valid data should create the model."""
        obj = _TestSchema(username="alice", password="goodPass1")
        assert obj.password == "goodPass1"

    def test_invalid_raises_validation_error(self):
        """Invalid password should raise Pydantic ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            _TestSchema(username="bob", password="short")
        assert "at least" in str(exc_info.value)

    def test_blocked_via_mixin(self):
        """Blocked password should fail through the mixin."""
        with pytest.raises(ValidationError) as exc_info:
            _TestSchema(username="eve", password="password1")
        assert "too common" in str(exc_info.value)

    def test_no_number_via_mixin(self):
        """No-number password should fail through the mixin."""
        with pytest.raises(ValidationError):
            _TestSchema(username="mallory", password="alllettters")
