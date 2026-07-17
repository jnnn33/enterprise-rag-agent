from typing import Any, Protocol

from app.services.rag import RagService


class AgentTool(Protocol):
    name: str
    description: str

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]: ...


class UnknownToolError(LookupError):
    pass


class ToolRegistry:
    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(f"unknown tool: {name}") from exc

    def list_tools(self) -> list[AgentTool]:
        return list(self._tools.values())


class KnowledgeAnswerTool:
    name = "knowledge_answer"
    description = "Answer a question from the indexed enterprise knowledge base."

    def __init__(self, rag_service: RagService) -> None:
        self._rag_service = rag_service

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        question = arguments.get("question")
        top_k = arguments.get("top_k")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("knowledge_answer requires a non-empty question")
        if top_k is not None and (not isinstance(top_k, int) or not 1 <= top_k <= 10):
            raise ValueError("knowledge_answer top_k must be between 1 and 10")
        response = self._rag_service.answer(question=question, top_k=top_k)
        return response.model_dump(mode="json")
