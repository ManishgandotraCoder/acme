from fastapi import APIRouter

from app.api.deps import SessionDep
from app.schemas import CountryStats, DepartmentStats, JobTitleStats, OrgSummary
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/summary")
def summary(session: SessionDep) -> OrgSummary:
    return InsightsService(session).summary()


@router.get("/countries")
def countries(session: SessionDep) -> list[CountryStats]:
    return InsightsService(session).country_stats()


@router.get("/job-titles")
def job_titles(country: str, session: SessionDep) -> list[JobTitleStats]:
    return InsightsService(session).job_title_stats(country)


@router.get("/departments")
def departments(session: SessionDep, country: str | None = None) -> list[DepartmentStats]:
    return InsightsService(session).department_stats(country=country)
