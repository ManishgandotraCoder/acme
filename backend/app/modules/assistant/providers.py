"""Which language models can classify questions, and which one a request uses.

Ollama (local, private) is always available and the default. Claude and OpenAI are offered only
when their API key is configured; a question may name one of the configured providers. Whatever
the provider, it only selects an analytics operation: answers are computed the same way.
"""

from dataclasses import dataclass

import anthropic
import httpx
import openai

from app.core.config import Settings
from app.core.errors import BusinessRuleError
from app.modules.assistant.anthropic_client import AnthropicClient
from app.modules.assistant.llm import LLMClient
from app.modules.assistant.ollama import OllamaClient
from app.modules.assistant.openai_client import OpenAIClient
from app.modules.assistant.schemas import ProviderInfo


class UnknownProviderError(BusinessRuleError):
    def __init__(self, requested: str, available: list[str]) -> None:
        super().__init__(
            f"Model provider {requested!r} is not configured. Available: {', '.join(available)}"
        )


@dataclass(frozen=True, slots=True)
class Provider:
    id: str
    label: str
    model: str
    client: LLMClient


class ProviderRegistry:
    def __init__(self, providers: list[Provider], default: str) -> None:
        self._providers = {p.id: p for p in providers}
        if default not in self._providers:
            raise ValueError(
                f"Default model provider {default!r} is not configured "
                f"(configured: {', '.join(self._providers)})"
            )
        self._default = default

    def get(self, provider_id: str | None) -> Provider:
        provider = self._providers.get(provider_id or self._default)
        if provider is None:
            raise UnknownProviderError(provider_id or "", list(self._providers))
        return provider

    def describe(self) -> list[ProviderInfo]:
        return [
            ProviderInfo(id=p.id, label=p.label, model=p.model, default=p.id == self._default)
            for p in self._providers.values()
        ]

    def close(self) -> None:
        for provider in self._providers.values():
            if close := getattr(provider.client, "close", None):
                close()


def build_registry(settings: Settings) -> ProviderRegistry:
    timeout = settings.llm_timeout_seconds
    providers = [
        Provider(
            "ollama",
            "Ollama (local)",
            settings.ollama_model,
            OllamaClient(
                httpx.Client(base_url=settings.ollama_url, timeout=timeout),
                model=settings.ollama_model,
            ),
        )
    ]
    if settings.anthropic_api_key:
        sdk = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=timeout)
        providers.append(
            Provider(
                "anthropic",
                "Claude",
                settings.anthropic_model,
                AnthropicClient(sdk, model=settings.anthropic_model),
            )
        )
    if settings.openai_api_key:
        sdk = openai.OpenAI(api_key=settings.openai_api_key, timeout=timeout)
        providers.append(
            Provider(
                "openai",
                "OpenAI",
                settings.openai_model,
                OpenAIClient(sdk, model=settings.openai_model),
            )
        )
    return ProviderRegistry(providers, default=settings.llm_provider)
