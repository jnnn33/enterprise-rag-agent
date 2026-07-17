from fastapi import APIRouter

from app.api.routes import agent, chat, conversations, documents, evaluation, health, uploads, workspace


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(uploads.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
api_router.include_router(evaluation.router, prefix="/evaluations", tags=["evaluations"])

