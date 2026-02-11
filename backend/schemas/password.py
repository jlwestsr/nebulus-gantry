"""Password validation utilities.

Provides a reusable Pydantic validator and standalone validation function
for enforcing password policy. Follows NIST 800-63B guidance: enforce
length and block common passwords, but do NOT require special characters.
"""

from pydantic import BaseModel, field_validator

# Top ~100 common passwords (lowercase for comparison).
BLOCKED_PASSWORDS: frozenset[str] = frozenset({
    "password", "12345678", "123456789", "1234567890", "12345678910",
    "qwerty12", "qwerty123", "qwertyuiop", "iloveyou", "admin123",
    "welcome1", "letmein1", "monkey12", "dragon12", "master12",
    "trustno1", "baseball1", "shadow12", "michael1", "football1",
    "jennifer", "jordan23", "superman1", "harley12", "ranger12",
    "abcdefgh", "abcd1234", "abc12345", "1q2w3e4r", "q1w2e3r4",
    "passw0rd", "p@ssword", "p@ssw0rd", "changeme", "welcome",
    "letmein", "sunshine", "princess", "football", "charlie",
    "access14", "mustang1", "shadow1", "master1", "michael",
    "ashley12", "jessica1", "charlie1", "thomas12", "george12",
    "computer", "internet", "whatever", "starwars", "mercedes",
    "password1", "password12", "password123", "pass1234", "passwd12",
    "qwerty1234", "asdfghjk", "asdf1234", "zxcvbnm1", "1234qwer",
    "admin1234", "root1234", "login123", "welcome123", "hello123",
    "monkey123", "dragon123", "master123", "qazwsx12", "test1234",
    "guest1234", "default1", "temp1234", "pass12345", "user1234",
    "secret12", "secret123", "baseball", "trustno12", "access123",
    "flower12", "hottie12", "loveme12", "zaq12wsx", "mustang",
    "batman12", "access12", "thunder1", "ginger12", "hammer12",
    "silver12", "summer12", "george1", "diamond1", "jackson1",
    "brandon1", "elizabeth", "jessica", "joshua12", "maggie12",
    "yankees1", "corvette", "camaro12", "firebird", "dealer12",
    "dealership", "carsales", "autosale", "cardealer",
})
"""Blocked common passwords. Compared case-insensitively."""

MIN_LENGTH: int = 8
MAX_LENGTH: int = 128


def validate_password(password: str) -> list[str]:
    """Validate a password against the policy and return error messages.

    Args:
        password: The password string to validate.

    Returns:
        A list of human-readable error strings. Empty list means valid.
    """
    errors: list[str] = []

    if len(password) < MIN_LENGTH:
        errors.append(f"Password must be at least {MIN_LENGTH} characters.")

    if len(password) > MAX_LENGTH:
        errors.append(f"Password must be {MAX_LENGTH} characters or fewer.")

    if password.lower() in BLOCKED_PASSWORDS:
        errors.append("This password is too common. Please choose something less guessable.")

    has_letter = any(c.isalpha() for c in password)
    has_number = any(c.isdigit() for c in password)

    if not has_letter:
        errors.append("Password must contain at least one letter.")

    if not has_number:
        errors.append("Password must contain at least one number.")

    return errors


class PasswordMixin(BaseModel):
    """Mixin providing a validated ``password`` field.

    Inherit from this (or copy the validator) in any schema that accepts
    a new password — e.g. registration, change-password, first-boot setup.

    Example::

        class CreateUserRequest(PasswordMixin):
            email: EmailStr
            display_name: str
    """

    password: str

    @field_validator("password")
    @classmethod
    def check_password_policy(cls, v: str) -> str:
        """Validate password against the policy.

        Args:
            v: The password value.

        Returns:
            The password unchanged if valid.

        Raises:
            ValueError: With a combined error message if validation fails.
        """
        errors = validate_password(v)
        if errors:
            raise ValueError(" ".join(errors))
        return v
