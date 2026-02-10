import os
from dataclasses import dataclass, field


def _get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./data/gantry.db")


def _get_secret_key() -> str:
    return os.getenv("SECRET_KEY", "dev-secret-change-in-production")


def _get_session_expire_hours() -> int:
    return int(os.getenv("SESSION_EXPIRE_HOURS", "24"))


def _get_overlord_routing_enabled() -> bool:
    return os.getenv("OVERLORD_ROUTING_ENABLED", "true").lower() in ("true", "1", "yes")


@dataclass
class Settings:
    database_url: str = field(default_factory=_get_database_url)
    secret_key: str = field(default_factory=_get_secret_key)
    session_expire_hours: int = field(default_factory=_get_session_expire_hours)
    overlord_routing_enabled: bool = field(default_factory=_get_overlord_routing_enabled)


settings = Settings()
