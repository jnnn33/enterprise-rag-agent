from dataclasses import dataclass

from app.core.config import Settings
from app.repositories.qdrant_index import QdrantVectorIndex
from app.repositories.sqlite_agent_runs import SQLiteAgentRunRepository
from app.repositories.sqlite_knowledge import SQLiteKnowledgeRepository
from app.repositories.sqlite_workspace import SQLiteWorkspaceRepository
from app.repositories.vector_index import VectorIndex
from app.services.agent_runtime import AgentRuntime
from app.services.agent_skills import HRRecruitingSkill, KnowledgeQASkill, SkillRegistry
from app.services.agent_tools import KnowledgeAnswerTool, ToolRegistry
from app.services.conversations import ConversationService
from app.services.integrations import FeishuGateway, FeishuWebhookGateway
from app.services.evaluation import RagEvaluationService
from app.services.recruiting_tools import (
    CandidateBriefTool,
    CreateRecruitingTaskTool,
    FeishuNotifyTool,
    InterviewFeedbackTool,
)
from app.services.workspace import WorkspaceService
from app.services.answer_generation import (
    AnswerGenerator,
    ExtractiveAnswerGenerator,
    LLMAnswerGenerator,
)
from app.services.chat_model import ChatModel, OpenAICompatibleChatModel
from app.services.chunking import TextChunker
from app.services.document_parser import DocumentParser
from app.services.embeddings import (
    EmbeddingProvider,
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)
from app.services.hybrid_retrieval import HybridRetriever
from app.services.knowledge import KnowledgeService
from app.services.query_rewrite import (
    IdentityQueryRewriter,
    LLMQueryRewriter,
    QueryRewriter,
)
from app.services.rag import RagService
from app.services.reranking import HeuristicReranker, Reranker
from app.services.retrieval import KeywordRetriever


@dataclass(slots=True)
class ApplicationContainer:
    knowledge_service: KnowledgeService
    rag_service: RagService
    agent_runtime: AgentRuntime
    vector_index: VectorIndex
    conversation_service: ConversationService
    workspace_service: WorkspaceService
    evaluation_service: RagEvaluationService
    feishu_gateway: FeishuGateway


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider_name = settings.embedding_provider.strip().lower()
    if provider_name == "hash":
        return HashingEmbeddingProvider(dimension=settings.embedding_dimension)
    if provider_name == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
    raise ValueError(
        "EMBEDDING_PROVIDER must be 'hash' or 'openai_compatible'"
    )


def build_chat_model(settings: Settings) -> ChatModel | None:
    provider_name = settings.llm_provider.strip().lower()
    if provider_name == "extractive":
        return None
    if provider_name == "openai_compatible":
        return OpenAICompatibleChatModel(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    raise ValueError("LLM_PROVIDER must be 'extractive' or 'openai_compatible'")


def build_answer_generator(
    settings: Settings,
    chat_model: ChatModel | None,
) -> AnswerGenerator:
    if settings.llm_provider.strip().lower() == "extractive":
        return ExtractiveAnswerGenerator()
    if chat_model is None:
        raise ValueError("a chat model is required for LLM answer generation")
    return LLMAnswerGenerator(chat_model)


def build_query_rewriter(
    settings: Settings,
    chat_model: ChatModel | None,
) -> QueryRewriter:
    if not settings.query_rewrite_enabled:
        return IdentityQueryRewriter()
    if chat_model is None:
        raise ValueError(
            "QUERY_REWRITE_ENABLED requires LLM_PROVIDER=openai_compatible"
        )
    return LLMQueryRewriter(chat_model)


def build_reranker(settings: Settings) -> Reranker:
    provider_name = settings.reranker_provider.strip().lower()
    if provider_name == "heuristic":
        return HeuristicReranker()
    raise ValueError("RERANKER_PROVIDER must be 'heuristic'")


def build_container(settings: Settings) -> ApplicationContainer:
    repository = SQLiteKnowledgeRepository(settings.database_path)
    chunker = TextChunker(
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    embedding_provider = build_embedding_provider(settings)
    vector_index = QdrantVectorIndex(
        path=settings.qdrant_path,
        collection_name=settings.qdrant_collection,
        dimension=embedding_provider.dimension,
        score_threshold=settings.vector_score_threshold,
    )
    existing_chunks = repository.list_chunks()
    if existing_chunks:
        vector_index.upsert(
            existing_chunks,
            embedding_provider.embed_documents(
                [chunk.text for chunk in existing_chunks]
            ),
        )

    knowledge_service = KnowledgeService(
        repository=repository,
        chunker=chunker,
        parser=DocumentParser(),
        embedding_provider=embedding_provider,
        vector_index=vector_index,
    )
    chat_model = build_chat_model(settings)
    query_rewriter = build_query_rewriter(settings, chat_model)
    reranker = build_reranker(settings)
    answer_generator = build_answer_generator(settings, chat_model)
    retriever = HybridRetriever(
        keyword_retriever=KeywordRetriever(),
        embedding_provider=embedding_provider,
        vector_index=vector_index,
    )
    rag_service = RagService(
        repository=repository,
        retriever=retriever,
        query_rewriter=query_rewriter,
        reranker=reranker,
        answer_generator=answer_generator,
        default_top_k=settings.default_top_k,
    )
    workspace_repository = SQLiteWorkspaceRepository(settings.database_path)
    conversation_service = ConversationService(workspace_repository, rag_service)
    feishu_gateway = FeishuWebhookGateway(
        webhook_url=settings.feishu_webhook_url,
        dry_run=settings.feishu_dry_run,
    )
    workspace_service = WorkspaceService(workspace_repository)
    evaluation_service = RagEvaluationService(rag_service)
    agent_runtime = AgentRuntime(
        repository=SQLiteAgentRunRepository(settings.database_path),
        skills=SkillRegistry([KnowledgeQASkill(), HRRecruitingSkill()]),
        tools=ToolRegistry(
            [
                KnowledgeAnswerTool(rag_service),
                CandidateBriefTool(),
                InterviewFeedbackTool(),
                CreateRecruitingTaskTool(workspace_repository),
                FeishuNotifyTool(feishu_gateway),
            ]
        ),
    )
    return ApplicationContainer(
        knowledge_service=knowledge_service,
        rag_service=rag_service,
        agent_runtime=agent_runtime,
        vector_index=vector_index,
        conversation_service=conversation_service,
        workspace_service=workspace_service,
        feishu_gateway=feishu_gateway,
        evaluation_service=evaluation_service,
    )

