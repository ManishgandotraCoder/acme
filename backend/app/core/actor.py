"""Who is making the request.

The app has a single persona and no login yet (docs/REQUIREMENTS.md), so the actor comes from
configuration. This is the one seam an SSO integration would fill: services record
``actor.name`` in audit trails and check ``actor.can(...)`` before individual-level results.
"""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.errors import PermissionDeniedError

VIEW_INDIVIDUAL_PAY = "view_individual_pay"
_DENIED = {
    VIEW_INDIVIDUAL_PAY: "You don't have permission to see individual employees' pay.",
}


@dataclass(frozen=True, slots=True)
class Actor:
    name: str
    permissions: frozenset[str]

    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if not self.can(permission):
            raise PermissionDeniedError(_DENIED.get(permission, "Permission denied."))


# Seed scripts and other non-request code paths.
SYSTEM = Actor(name="System", permissions=frozenset())


def get_actor(request: Request) -> Actor:
    return request.app.state.actor


ActorDep = Annotated[Actor, Depends(get_actor)]
