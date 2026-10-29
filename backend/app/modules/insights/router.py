from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.core.actor import VIEW_INDIVIDUAL_PAY, ActorDep
from app.core.dependencies import SessionDep
from app.modules.insights.schemas import (
    AboveAverageReport,
    CountryStats,
    DepartmentStats,
    JobTitleStats,
    LevelStats,
    OrgSummary,
    PayOutlier,
    SalaryBand,
    SalaryTrend,
)
from app.modules.insights.service import InsightsService

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


@router.get("/levels")
def levels(
    session: SessionDep,
    job_title: str | None = None,
    department: str | None = None,
    country: str | None = None,
) -> list[LevelStats]:
    return InsightsService(session).level_stats(
        job_title=job_title, department=department, country=country
    )


@router.get("/salary-bands")
def salary_bands(
    session: SessionDep, department: str | None = None, country: str | None = None
) -> list[SalaryBand]:
    return InsightsService(session).salary_bands(department=department, country=country)


@router.get("/salary-trends")
def salary_trends(
    session: SessionDep,
    as_of: date | None = None,
    months: Annotated[int, Query(ge=1, le=36)] = 12,
    department: str | None = None,
    country: str | None = None,
) -> SalaryTrend:
    return InsightsService(session).salary_trends(
        as_of=as_of, months=months, department=department, country=country
    )


@router.get("/outliers")
def outliers(
    session: SessionDep,
    actor: ActorDep,
    threshold_pct: Annotated[float, Query(gt=0, le=500)] = 25,
    department: str | None = None,
    country: str | None = None,
) -> list[PayOutlier]:
    actor.require(VIEW_INDIVIDUAL_PAY)
    return InsightsService(session).outliers(
        threshold_pct=threshold_pct, department=department, country=country
    )


@router.get("/above-department-average")
def above_department_average(session: SessionDep, actor: ActorDep) -> AboveAverageReport:
    actor.require(VIEW_INDIVIDUAL_PAY)
    return InsightsService(session).above_department_average()
