from typing import Protocol

from app.core.errors import ServiceUnavailableError


class LLMUnavailableError(ServiceUnavailableError):
    """The language model could not be reached or returned an error."""

    public_message = "The AI assistant is unavailable right now. Is Ollama running?"


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        """Return the model's reply parsed as JSON constrained by ``schema``."""
        ...
