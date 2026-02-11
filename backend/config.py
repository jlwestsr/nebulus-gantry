import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

SECRET_KEY_FILE = Path("data/.secret_key")


def _get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/gantry.db")


def _get_secret_key() -> str:
    """Return the secret key for session signing.

    Priority: SECRET_KEY env var > persisted file > generate new.
    """
    env_key = os.getenv("SECRET_KEY")
    if env_key:
        return env_key

    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text().strip()

    logger.warning(
        "SECRET_KEY not set — generating random key and persisting to %s",
        SECRET_KEY_FILE,
    )
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_KEY_FILE.write_text(key)
    SECRET_KEY_FILE.chmod(0o600)
    return key


def _get_session_expire_hours() -> int:
    return int(os.getenv("SESSION_EXPIRE_HOURS", "24"))


def _get_overlord_routing_enabled() -> bool:
    return os.getenv("OVERLORD_ROUTING_ENABLED", "true").lower() in ("true", "1", "yes")


def _get_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS")
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:5173", "http://localhost:3000"]


def _get_bind_host() -> str:
    return os.getenv("BIND_HOST", "127.0.0.1")


def _get_https_enabled() -> bool:
    return os.getenv("HTTPS_ENABLED", "false").lower() in ("true", "1", "yes")


@dataclass
class Settings:
    database_url: str = field(default_factory=_get_database_url)
    secret_key: str = field(default_factory=_get_secret_key)
    session_expire_hours: int = field(default_factory=_get_session_expire_hours)
    overlord_routing_enabled: bool = field(default_factory=_get_overlord_routing_enabled)
    cors_origins: list[str] = field(default_factory=_get_cors_origins)
    bind_host: str = field(default_factory=_get_bind_host)
    https_enabled: bool = field(default_factory=_get_https_enabled)


settings = Settings()
