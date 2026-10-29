from datetime import date

import pytest

from app.core.actor import Actor
from app.modules.employees.errors import (
    CurrencyChangeRequiresSalaryError,
    DuplicateEmailError,
    EmployeeNotFoundError,
    SalaryEffectiveBeforeHireError,
)
from app.modules.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.modules.employees.service import EmployeeService


def _payload(**overrides) -> EmployeeCreate:
    data = dict(
        full_name="Ada Lovelace",
        email="Ada@example.com",
        job_title="Software Engineer",
        job_level="Mid",
        department="Engineering",
        country="India",
        annual_salary=2_400_000,
        hire_date=date(2021, 3, 1),
    )
    data.update(overrides)
    return EmployeeCreate(**data)


HR = Actor(name="Priya Shah (HR)", permissions=frozenset())


@pytest.fixture
def service(session):
    return EmployeeService(session, actor=HR)


def test_create_normalises_email_and_derives_currency_from_country(service):
    employee = service.create(_payload())

    assert employee.id is not None
    assert employee.email == "ada@example.com"
    assert employee.currency == "INR"


def test_create_rejects_duplicate_email_regardless_of_case(service):
    service.create(_payload())
    with pytest.raises(DuplicateEmailError):
        service.create(_payload(email="ADA@example.com"))


def test_get_unknown_employee_raises_not_found(service):
    with pytest.raises(EmployeeNotFoundError):
        service.get(999)


def test_salary_change_is_recorded_with_reason(service):
    employee = service.create(_payload())

    service.update(
        employee.id, EmployeeUpdate(annual_salary=2_640_000, salary_change_reason="Promotion")
    )

    [change] = service.salary_history(employee.id)
    assert (change.previous_salary, change.new_salary) == (2_400_000, 2_640_000)
    assert (change.previous_currency, change.new_currency) == ("INR", "INR")
    assert change.reason == "Promotion"


def test_non_salary_update_records_no_history(service):
    employee = service.create(_payload())

    updated = service.update(employee.id, EmployeeUpdate(job_title="Staff Engineer"))

    assert updated.job_title == "Staff Engineer"
    assert service.salary_history(employee.id) == []


def test_unchanged_salary_records_no_history(service):
    employee = service.create(_payload())
    service.update(employee.id, EmployeeUpdate(annual_salary=2_400_000))
    assert service.salary_history(employee.id) == []


def test_moving_to_a_different_currency_requires_a_new_salary(service):
    employee = service.create(_payload(country="India"))

    with pytest.raises(CurrencyChangeRequiresSalaryError):
        service.update(employee.id, EmployeeUpdate(country="Germany"))


def test_moving_country_with_new_salary_updates_currency_and_history(service):
    employee = service.create(_payload(country="India"))

    updated = service.update(employee.id, EmployeeUpdate(country="Germany", annual_salary=70_000))

    assert updated.currency == "EUR"
    [change] = service.salary_history(employee.id)
    assert (change.previous_currency, change.new_currency) == ("INR", "EUR")


def test_moving_within_same_currency_keeps_salary(service):
    employee = service.create(_payload(country="France", annual_salary=60_000))
    updated = service.update(employee.id, EmployeeUpdate(country="Germany"))
    assert (updated.currency, updated.annual_salary) == ("EUR", 60_000)


def test_update_rejects_email_belonging_to_someone_else(service):
    service.create(_payload(email="grace@example.com"))
    ada = service.create(_payload())

    with pytest.raises(DuplicateEmailError):
        service.update(ada.id, EmployeeUpdate(email="grace@example.com"))


def test_salary_history_is_newest_first(service):
    employee = service.create(_payload())
    service.update(employee.id, EmployeeUpdate(annual_salary=2_500_000))
    service.update(employee.id, EmployeeUpdate(annual_salary=2_600_000))

    assert [c.new_salary for c in service.salary_history(employee.id)] == [2_600_000, 2_500_000]


def test_delete_removes_employee(service):
    employee = service.create(_payload())
    service.delete(employee.id)
    with pytest.raises(EmployeeNotFoundError):
        service.get(employee.id)


def test_usd_salary_is_kept_in_sync_for_sorting(service):
    employee = service.create(_payload(country="India", annual_salary=1_000_000))
    assert employee.annual_salary_usd == 12_000

    service.update(employee.id, EmployeeUpdate(annual_salary=2_000_000))
    assert service.get(employee.id).annual_salary_usd == 24_000

    service.update(employee.id, EmployeeUpdate(country="Germany", annual_salary=50_000))
    assert service.get(employee.id).annual_salary_usd == 54_000


def test_salary_change_records_who_made_it(service):
    employee = service.create(_payload())
    service.update(employee.id, EmployeeUpdate(annual_salary=2_500_000))

    [change] = service.salary_history(employee.id)
    assert change.changed_by == "Priya Shah (HR)"


def test_salary_change_takes_effect_on_the_given_date(service):
    employee = service.create(_payload())
    service.update(
        employee.id,
        EmployeeUpdate(annual_salary=2_500_000, salary_effective_date=date(2026, 4, 1)),
    )

    [change] = service.salary_history(employee.id)
    assert change.effective_date == date(2026, 4, 1)


def test_salary_change_takes_effect_today_by_default(service):
    employee = service.create(_payload())
    service.update(employee.id, EmployeeUpdate(annual_salary=2_500_000))

    [change] = service.salary_history(employee.id)
    assert change.effective_date == date.today()


def test_salary_change_cannot_take_effect_before_the_hire_date(service):
    employee = service.create(_payload(hire_date=date(2021, 3, 1)))

    with pytest.raises(SalaryEffectiveBeforeHireError):
        service.update(
            employee.id,
            EmployeeUpdate(annual_salary=2_500_000, salary_effective_date=date(2021, 2, 28)),
        )


def test_salary_history_is_ordered_by_effective_date_even_when_backdated(service):
    employee = service.create(_payload())
    service.update(
        employee.id,
        EmployeeUpdate(annual_salary=2_600_000, salary_effective_date=date(2026, 4, 1)),
    )
    service.update(  # recorded later, but effective earlier
        employee.id,
        EmployeeUpdate(annual_salary=2_500_000, salary_effective_date=date(2025, 4, 1)),
    )

    history = service.salary_history(employee.id)
    assert [c.effective_date for c in history] == [date(2026, 4, 1), date(2025, 4, 1)]


def test_job_level_is_stored_and_can_change(service):
    employee = service.create(_payload(job_level="Senior"))
    assert employee.job_level == "Senior"

    assert service.update(employee.id, EmployeeUpdate(job_level="Lead")).job_level == "Lead"
