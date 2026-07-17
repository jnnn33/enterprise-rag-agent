import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    app = create_app(
        settings=Settings(
            chunk_size=80,
            chunk_overlap=10,
            default_top_k=3,
            database_path=str(tmp_path / "test.db"),
            qdrant_path=":memory:",
            qdrant_collection="test_chunks",
        )
    )
    with TestClient(app) as test_client:
        yield test_client

