from fastapi import APIRouter

from app.core.actor import ActorDep
from app.core.dependencies import SessionDep
from app.modules.assistant.dependencies import LLMDep
from app.modules.assistant.schemas import AskRequest, AskResult
from app.modules.assistant.service import AskService

router = APIRouter(prefix="/api", tags=["assistant"])


@router.post("/ask")
def ask(payload: AskRequest, session: SessionDep, llm: LLMDep, actor: ActorDep) -> AskResult:
    return AskService(session, llm, actor=actor).ask(payload.question)
