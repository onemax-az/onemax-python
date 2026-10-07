from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from onemax import AsyncOneMaxClient, OneMaxClient

KEY = "omx_live_test"
BASE = "https://api.test/v1"

Reply = tuple[int, Any]


@dataclass
class Recorder:
    reply: Reply = (200, {})
    requests: list[httpx.Request] = field(default_factory=list)
    failure: Exception | None = None

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        status, body = self.reply
        if isinstance(body, str):
            return httpx.Response(status, text=body)
        return httpx.Response(status, json=body)

    @property
    def last(self) -> httpx.Request:
        return self.requests[-1]

    @property
    def sent(self) -> Any:
        return json.loads(self.last.content) if self.last.content else None


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def client(recorder: Recorder) -> OneMaxClient:
    transport = httpx.Client(transport=httpx.MockTransport(recorder.handle))
    return OneMaxClient(KEY, base_url=BASE, transport=transport)


@pytest.fixture
def async_client(recorder: Recorder) -> AsyncOneMaxClient:
    transport = httpx.AsyncClient(transport=httpx.MockTransport(recorder.handle))
    return AsyncOneMaxClient(KEY, base_url=BASE, transport=transport)


def envelope(code: str, **details: Any) -> dict[str, Any]:
    return {"error": {"code": code, "message": "Xəta", "details": details, "request_id": "req-1"}}
