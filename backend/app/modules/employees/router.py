from typing import Annotated, Literal

from fastapi import APIRouter, Query, status

from app.core.dependencies import SessionDep
from app.core.pagination import Page
from app.modules.employees.repository import EmployeeFilter, EmployeeRepository, SortField
from app.modules.employees.schemas import (
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    Meta,
    SalaryChangeOut,
)
from app.modules.employees.service import EmployeeService
from app.shared.countries import SUPPORTED_COUNTRIES

router = APIRouter(prefix="/api", tags=["employees"])


@router.get("/meta")
def meta(session: SessionDep) -> Meta:
    repo = EmployeeRepository(session)
    return Meta(
        countries=[{"name": c.name, "currency": c.currency} for c in SUPPORTED_COUNTRIES],
        departments=repo.distinct_departments(),
        job_titles=repo.distinct_job_titles(),
    )


@router.get("/employees")
def list_employees(
    session: SessionDep,
    search: str | None = None,
    country: str | None = None,
    department: str | None = None,
    job_title: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: SortField = SortField.FULL_NAME,
    order: Literal["asc", "desc"] = "asc",
) -> Page[EmployeeOut]:
    filters = EmployeeFilter(
        search=search, country=country, department=department, job_title=job_title
    )
    items, total = EmployeeService(session).search(
        filters, page=page, page_size=page_size, sort=sort, descending=order == "desc"
    )
    return Page[EmployeeOut](
        items=[EmployeeOut.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/employees", status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, session: SessionDep) -> EmployeeOut:
    return EmployeeOut.model_validate(EmployeeService(session).create(payload))


@router.get("/employees/{employee_id}")
def get_employee(employee_id: int, session: SessionDep) -> EmployeeOut:
    return EmployeeOut.model_validate(EmployeeService(session).get(employee_id))


@router.patch("/employees/{employee_id}")
def update_employee(employee_id: int, payload: EmployeeUpdate, session: SessionDep) -> EmployeeOut:
    return EmployeeOut.model_validate(EmployeeService(session).update(employee_id, payload))


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(employee_id: int, session: SessionDep) -> None:
    EmployeeService(session).delete(employee_id)


@router.get("/employees/{employee_id}/salary-history")
def salary_history(employee_id: int, session: SessionDep) -> list[SalaryChangeOut]:
    changes = EmployeeService(session).salary_history(employee_id)
    return [SalaryChangeOut.model_validate(c) for c in changes]
