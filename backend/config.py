import os
from dataclasses import dataclass, field


def _get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/gantry.db")


def _get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "dev-secret-change-in-production")


def _get_chroma_host() -> str:
    return os.getenv("CHROMA_HOST", "http://localhost:8001")


def _get_tabby_host() -> str:
    return os.getenv("TABBY_HOST", "http://localhost:5000")


def _get_session_expire_hours() -> int:
    return int(os.getenv("SESSION_EXPIRE_HOURS", "24"))


@dataclass
class Settings:
    database_url: str = field(default_factory=_get_database_url)
    secret_key: str = field(default_factory=_get_secret_key)
    chroma_host: str = field(default_factory=_get_chroma_host)
    tabby_host: str = field(default_factory=_get_tabby_host)
    session_expire_hours: int = field(default_factory=_get_session_expire_hours)


settings = Settings()
