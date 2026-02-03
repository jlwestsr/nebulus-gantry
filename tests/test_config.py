import os
from backend.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.database_url == "sqlite:///./data/gantry.db"
    assert settings.secret_key is not None


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    settings = Settings()
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.secret_key == "test-secret"
