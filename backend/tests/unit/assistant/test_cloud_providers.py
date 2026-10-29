"""Claude and OpenAI adapters, over mocked HTTP: no network, no API keys."""

import json

import anthropic
import httpx
import httpx2  # the Anthropic SDK's HTTP client (a fork of httpx with the same API)
import openai
import pytest

from app.modules.assistant.anthropic_client import AnthropicClient
from app.modules.assistant.llm import LLMUnavailableError
from app.modules.assistant.openai_client import OpenAIClient

SCHEMA = {"type": "object", "properties": {"metric": {"type": "string"}}}
INTENT = {"metric": "org_summary"}


def _http(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # the OpenAI SDK's client


# --- Claude ----------------------------------------------------------------------------------


def _claude(handler) -> AnthropicClient:
    http = httpx2.Client(transport=httpx2.MockTransport(handler))
    sdk = anthropic.Anthropic(api_key="test-key", http_client=http, max_retries=0)
    return AnthropicClient(sdk, model="claude-opus-5-5")


def _claude_reply(text: str, stop_reason: str = "end_turn") -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": text}],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )


def test_claude_returns_structured_json_constrained_by_the_schema():
    sent = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent["body"] = json.loads(request.content)
        sent["beta"] = request.headers.get("anthropic-beta", "")
        return _claude_reply(json.dumps(INTENT))

    assert _claude(handler).complete_json("system prompt", "question", SCHEMA) == INTENT

    body = sent["body"]
    assert body["model"] == "claude-opus-5-5"
    assert body["system"] == "system prompt"
    assert body["messages"] == [{"role": "user", "content": "question"}]
    assert body["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    assert body["output_config"]["effort"] == "low"  # a classification, not deep reasoning
    # A declined request is re-run on Anthropic's recommended fallback model server-side.
    assert body["fallbacks"] == "default" and "server-side-fallback" in sent["beta"]


def test_claude_refusal_is_treated_as_an_unsupported_question():
    assert (
        _claude(lambda r: _claude_reply("", stop_reason="refusal")).complete_json("s", "q", SCHEMA)
        == {}
    )


@pytest.mark.parametrize(
    "handler",
    [
        lambda r: httpx2.Response(500, json={"type": "error", "error": {"type": "api_error"}}),
        lambda r: httpx2.Response(
            401, json={"type": "error", "error": {"type": "authentication_error"}}
        ),
        lambda r: (_ for _ in ()).throw(httpx2.ConnectError("refused")),
    ],
)
def test_claude_failures_make_the_assistant_unavailable(handler):
    with pytest.raises(LLMUnavailableError) as error:
        _claude(handler).complete_json("s", "q", SCHEMA)
    assert "Claude" in error.value.public_message


# --- OpenAI ----------------------------------------------------------------------------------


def _openai(handler) -> OpenAIClient:
    sdk = openai.OpenAI(api_key="test-key", http_client=_http(handler), max_retries=0)
    return OpenAIClient(sdk, model="gpt-test")


def _openai_reply(content: str | None, refusal: str | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-test",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content, "refusal": refusal},
                    "finish_reason": "stop",
                }
            ],
        },
    )


def test_openai_returns_structured_json_with_a_strict_schema():
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return _openai_reply(json.dumps(INTENT))

    assert _openai(handler).complete_json("system prompt", "question", SCHEMA) == INTENT

    assert sent["model"] == "gpt-test"
    assert [m["role"] for m in sent["messages"]] == ["system", "user"]
    response_format = sent["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["schema"] == SCHEMA
    assert response_format["json_schema"]["strict"] is True


def test_openai_refusal_is_treated_as_an_unsupported_question():
    handler = lambda r: _openai_reply(None, refusal="I can't help with that")  # noqa: E731
    assert _openai(handler).complete_json("s", "q", SCHEMA) == {}


def test_openai_failures_make_the_assistant_unavailable():
    with pytest.raises(LLMUnavailableError) as error:
        _openai(lambda r: httpx.Response(503, json={"error": {}})).complete_json("s", "q", SCHEMA)
    assert "OpenAI" in error.value.public_message
