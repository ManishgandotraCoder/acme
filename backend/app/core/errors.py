"""Domain error hierarchy.

Modules raise errors from these categories; the HTTP layer maps a *category* to a status
code once (core/http_errors.py). Adding a new error never requires touching infrastructure.
"""


class DomainError(Exception):
    """A business rule was violated. Message is safe to show to the user."""

    @property
    def public_message(self) -> str:
        return str(self)


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class BusinessRuleError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    """The actor may not see or do this."""


class ServiceUnavailableError(DomainError):
    """A dependency failed. ``str(error)`` holds internal details for logs only."""

    public_message = "A required service is temporarily unavailable."  # type: ignore[assignment]
