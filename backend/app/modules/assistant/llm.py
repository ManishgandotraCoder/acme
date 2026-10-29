import json
from typing import Protocol

from app.core.errors import ServiceUnavailableError


class LLMUnavailableError(ServiceUnavailableError):
    """The language model could not be reached or returned an error."""

    def __init__(self, detail: str, provider: str = "Ollama") -> None:
        super().__init__(detail)
        self.provider = provider

    @property
    def public_message(self) -> str:  # type: ignore[override]
        hint = " Is it running?" if self.provider == "Ollama" else ""
        return f"The AI assistant ({self.provider}) is unavailable right now.{hint}"


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        """Return the model's reply parsed as JSON constrained by ``schema``.

        Returns ``{}`` when the model declines; raises ``LLMUnavailableError`` when it can't be
        reached or fails.
        """
        ...


def parse_json_object(text: str) -> dict:
    """The model's reply as a JSON object, or ``{}`` (treated as "unsupported") if it isn't one."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
