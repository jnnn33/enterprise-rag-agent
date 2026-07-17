from typing import Any

from app.domain.models import Chunk, SearchHit


class MilvusVectorIndex:
    def __init__(
        self,
        uri: str,
        collection_name: str,
        dimension: int,
        token: str = "",
        score_threshold: float = 0.05,
        client: Any | None = None,
        data_type: Any | None = None,
    ) -> None:
        if not uri.strip():
            raise ValueError("Milvus uri is required")
        if dimension < 1:
            raise ValueError("Milvus vector dimension must be positive")
        self._collection_name = collection_name
        self._dimension = dimension
        self._score_threshold = score_threshold
        if client is None:
            try:
                from pymilvus import DataType, MilvusClient
            except ImportError as exc:
                raise RuntimeError(
                    "Milvus support requires the 'milvus' optional dependency"
                ) from exc
            client_kwargs = {"uri": uri}
            if token:
                client_kwargs["token"] = token
            client = MilvusClient(**client_kwargs)
            data_type = DataType
        if data_type is None:
            raise ValueError("Milvus data_type is required with an injected client")
        self._client = client
        self._data_type = data_type
        self._ensure_collection()

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not chunks:
            return
        for vector in vectors:
            if len(vector) != self._dimension:
                raise ValueError("vector dimension does not match Milvus collection")
        rows = [
            {
                "id": chunk.id,
                "vector": vector,
                "document_id": chunk.document_id,
                "document_title": chunk.document_title,
                "source": chunk.source,
                "position": chunk.position,
                "text": chunk.text,
            }
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self._client.upsert(
            collection_name=self._collection_name,
            data=rows,
        )

    def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        if len(vector) != self._dimension:
            raise ValueError("query vector dimension does not match Milvus collection")
        result = self._client.search(
            collection_name=self._collection_name,
            data=[vector],
            anns_field="vector",
            limit=limit,
            output_fields=[
                "document_id",
                "document_title",
                "source",
                "position",
                "text",
            ],
            search_params={"metric_type": "COSINE", "params": {}},
        )
        rows = result[0] if result else []
        hits: list[SearchHit] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Milvus search result must be an object")
            entity = row.get("entity") or {}
            point_id = row.get("id", entity.get("id"))
            score = row.get("distance", row.get("score"))
            try:
                numeric_score = float(score)
            except (TypeError, ValueError) as exc:
                raise ValueError("Milvus result contains an invalid score") from exc
            if numeric_score < self._score_threshold:
                continue
            hits.append(
                SearchHit(
                    chunk=self._payload_to_chunk(point_id, entity),
                    score=round(numeric_score, 6),
                )
            )
        return hits

    def close(self) -> None:
        self._client.close()

    def _ensure_collection(self) -> None:
        if self._client.has_collection(collection_name=self._collection_name):
            return
        schema = self._client.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )
        schema.add_field(
            field_name="id",
            datatype=self._data_type.VARCHAR,
            is_primary=True,
            max_length=64,
        )
        schema.add_field(
            field_name="vector",
            datatype=self._data_type.FLOAT_VECTOR,
            dim=self._dimension,
        )
        schema.add_field(
            field_name="document_id",
            datatype=self._data_type.VARCHAR,
            max_length=64,
        )
        schema.add_field(
            field_name="document_title",
            datatype=self._data_type.VARCHAR,
            max_length=1024,
        )
        schema.add_field(
            field_name="source",
            datatype=self._data_type.VARCHAR,
            max_length=2048,
        )
        schema.add_field(
            field_name="position",
            datatype=self._data_type.INT64,
        )
        schema.add_field(
            field_name="text",
            datatype=self._data_type.VARCHAR,
            max_length=65535,
        )
        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )
        self._client.create_collection(
            collection_name=self._collection_name,
            schema=schema,
            index_params=index_params,
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
            raise ValueError(f"Milvus payload is missing fields: {sorted(missing)}")
        return Chunk(
            id=str(point_id),
            document_id=str(payload["document_id"]),
            document_title=str(payload["document_title"]),
            source=str(payload["source"]),
            position=int(payload["position"]),
            text=str(payload["text"]),
        )