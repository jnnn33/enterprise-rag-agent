from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models

from app.domain.models import Chunk, SearchHit


class QdrantVectorIndex:
    def __init__(
        self,
        path: str,
        collection_name: str,
        dimension: int,
        score_threshold: float = 0.05,
    ) -> None:
        self._collection_name = collection_name
        self._dimension = dimension
        self._score_threshold = score_threshold
        if path == ":memory:":
            self._client = QdrantClient(":memory:")
        else:
            Path(path).mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=path)
        self._ensure_collection()

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not chunks:
            return

        points = [
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "document_id": chunk.document_id,
                    "document_title": chunk.document_title,
                    "source": chunk.source,
                    "position": chunk.position,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )

    def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        result = self._client.query_points(
            collection_name=self._collection_name,
            query=vector,
            limit=limit,
            with_payload=True,
            score_threshold=self._score_threshold,
        )
        hits: list[SearchHit] = []
        for point in result.points:
            payload = point.payload or {}
            chunk = self._payload_to_chunk(point.id, payload)
            hits.append(SearchHit(chunk=chunk, score=round(point.score, 6)))
        return hits

    def close(self) -> None:
        self._client.close()

    def _ensure_collection(self) -> None:
        if self._client.collection_exists(self._collection_name):
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=models.VectorParams(
                size=self._dimension,
                distance=models.Distance.COSINE,
            ),
        )

    @staticmethod
    def _payload_to_chunk(point_id: Any, payload: dict[str, Any]) -> Chunk:
        required = {
            "document_id",
            "document_title",
            "source",
            "position",
            "text",
        }
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Qdrant payload is missing fields: {sorted(missing)}")
        return Chunk(
            id=str(point_id),
            document_id=str(payload["document_id"]),
            document_title=str(payload["document_title"]),
            source=str(payload["source"]),
            position=int(payload["position"]),
            text=str(payload["text"]),
        )
