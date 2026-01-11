"""Persist stage - saves interactions to database."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipelines.stages.base import Stage, StageContext, StageResult
from app.application.services.session_service import SessionService
from app.infrastructure.telemetry import get_logger

logger = get_logger(__name__)


class PersistStage(Stage[StageContext]):
    """Persists the interaction to the database.

    Saves both user input and assistant response as interactions,
    and updates summary state if needed.
    """

    def __init__(self, db: AsyncSession, summary_threshold: int = 8):
        self.db = db
        self.session_service = SessionService(db)
        self.summary_threshold = summary_threshold

    @property
    def name(self) -> str:
        return "persist"

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute persistence."""
        if not ctx.session_id:
            logger.warning("No session_id in context, skipping persist")
            return StageResult(success=True)

        try:
            # Save user interaction
            if ctx.user_input:
                await self.session_service.add_interaction(
                    session_id=ctx.session_id,
                    role="user",
                    content=ctx.user_input,
                    input_type=ctx.input_type,
                )

            # Save assistant response
            final_output = ctx.get_final_output()
            if final_output:
                await self.session_service.add_interaction(
                    session_id=ctx.session_id,
                    role="assistant",
                    content=final_output,
                    metadata={
                        "tokens_in": ctx.tokens_in,
                        "tokens_out": ctx.tokens_out,
                        "output_blocked": ctx.output_blocked,
                    },
                )

            # Update turn count for summary tracking
            await self.session_service.increment_turn_count(ctx.session_id)

            # Check if summary is needed
            needs_summary = await self.session_service.check_summary_needed(
                ctx.session_id,
                threshold=self.summary_threshold,
            )

            if needs_summary:
                ctx.metadata["summary_needed"] = True
                logger.info(
                    "Summary generation needed",
                    extra={"session_id": str(ctx.session_id)},
                )

            logger.debug(
                "Interactions persisted",
                extra={
                    "session_id": str(ctx.session_id),
                    "needs_summary": needs_summary,
                },
            )

            return StageResult(
                success=True,
                metadata={"summary_needed": needs_summary},
            )

        except Exception as e:
            logger.exception(
                "Failed to persist interactions",
                extra={"session_id": str(ctx.session_id)},
            )
            return StageResult(
                success=False,
                error=str(e),
                error_code="PERSIST_FAILED",
                should_continue=True,  # Don't fail pipeline for persist errors
            )
