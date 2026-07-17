import os
from dataclasses import dataclass
from functools import lru_cache


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Enterprise RAG Agent"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    chunk_size: int = 500
    chunk_overlap: int = 80
    default_top_k: int = 3
    database_path: str = "data/app.db"
    qdrant_path: str = "data/qdrant"
    qdrant_collection: str = "knowledge_chunks"
    embedding_provider: str = "hash"
    embedding_dimension: int = 384
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = ""
    vector_score_threshold: float = 0.05
    llm_provider: str = "extractive"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    query_rewrite_enabled: bool = False
    reranker_provider: str = "heuristic"
    cors_origins: str = "http://127.0.0.1:3000,http://localhost:3000"
    feishu_webhook_url: str = ""
    feishu_dry_run: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            app_name=os.getenv("APP_NAME", defaults.app_name),
            app_env=os.getenv("APP_ENV", defaults.app_env),
            api_prefix=os.getenv("API_PREFIX", defaults.api_prefix),
            chunk_size=int(os.getenv("CHUNK_SIZE", str(defaults.chunk_size))),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", str(defaults.chunk_overlap))),
            default_top_k=int(os.getenv("DEFAULT_TOP_K", str(defaults.default_top_k))),
            database_path=os.getenv("DATABASE_PATH", defaults.database_path),
            qdrant_path=os.getenv("QDRANT_PATH", defaults.qdrant_path),
            qdrant_collection=os.getenv(
                "QDRANT_COLLECTION", defaults.qdrant_collection
            ),
            embedding_provider=os.getenv(
                "EMBEDDING_PROVIDER", defaults.embedding_provider
            ),
            embedding_dimension=int(
                os.getenv("EMBEDDING_DIMENSION", str(defaults.embedding_dimension))
            ),
            embedding_base_url=os.getenv(
                "EMBEDDING_BASE_URL", defaults.embedding_base_url
            ),
            embedding_api_key=os.getenv(
                "EMBEDDING_API_KEY", defaults.embedding_api_key
            ),
            embedding_model=os.getenv("EMBEDDING_MODEL", defaults.embedding_model),
            vector_score_threshold=float(
                os.getenv("VECTOR_SCORE_THRESHOLD", str(defaults.vector_score_threshold))
            ),
            llm_provider=os.getenv("LLM_PROVIDER", defaults.llm_provider),
            llm_base_url=os.getenv("LLM_BASE_URL", defaults.llm_base_url),
            llm_api_key=os.getenv("LLM_API_KEY", defaults.llm_api_key),
            llm_model=os.getenv("LLM_MODEL", defaults.llm_model),
            query_rewrite_enabled=_read_bool(
                "QUERY_REWRITE_ENABLED", defaults.query_rewrite_enabled
            ),
            reranker_provider=os.getenv(
                "RERANKER_PROVIDER", defaults.reranker_provider
            ),
            cors_origins=os.getenv("CORS_ORIGINS", defaults.cors_origins),
            feishu_webhook_url=os.getenv(
                "FEISHU_WEBHOOK_URL", defaults.feishu_webhook_url
            ),
            feishu_dry_run=_read_bool(
                "FEISHU_DRY_RUN", defaults.feishu_dry_run
            ),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()

