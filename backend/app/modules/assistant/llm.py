from typing import Protocol


class LLMUnavailableError(RuntimeError):
    """The language model could not be reached or returned an error."""


class LLMClient(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        """Return the model's reply parsed as JSON constrained by ``schema``."""
        ...
