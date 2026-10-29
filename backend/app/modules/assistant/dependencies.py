from typing import Annotated

from fastapi import Depends, Request

from app.modules.assistant.llm import LLMClient


def get_llm(request: Request) -> LLMClient:
    return request.app.state.llm


LLMDep = Annotated[LLMClient, Depends(get_llm)]
