# conftest.py
import os
import pytest
from fastapi.testclient import TestClient

# Ensure the API sees the same secret it uses at runtime
os.environ["JWT_SECRET"] = "supersecretkey"  # matches default in api.py

from api import app

@pytest.fixture(scope="session")
def client():
    """Return a TestClient for the FastAPI app."""
    with TestClient(app) as c:
        yield c
