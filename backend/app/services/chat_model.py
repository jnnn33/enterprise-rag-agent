from collections.abc import Callable
from typing import Any, Protocol

import httpx2


class ChatModel(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str: ...


class ChatModelError(RuntimeError):
    pass


class OpenAICompatibleChatModel:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 60.0,
        post: Callable[..., Any] | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("LLM base_url is required")
        if not model.strip():
            raise ValueError("LLM model is required")
        self._endpoint = f"{base_url.rstrip('/')}/chat/completions"
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._post = post or httpx2.post

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = self._post(
            self._endpoint,
            headers=headers,
            json={
                "model": self._model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ChatModelError(
                "chat completion response has an invalid structure"
            ) from exc
        if not isinstance(content, str) or not content.strip():
            raise ChatModelError("chat completion response is empty")
        return content.strip()
