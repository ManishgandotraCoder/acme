from fastapi import APIRouter

from app.core.dependencies import SessionDep
from app.modules.assistant.dependencies import LLMDep
from app.modules.assistant.schemas import AskRequest, AskResult
from app.modules.assistant.service import AskService

router = APIRouter(prefix="/api", tags=["assistant"])


@router.post("/ask")
def ask(payload: AskRequest, session: SessionDep, llm: LLMDep) -> AskResult:
    return AskService(session, llm).ask(payload.question)
