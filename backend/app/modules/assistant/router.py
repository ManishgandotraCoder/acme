from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.dependencies import LLMDep, SessionDep
from app.modules.assistant.service import AskResult, AskService

router = APIRouter(prefix="/api", tags=["ai"])


class AskRequest(BaseModel):
    question: Annotated[str, Field(min_length=3, max_length=500)]

    model_config = {"str_strip_whitespace": True}


@router.post("/ask")
def ask(payload: AskRequest, session: SessionDep, llm: LLMDep) -> AskResult:
    return AskService(session, llm).ask(payload.question)
