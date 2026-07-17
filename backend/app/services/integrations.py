from collections.abc import Callable
from typing import Any, Protocol

import httpx2


class FeishuGateway(Protocol):
    def status(self) -> dict[str, Any]: ...

    def send_text(self, text: str) -> dict[str, Any]: ...


class FeishuWebhookGateway:
    def __init__(
        self,
        webhook_url: str = "",
        dry_run: bool = True,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self._webhook_url = webhook_url.strip()
        self._dry_run = dry_run
        self._post = post or httpx2.post

    def status(self) -> dict[str, Any]:
        return {
            "provider": "feishu_webhook",
            "configured": bool(self._webhook_url),
            "mode": "simulated" if self._dry_run else "live",
        }

    def send_text(self, text: str) -> dict[str, Any]:
        if self._dry_run:
            return {
                "provider": "feishu_webhook",
                "delivery": "simulated",
                "text": text,
            }
        if not self._webhook_url:
            raise RuntimeError("FEISHU_WEBHOOK_URL is required in live mode")
        response = self._post(
            self._webhook_url,
            json={"msg_type": "text", "content": {"text": text}},
            timeout=15.0,
        )
        response.raise_for_status()
        return {
            "provider": "feishu_webhook",
            "delivery": "sent",
            "response": response.json(),
        }
