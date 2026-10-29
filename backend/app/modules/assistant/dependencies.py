from typing import Annotated

from fastapi import Depends, Request

from app.modules.assistant.providers import ProviderRegistry


def get_providers(request: Request) -> ProviderRegistry:
    return request.app.state.llm_providers


ProvidersDep = Annotated[ProviderRegistry, Depends(get_providers)]
