from fastapi import APIRouter

from app.core.actor import ActorDep
from app.core.dependencies import SessionDep
from app.modules.assistant.dependencies import ProvidersDep
from app.modules.assistant.schemas import AskRequest, AskResult, ProviderInfo
from app.modules.assistant.service import AskService

router = APIRouter(prefix="/api", tags=["assistant"])


@router.get("/assistant/providers")
def providers(registry: ProvidersDep) -> list[ProviderInfo]:
    return registry.describe()


@router.post("/ask")
def ask(
    payload: AskRequest, session: SessionDep, registry: ProvidersDep, actor: ActorDep
) -> AskResult:
    provider = registry.get(payload.provider)
    service = AskService(session, provider.client, actor=actor, provider=provider.id)
    return service.ask(payload.question)
