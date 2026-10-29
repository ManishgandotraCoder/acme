import json

import httpx

from app.modules.assistant.llm import LLMUnavailableError


class OllamaClient:
    """Minimal adapter over Ollama's /api/chat using structured outputs."""

    def __init__(self, http: httpx.Client, model: str) -> None:
        self._http = http
        self._model = model

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        payload = {
            "model": self._model,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = self._http.post("/api/chat", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Ollama request failed: {exc}") from exc

        content = response.json().get("message", {}).get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
