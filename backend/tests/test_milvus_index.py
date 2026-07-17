from typing import Any

import pytest

from app.domain.models import Chunk
from app.repositories.milvus_index import MilvusVectorIndex


class FakeDataType:
    VARCHAR = "VARCHAR"
    FLOAT_VECTOR = "FLOAT_VECTOR"
    INT64 = "INT64"


class FakeSchema:
    def __init__(self) -> None:
        self.fields: list[dict[str, Any]] = []

    def add_field(self, **kwargs: Any) -> None:
        self.fields.append(kwargs)


class FakeIndexParams:
    def __init__(self) -> None:
        self.indexes: list[dict[str, Any]] = []

    def add_index(self, **kwargs: Any) -> None:
        self.indexes.append(kwargs)


class FakeMilvusClient:
    def __init__(self, existing: bool = False) -> None:
        self.existing = existing
        self.schema = FakeSchema()
        self.index_params = FakeIndexParams()
        self.created: dict[str, Any] | None = None
        self.upserted: dict[str, Any] | None = None
        self.search_kwargs: dict[str, Any] | None = None
        self.search_result: list[list[dict[str, Any]]] = []
        self.closed = False

    def has_collection(self, **kwargs: Any) -> bool:
        return self.existing

    def create_schema(self, **kwargs: Any) -> FakeSchema:
        return self.schema

    def prepare_index_params(self) -> FakeIndexParams:
        return self.index_params

    def create_collection(self, **kwargs: Any) -> None:
        self.created = kwargs

    def upsert(self, **kwargs: Any) -> None:
        self.upserted = kwargs

    def search(self, **kwargs: Any) -> list[list[dict[str, Any]]]:
        self.search_kwargs = kwargs
        return self.search_result

    def close(self) -> None:
        self.closed = True


def _chunk() -> Chunk:
    return Chunk(
        id="chunk-1",
        document_id="document-1",
        document_title="Travel policy",
        source="handbook",
        position=2,
        text="Second-class rail tickets can be reimbursed.",
    )


def test_milvus_index_creates_schema_and_round_trips_payload() -> None:
    client = FakeMilvusClient()
    index = MilvusVectorIndex(
        uri="local.db",
        collection_name="knowledge",
        dimension=3,
        score_threshold=0.5,
        client=client,
        data_type=FakeDataType,
    )
    chunk = _chunk()
    index.upsert([chunk], [[1.0, 0.0, 0.0]])
    client.search_result = [
        [
            {
                "id": chunk.id,
                "distance": 0.93,
                "entity": {
                    "document_id": chunk.document_id,
                    "document_title": chunk.document_title,
                    "source": chunk.source,
                    "position": chunk.position,
                    "text": chunk.text,
                },
            },
            {
                "id": "low-score",
                "distance": 0.1,
                "entity": {
                    "document_id": "document-2",
                    "document_title": "Other",
                    "source": "test",
                    "position": 0,
                    "text": "Other content",
                },
            },
        ]
    ]

    hits = index.search([1.0, 0.0, 0.0], limit=3)
    index.close()

    assert client.created is not None
    assert [field["field_name"] for field in client.schema.fields] == [
        "id",
        "vector",
        "document_id",
        "document_title",
        "source",
        "position",
        "text",
    ]
    assert client.index_params.indexes[0]["metric_type"] == "COSINE"
    assert client.upserted is not None
    assert client.upserted["data"][0]["text"] == chunk.text
    assert hits[0].chunk == chunk
    assert hits[0].score == pytest.approx(0.93)
    assert len(hits) == 1
    assert client.closed is True


def test_milvus_index_reuses_existing_collection() -> None:
    client = FakeMilvusClient(existing=True)

    MilvusVectorIndex(
        uri="https://milvus.example",
        collection_name="knowledge",
        dimension=3,
        token="secret",
        client=client,
        data_type=FakeDataType,
    )

    assert client.created is None


def test_milvus_index_validates_vector_dimension() -> None:
    index = MilvusVectorIndex(
        uri="local.db",
        collection_name="knowledge",
        dimension=3,
        client=FakeMilvusClient(existing=True),
        data_type=FakeDataType,
    )

    with pytest.raises(ValueError, match="dimension"):
        index.upsert([_chunk()], [[1.0, 0.0]])