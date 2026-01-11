"""Enrichment stages - context building for LLM."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pipelines.stages.base import Stage, StageContext, StageResult
from app.domain.protocols.providers import LLMMessage
from app.infrastructure.repositories.company_profile_repository import (
    CompanyProfileRepositoryImpl,
)
from app.infrastructure.repositories.interaction_repository import (
    InteractionRepositoryImpl,
)
from app.infrastructure.repositories.product_repository import ProductRepositoryImpl
from app.infrastructure.repositories.client_repository import ClientRepositoryImpl
from app.infrastructure.telemetry import get_logger

logger = get_logger(__name__)


class ProfileEnrichStage(Stage[StageContext]):
    """Enriches context with product, client, and company profiles.

    Fetches relevant context data and builds the system prompt
    with product knowledge, client information, and company details.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.product_repo = ProductRepositoryImpl(db)
        self.client_repo = ClientRepositoryImpl(db)
        self.company_repo = CompanyProfileRepositoryImpl(db)

    @property
    def name(self) -> str:
        return "profile_enrich"

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute profile enrichment."""
        # Get product context if specified
        if ctx.metadata.get("product_id") and ctx.org_id:
            product = await self.product_repo.get_by_id(
                ctx.metadata["product_id"],
                ctx.org_id,
            )
            if product:
                ctx.product_context = product.to_context_dict()
                logger.debug(
                    "Product context loaded",
                    extra={"product_id": str(product.id)},
                )

        # Get client context if specified
        if ctx.metadata.get("client_id") and ctx.org_id:
            client = await self.client_repo.get_by_id(
                ctx.metadata["client_id"],
                ctx.org_id,
            )
            if client:
                ctx.client_context = client.to_context_dict()
                logger.debug(
                    "Client context loaded",
                    extra={"client_id": str(client.id)},
                )

        # Get company profile for org
        if ctx.org_id:
            company = await self.company_repo.get_by_org(ctx.org_id)
            if company:
                ctx.company_context = company.to_context_dict()
                logger.debug(
                    "Company context loaded",
                    extra={"company_id": str(company.id)},
                )

        # Build system prompt
        ctx.system_prompt = self._build_system_prompt(ctx)

        return StageResult(success=True)

    def _build_system_prompt(self, ctx: StageContext) -> str:
        """Build the system prompt with context."""
        parts = []

        # Base persona
        parts.append(
            "You are a helpful AI sales assistant for HelloSales. "
            "Your goal is to help sales representatives prepare for calls, "
            "craft compelling emails, and improve their sales effectiveness."
        )

        # Company context
        if ctx.company_context:
            parts.append(f"\n\n## Company Information\n")
            parts.append(f"Company: {ctx.company_context.get('name', 'Unknown')}")
            if ctx.company_context.get("industry"):
                parts.append(f"Industry: {ctx.company_context['industry']}")
            if ctx.company_context.get("value_proposition"):
                parts.append(
                    f"Value Proposition: {ctx.company_context['value_proposition']}"
                )

        # Product context
        if ctx.product_context:
            parts.append(f"\n\n## Product Information\n")
            parts.append(f"Product: {ctx.product_context.get('name', 'Unknown')}")
            if ctx.product_context.get("description"):
                parts.append(f"Description: {ctx.product_context['description']}")
            if ctx.product_context.get("key_features"):
                parts.append("Key Features:")
                for feature in ctx.product_context["key_features"]:
                    parts.append(f"  - {feature}")
            if ctx.product_context.get("target_audience"):
                parts.append(
                    f"Target Audience: {ctx.product_context['target_audience']}"
                )

        # Client context
        if ctx.client_context:
            parts.append(f"\n\n## Client Information\n")
            parts.append(f"Contact: {ctx.client_context.get('name', 'Unknown')}")
            if ctx.client_context.get("company"):
                parts.append(f"Company: {ctx.client_context['company']}")
            if ctx.client_context.get("pain_points"):
                parts.append("Known Pain Points:")
                for point in ctx.client_context["pain_points"]:
                    parts.append(f"  - {point}")
            if ctx.client_context.get("goals"):
                parts.append("Goals:")
                for goal in ctx.client_context["goals"]:
                    parts.append(f"  - {goal}")

        # Conversation summary if available
        if ctx.conversation_summary:
            parts.append(f"\n\n## Conversation Summary\n")
            parts.append(ctx.conversation_summary)

        return "\n".join(parts)


class SummaryEnrichStage(Stage[StageContext]):
    """Enriches context with conversation history and summary.

    Fetches recent interactions and any existing summary,
    building the messages list for LLM context.
    """

    def __init__(
        self,
        db: AsyncSession,
        always_include_last_n: int = 6,
    ):
        self.db = db
        self.interaction_repo = InteractionRepositoryImpl(db)
        self.always_include_last_n = always_include_last_n

    @property
    def name(self) -> str:
        return "summary_enrich"

    async def execute(self, ctx: StageContext) -> StageResult:
        """Execute summary enrichment."""
        if not ctx.session_id:
            return StageResult(success=True)

        # Get recent interactions
        recent = await self.interaction_repo.get_recent(
            ctx.session_id,
            limit=self.always_include_last_n,
        )

        # Convert to LLM messages
        for interaction in recent:
            if interaction.content:
                ctx.recent_turns.append(
                    LLMMessage(
                        role=interaction.role,
                        content=interaction.content,
                    )
                )

        logger.debug(
            "Conversation history loaded",
            extra={
                "session_id": str(ctx.session_id),
                "turn_count": len(ctx.recent_turns),
            },
        )

        # Build messages list
        self._build_messages(ctx)

        return StageResult(success=True)

    def _build_messages(self, ctx: StageContext) -> None:
        """Build the full messages list for LLM."""
        # Start with system prompt
        if ctx.system_prompt:
            ctx.messages = [LLMMessage(role="system", content=ctx.system_prompt)]
        else:
            ctx.messages = []

        # Add summary as assistant context if available
        if ctx.conversation_summary:
            ctx.messages.append(
                LLMMessage(
                    role="assistant",
                    content=f"[Previous conversation summary: {ctx.conversation_summary}]",
                )
            )

        # Add recent turns
        ctx.messages.extend(ctx.recent_turns)

        # Add current user input
        if ctx.user_input:
            ctx.messages.append(
                LLMMessage(role="user", content=ctx.user_input)
            )
