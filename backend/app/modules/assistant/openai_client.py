import openai

from app.modules.assistant.llm import LLMUnavailableError, parse_json_object


class OpenAIClient:
    """OpenAI chat completions with a strict JSON-schema response format."""

    def __init__(self, client: openai.OpenAI, model: str) -> None:
        self._client = client
        self._model = model

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "query_intent", "schema": schema, "strict": True},
                },
            )
        except openai.APIError as exc:
            raise LLMUnavailableError(f"OpenAI request failed: {exc}", provider="OpenAI") from exc

        message = response.choices[0].message
        if message.refusal or not message.content:
            return {}
        return parse_json_object(message.content)

    def close(self) -> None:
        self._client.close()
