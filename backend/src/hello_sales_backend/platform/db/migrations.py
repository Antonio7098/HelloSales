"""Migration metadata helpers.

Provides the shared ``metadata`` object used by Alembic. Salesbook ORM Records
are registered lazily the first time ``metadata`` is accessed to avoid importing
module infra at platform load time.
"""
from __future__ import annotations

from hello_sales_backend.platform.db.base import Base, metadata as _base_metadata

_loaded = False


def _ensure_salesbook_models_registered() -> None:
    global _loaded
    if _loaded:
        return
    from hello_sales_backend.modules.salesbook.infra import persistence

    for name in persistence.__all__:
        model_cls = getattr(persistence, name)
        model_cls.__table__.tometadata(_base_metadata)
    _loaded = True


class _MetadataWrapper:
    """Lazy-load wrapper that triggers salesbook model registration on first access."""

    def __getattr__(self, name: str):
        _ensure_salesbook_models_registered()
        return getattr(_base_metadata, name)


metadata = _MetadataWrapper()


from hello_sales_backend.platform.db.models import (
    AgentArtifactRecord,
    AgentRunRecord,
    AgentStreamEventRecord,
    AgentToolCallRecord,
    AgentTurnRecord,
    CompanyProfileRecord,
    ProductRecord,
    SessionItemRecord,
    SessionRecord,
    SessionSummaryRecord,
    TaskRunRecord,
)

__all__ = [
    "AgentArtifactRecord",
    "AgentRunRecord",
    "AgentStreamEventRecord",
    "AgentToolCallRecord",
    "AgentTurnRecord",
    "CompanyProfileRecord",
    "ProductRecord",
    "SessionItemRecord",
    "SessionRecord",
    "SessionSummaryRecord",
    "TaskRunRecord",
    "metadata",
]
