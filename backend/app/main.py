from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.container import ApplicationContainer, build_container


def create_app(
    settings: Settings | None = None,
    container: ApplicationContainer | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_container = container or build_container(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            resolved_container.vector_index.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="1.0.0",
        description="Enterprise RAG, Agent Runtime and recruiting workflow API.",
        lifespan=lifespan,
    )
    app.state.container = resolved_container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in resolved_settings.cors_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=resolved_settings.api_prefix)

    @app.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {
            "name": resolved_settings.app_name,
            "environment": resolved_settings.app_env,
            "docs": "/docs",
            "ui": "http://127.0.0.1:3000",
        }

    return app


app = create_app()

