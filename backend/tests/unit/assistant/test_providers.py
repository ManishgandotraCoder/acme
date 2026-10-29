import pytest

from app.core.config import Settings
from app.modules.assistant.providers import (
    Provider,
    ProviderRegistry,
    UnknownProviderError,
    build_registry,
)


class Echo:
    def complete_json(self, system, user, schema):
        return {}


def _registry() -> ProviderRegistry:
    return ProviderRegistry(
        [
            Provider("ollama", "Ollama", "llama3.2", Echo()),
            Provider("openai", "OpenAI", "gpt", Echo()),
        ],
        default="ollama",
    )


def test_no_choice_means_the_default_provider():
    assert _registry().get(None).id == "ollama"


def test_a_configured_provider_can_be_chosen():
    assert _registry().get("openai").id == "openai"


def test_choosing_a_provider_that_is_not_configured_is_rejected_with_the_options():
    with pytest.raises(UnknownProviderError) as error:
        _registry().get("anthropic")
    assert "ollama, openai" in str(error.value)


def test_describe_lists_providers_with_the_default_marked():
    assert [(p.id, p.default) for p in _registry().describe()] == [
        ("ollama", True),
        ("openai", False),
    ]


def test_cloud_providers_are_offered_only_when_their_api_key_is_set():
    # Explicit None: Settings also reads ANTHROPIC_API_KEY / OPENAI_API_KEY from the shell.
    no_keys = Settings(anthropic_api_key=None, openai_api_key=None)
    assert [p.id for p in build_registry(no_keys).describe()] == ["ollama"]

    settings = Settings(
        anthropic_api_key="sk-ant-test", openai_api_key="sk-test", llm_provider="ollama"
    )
    registry = build_registry(settings)

    assert [p.id for p in registry.describe()] == ["ollama", "anthropic", "openai"]
    assert registry.get(None).id == "ollama"


def test_the_default_provider_is_configurable_but_must_be_available():
    assert (
        build_registry(Settings(anthropic_api_key="k", llm_provider="anthropic")).get(None).id
        == "anthropic"
    )
    with pytest.raises(ValueError):
        build_registry(Settings(llm_provider="anthropic", anthropic_api_key=None))
