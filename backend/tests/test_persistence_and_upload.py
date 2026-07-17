from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_markdown_upload_is_searchable(client: TestClient) -> None:
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "employee-handbook.md",
                b"# Vacation policy\n\nEmployees receive 10 paid leave days.",
                "text/markdown",
            )
        },
    )

    assert upload_response.status_code == 201
    assert upload_response.json()["source"] == "upload:employee-handbook.md"

    chat_response = client.post(
        "/api/v1/chat",
        json={"question": "How many paid leave days do employees receive?"},
    )

    assert chat_response.status_code == 200
    assert "10 paid leave days" in chat_response.json()["answer"]


def test_unsupported_upload_type_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("policy.exe", b"not a document", "application/octet-stream")},
    )

    assert response.status_code == 415


def test_documents_survive_application_restart(tmp_path) -> None:
    settings = Settings(
        chunk_size=80,
        chunk_overlap=10,
        database_path=str(tmp_path / "persistent.db"),
        qdrant_path=":memory:",
        qdrant_collection="restart_chunks",
    )
    first_app = create_app(settings=settings)
    with TestClient(first_app) as first_client:
        response = first_client.post(
            "/api/v1/documents",
            json={
                "title": "Production policy",
                "source": "security-v1",
                "content": "Production changes require two-person approval.",
            },
        )
        assert response.status_code == 201

    restarted_app = create_app(settings=settings)
    with TestClient(restarted_app) as restarted_client:
        response = restarted_client.post(
            "/api/v1/chat",
            json={"question": "What approval is required for production changes?"},
        )

    assert response.status_code == 200
    assert "two-person approval" in response.json()["answer"]
