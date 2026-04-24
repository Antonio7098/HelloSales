"""Shared authentication and authorization primitives."""

from __future__ import annotations

from dataclasses import dataclass, field

from hello_sales_backend.shared.errors import app_error

APP_ACCESS_PERMISSION = "app.access"
SESSIONS_READ_PERMISSION = "sessions.read"
SESSIONS_WRITE_PERMISSION = "sessions.write"
SESSIONS_READ_ANY_PERMISSION = "sessions.read:any"
SESSIONS_WRITE_ANY_PERMISSION = "sessions.write:any"
COMPANY_PROFILE_READ_PERMISSION = "company_profile.read"
COMPANY_PROFILE_WRITE_PERMISSION = "company_profile.write"
JOBS_READ_PERMISSION = "jobs.read"
JOBS_RUN_PERMISSION = "jobs.run"
WORKERS_READ_PERMISSION = "workers.read"
WORKERS_RUN_PERMISSION = "workers.run"
WORKERS_CANCEL_PERMISSION = "workers.cancel"
SYSTEM_READ_PERMISSION = "system.read"
ANALYTICS_READ_PERMISSION = "analytics.read"
WEB_SEARCH_USE_PERMISSION = "web_search.use"
ENTITY_OPERATIONS_WRITE_PERMISSION = "entity_operations.write"


@dataclass(slots=True, frozen=True)
class AuthContext:
    """Provider-neutral authenticated actor snapshot."""

    provider_name: str
    actor_id: str
    user_id: str
    session_id: str | None = None
    org_id: str | None = None
    email: str | None = None
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()
    impersonator_email: str | None = None
    raw_claims: dict[str, object] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        """Return whether the current auth context includes one permission."""

        return permission in set(self.permissions)

    def missing_permissions(self, *permissions: str) -> list[str]:
        """Return the subset of required permissions that are absent."""

        current = set(self.permissions)
        return [permission for permission in permissions if permission not in current]

    def require_permissions(
        self,
        *permissions: str,
        operation: str,
        component: str,
        details: dict[str, object] | None = None,
    ) -> None:
        """Raise a structured 403 when required permissions are absent."""

        missing = self.missing_permissions(*permissions)
        if not missing:
            return
        raise app_error(
            "Authenticated actor does not have the required permissions",
            code="auth.permission_denied",
            category="validation",
            status_code=403,
            severity="warning",
            details={
                "actor_id": self.actor_id,
                "org_id": self.org_id,
                "missing_permissions": missing,
                "required_permissions": list(permissions),
                **(details or {}),
            },
            operation=operation,
            component=component,
        )

