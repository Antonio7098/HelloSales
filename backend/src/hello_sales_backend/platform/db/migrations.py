"""Migration metadata helpers."""

from hello_sales_backend.platform.db.base import metadata
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

# Side-effect import: register salesbook ORM Records with Base.metadata so
# Alembic autogenerate discovers them. Keep all salesbook ORM in modules/salesbook/.
from hello_sales_backend.modules.salesbook.infra.persistence import *  # noqa: F401, E402, F403  /Oliviercontribution

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
