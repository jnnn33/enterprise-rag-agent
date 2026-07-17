from collections.abc import Iterable, Iterator
import json
from typing import Any


def encode_sse(event: str, data: dict[str, Any]) -> str:
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


def stream_sse(events: Iterable[dict[str, Any]]) -> Iterator[str]:
    try:
        for item in events:
            yield encode_sse(item["event"], item["data"])
    except Exception as exc:
        yield encode_sse("error", {"message": str(exc)})