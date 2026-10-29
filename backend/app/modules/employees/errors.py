from app.core.errors import BusinessRuleError, ConflictError, NotFoundError


class EmployeeNotFoundError(NotFoundError):
    def __init__(self, employee_id: int) -> None:
        super().__init__(f"Employee {employee_id} not found")


class DuplicateEmailError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(f"An employee with email {email!r} already exists")


class CurrencyChangeRequiresSalaryError(BusinessRuleError):
    def __init__(self, old: str, new: str) -> None:
        super().__init__(
            f"Moving from {old} to {new} changes currency; provide annual_salary in {new}"
        )
