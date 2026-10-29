import anthropic

from app.modules.assistant.llm import LLMUnavailableError, parse_json_object

# A declined request is re-run server-side on Anthropic's recommended fallback model.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicClient:
    """Claude via the Messages API with structured outputs (JSON constrained by a schema)."""

    def __init__(self, client: anthropic.Anthropic, model: str) -> None:
        self._client = client
        self._model = model

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        try:
            response = self._client.beta.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user}],
                # Choosing one operation is a small classification: low effort is enough.
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": schema},
                },
                betas=[_FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.APIError as exc:
            raise LLMUnavailableError(f"Claude request failed: {exc}", provider="Claude") from exc

        if response.stop_reason == "refusal":
            return {}
        text = next((block.text for block in response.content if block.type == "text"), "")
        return parse_json_object(text)

    def close(self) -> None:
        self._client.close()
