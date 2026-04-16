"""Jobs diagnostic workflow."""

from __future__ import annotations

from hello_sales_backend.platform.providers.llm.contracts import ChatMessage, ChatModelPort
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.workflows.executor import WorkflowExecutor


async def run_diagnostic_workflow(
    *,
    metadata: TaskMetadata,
    workflow_executor: WorkflowExecutor,
    llm_provider: ChatModelPort,
    prompt: str,
) -> None:
    """Run a minimal provider-backed diagnostic workflow."""

    await workflow_executor.run_diagnostic_workflow(
        metadata=metadata,
        llm_provider=llm_provider,
        messages=[ChatMessage(role="user", content=prompt)],
    )
