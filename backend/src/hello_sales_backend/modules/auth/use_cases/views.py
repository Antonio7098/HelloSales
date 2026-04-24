"""Auth-facing views."""

from pydantic import BaseModel, Field


class CurrentSessionView(BaseModel):
    """Current authenticated session returned to adapters."""

    provider_name: str
    actor_id: str
    user_id: str
    session_id: str | None = None
    org_id: str | None = None
    email: str | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    impersonator_email: str | None = None


class LogoutView(BaseModel):
    """Logout response returned to adapters."""

    redirect_url: str | None = None
