"""
Pytest configuration and shared fixtures for backend tests.
"""
import os

# Ensure module-level code in dependencies.py uses an in-memory database
# instead of creating a file-based SQLite database.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
