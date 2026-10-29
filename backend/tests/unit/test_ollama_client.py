import json

import httpx
import pytest

from app.ai.llm import LLMUnavailableError
from app.ai.ollama_client import OllamaClient


def _client(handler) -> OllamaClient:
    http = httpx.Client(transport=httpx.MockTransport(handler), base_url="http://ollama")
    return OllamaClient(http, model="llama3.2")


def test_sends_structured_output_request_and_parses_json_content():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": '{"metric": "org_summary"}'}})

    result = _client(handler).complete_json("sys", "question", {"type": "object"})

    assert result == {"metric": "org_summary"}
    assert captured["model"] == "llama3.2"
    assert captured["format"] == {"type": "object"}
    assert captured["stream"] is False
    assert captured["options"]["temperature"] == 0
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]


def test_connection_failure_raises_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMUnavailableError):
        _client(handler).complete_json("s", "u", {})


def test_server_error_raises_unavailable():
    with pytest.raises(LLMUnavailableError):
        _client(lambda r: httpx.Response(500, text="boom")).complete_json("s", "u", {})


def test_non_json_content_returns_empty_dict():
    handler = lambda r: httpx.Response(200, json={"message": {"content": "not json"}})  # noqa: E731
    assert _client(handler).complete_json("s", "u", {}) == {}
