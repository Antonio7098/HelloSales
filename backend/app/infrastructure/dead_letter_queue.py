"""Dead Letter Queue service for capturing failed pipeline runs.

Provides functionality to:
- Enqueue failed pipeline runs for later inspection
- Query DLQ entries by various criteria
- Resolve/reprocess DLQ entries

See stageflow.md §5.6 for specification.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.substrate.stages.context import PipelineContext
from app.models.observability import DeadLetterQueue


class DeadLetterQueueService:
    """Service for managing dead letter queue entries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def enqueue(
        self,
        ctx: PipelineContext,
        error: Exception,
        failed_stage: str | None = None,
        context_snapshot: dict[str, Any] | None = None,
    ) -> DeadLetterQueue:
        """Enqueue a failed pipeline run to the DLQ.

        Args:
            ctx: PipelineContext at time of failure
            error: The exception that caused the failure
            failed_stage: Name of the stage that failed (if known)
            context_snapshot: Context snapshot at time of failure

        Returns:
            The created DeadLetterQueue entry
        """
        # Determine service from context or topology
        service = self._determine_service(ctx)

        # Extract error type from exception class name
        error_type = type(error).__name__

        dlq_entry = DeadLetterQueue(
            pipeline_run_id=ctx.pipeline_run_id,
            request_id=ctx.request_id,
            session_id=ctx.session_id,
            user_id=ctx.user_id,
            org_id=ctx.org_id,
            service=service,
            error_type=error_type,
            error_message=str(error),
            failed_stage=failed_stage,
            context_snapshot=context_snapshot,
            input_data=self._extract_input_data(ctx),
            status="pending",
        )

        self.db.add(dlq_entry)
        await self.db.commit()
        await self.db.refresh(dlq_entry)

        return dlq_entry

    async def get_pending(self, limit: int = 100) -> list[DeadLetterQueue]:
        """Get pending DLQ entries.

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of pending DLQ entries
        """
        stmt = (
            select(DeadLetterQueue)
            .where(DeadLetterQueue.status == "pending")
            .order_by(DeadLetterQueue.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_service(self, service: str, status: str | None = None) -> list[DeadLetterQueue]:
        """Get DLQ entries by service.

        Args:
            service: Service name ('voice', 'chat')
            status: Optional status filter

        Returns:
            List of matching DLQ entries
        """
        stmt = select(DeadLetterQueue).where(DeadLetterQueue.service == service)

        if status:
            stmt = stmt.where(DeadLetterQueue.status == status)

        stmt = stmt.order_by(DeadLetterQueue.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def resolve(
        self,
        dlq_id: UUID,
        resolved_by: UUID,
        notes: str | None = None,
    ) -> DeadLetterQueue:
        """Mark a DLQ entry as resolved.

        Args:
            dlq_id: ID of the DLQ entry to resolve
            resolved_by: User ID who resolved it
            notes: Optional resolution notes

        Returns:
            The updated DLQ entry
        """
        stmt = select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_id)
        result = await self.db.execute(stmt)
        dlq_entry = result.scalar_one_or_none()

        if not dlq_entry:
            raise ValueError(f"DLQ entry {dlq_id} not found")

        dlq_entry.status = "resolved"
        dlq_entry.resolved_at = datetime.utcnow()
        dlq_entry.resolved_by = resolved_by
        dlq_entry.resolution_notes = notes

        await self.db.commit()
        await self.db.refresh(dlq_entry)

        return dlq_entry

    async def mark_reprocessed(self, dlq_id: UUID) -> DeadLetterQueue:
        """Mark a DLQ entry as reprocessed (successfully retried).

        Args:
            dlq_id: ID of the DLQ entry

        Returns:
            The updated DLQ entry
        """
        stmt = select(DeadLetterQueue).where(DeadLetterQueue.id == dlq_id)
        result = await self.db.execute(stmt)
        dlq_entry = result.scalar_one_or_none()

        if not dlq_entry:
            raise ValueError(f"DLQ entry {dlq_id} not found")

        dlq_entry.status = "reprocessed"
        dlq_entry.retry_count += 1
        dlq_entry.last_retry_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(dlq_entry)

        return dlq_entry

    async def get_stats(self) -> dict[str, Any]:
        """Get DLQ statistics.

        Returns:
            Dictionary with DLQ statistics
        """
        # Count by status
        status_counts = {}
        for status in ["pending", "investigating", "resolved", "reprocessed"]:
            stmt = select(func.count(DeadLetterQueue.id)).where(
                DeadLetterQueue.status == status
            )
            result = await self.db.execute(stmt)
            status_counts[status] = result.scalar() or 0

        # Count by error type
        stmt = (
            select(DeadLetterQueue.error_type, func.count(DeadLetterQueue.id))
            .group_by(DeadLetterQueue.error_type)
            .order_by(func.count(DeadLetterQueue.id).desc())
            .limit(10)
        )
        result = await self.db.execute(stmt)
        error_type_counts = {row[0]: row[1] for row in result.fetchall()}

        # Count by service
        stmt = (
            select(DeadLetterQueue.service, func.count(DeadLetterQueue.id))
            .group_by(DeadLetterQueue.service)
        )
        result = await self.db.execute(stmt)
        service_counts = {row[0]: row[1] for row in result.fetchall()}

        return {
            "by_status": status_counts,
            "by_error_type": error_type_counts,
            "by_service": service_counts,
            "total": sum(status_counts.values()),
        }

    def _determine_service(self, ctx: PipelineContext) -> str:
        """Determine service name from context."""
        # Try to infer from topology or behavior
        topology = ctx.topology or ""
        behavior = ctx.behavior or ""

        if "voice" in topology.lower() or "voice" in behavior.lower():
            return "voice"
        if "chat" in topology.lower() or "chat" in behavior.lower():
            return "chat"

        # Fall back to behavior if set
        if behavior:
            return behavior

        # Default to "unknown"
        return "unknown"

    def _extract_input_data(self, ctx: PipelineContext) -> dict[str, Any]:
        """Extract relevant input data from context for reprocessing."""
        # Copy relevant fields from context.data
        input_data = dict(ctx.data)

        # Remove internal keys that shouldn't be stored
        internal_keys = [k for k in input_data if k.startswith("_")]
        for key in internal_keys:
            input_data.pop(key, None)

        return input_data


async def create_dlq_entry(
    db: AsyncSession,
    ctx: PipelineContext,
    error: Exception,
    failed_stage: str | None = None,
) -> DeadLetterQueue:
    """Convenience function to create a DLQ entry."""
    service = DeadLetterQueueService(db)
    return await service.enqueue(
        ctx=ctx,
        error=error,
        failed_stage=failed_stage,
        context_snapshot=ctx.data.get("context_snapshot_metadata"),
    )
