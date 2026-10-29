from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import SessionDep

router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/ready")
def ready(session: SessionDep) -> dict[str, str]:
    """Readiness: dependencies needed to serve traffic are reachable."""
    session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
