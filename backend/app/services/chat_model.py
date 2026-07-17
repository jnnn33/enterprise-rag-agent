from collections.abc import Callable, Iterator
import json
from typing import Any, Protocol

import httpx2


class ChatModel(Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str: ...

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> Iterator[str]: ...


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
        stream_request: Callable[..., Any] | None = None,
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
        self._stream_request = stream_request or httpx2.stream

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        response = self._post(
            self._endpoint,
            headers=self._headers(),
            json=self._payload(messages, temperature, stream=False),
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

    def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> Iterator[str]:
        with self._stream_request(
            "POST",
            self._endpoint,
            headers=self._headers(),
            json=self._payload(messages, temperature, stream=True),
            timeout=self._timeout_seconds,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not isinstance(line, str) or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                    content = event["choices"][0]["delta"].get("content")
                except (IndexError, KeyError, TypeError, ValueError) as exc:
                    raise ChatModelError(
                        "streaming chat response has an invalid structure"
                    ) from exc
                if isinstance(content, str) and content:
                    yield content

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _payload(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        stream: bool,
    ) -> dict[str, Any]:
        return {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }