"""Composite sales campaign workflow workers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hello_sales_backend.application.workers.contracts import (
    WorkerDefinition,
    WorkerPromptDefinition,
)
from hello_sales_backend.platform.llm import LLMMessage, PromptMetadata


class SalesCampaignBlueprintInput(BaseModel):
    """Input payload for the Stageflow-orchestrated campaign workflow."""

    campaign_goal: str = Field(min_length=1)
    target_segments: list[str] = Field(min_length=1, max_length=4)
    product_ids: list[str] = Field(default_factory=list, max_length=5)


class SalesAngleInput(BaseModel):
    """Input payload for one product and segment positioning run."""

    company_name: str = Field(min_length=1)
    industry: str | None = None
    target_customer: str | None = None
    quarterly_sales_focus: str | None = None
    product_name: str = Field(min_length=1)
    product_description: str | None = None
    primary_use_case: str | None = None
    pricing_model: str | None = None
    deal_size: str | None = None
    segment_name: str = Field(min_length=1)
    campaign_goal: str = Field(min_length=1)


class SalesAngleOutput(BaseModel):
    """High-level message strategy for a product and segment."""

    headline: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    value_points: list[str] = Field(min_length=2, max_length=4)
    confidence: Literal["low", "medium", "high"]


class ObjectionHandlingInput(BaseModel):
    """Input payload for objection-mapping."""

    company_name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    segment_name: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    value_points: list[str] = Field(min_length=2, max_length=4)
    pricing_model: str | None = None
    deal_size: str | None = None
    primary_sales_constraint: str | None = None


class ObjectionResponse(BaseModel):
    """One likely objection and the recommended response."""

    objection: str = Field(min_length=1)
    response: str = Field(min_length=1)


class ObjectionHandlingOutput(BaseModel):
    """Structured objection handling guidance."""

    likely_objections: list[ObjectionResponse] = Field(min_length=2, max_length=4)


class OutreachSequenceInput(BaseModel):
    """Input payload for first-touch outreach generation."""

    company_name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    segment_name: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    value_points: list[str] = Field(min_length=2, max_length=4)
    likely_objections: list[ObjectionResponse] = Field(min_length=2, max_length=4)


class OutreachSequenceOutput(BaseModel):
    """Structured outreach assets for one product and segment."""

    subject_lines: list[str] = Field(min_length=2, max_length=3)
    email_opener: str = Field(min_length=1)
    call_opener: str = Field(min_length=1)
    call_to_action: str = Field(min_length=1)


class CampaignBlueprintSummary(BaseModel):
    """Summary counts for the assembled campaign blueprint."""

    total_products: int = Field(ge=1)
    total_segments: int = Field(ge=1)
    total_blueprints: int = Field(ge=1)


class ProductSegmentBlueprint(BaseModel):
    """One assembled product and segment blueprint."""

    product_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    segment_name: str = Field(min_length=1)
    angle: SalesAngleOutput
    objection_handling: ObjectionHandlingOutput
    outreach_sequence: OutreachSequenceOutput
    child_run_ids: list[str] = Field(min_length=3, max_length=3)


class SalesCampaignBlueprintOutput(BaseModel):
    """Final output for the Stageflow-composed campaign workflow."""

    company_name: str = Field(min_length=1)
    campaign_goal: str = Field(min_length=1)
    blueprints: list[ProductSegmentBlueprint] = Field(min_length=1)
    summary: CampaignBlueprintSummary


def _workflow_only_messages(_validated_input: BaseModel, _retry_issue: str | None) -> list[LLMMessage]:
    raise RuntimeError("This worker must be executed through the Stageflow workflow path")


def _sales_angle_messages(validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]:
    payload = SalesAngleInput.model_validate(validated_input.model_dump(mode="json"))
    instructions = [
        "Return only JSON that satisfies the provided schema.",
        "Write concise B2B sales positioning grounded in the supplied company and product context.",
        f"Company: {payload.company_name}",
        f"Industry: {payload.industry or 'unknown'}",
        f"Target customer: {payload.target_customer or 'unknown'}",
        f"Quarterly sales focus: {payload.quarterly_sales_focus or 'unknown'}",
        f"Product: {payload.product_name}",
        f"Product description: {payload.product_description or 'unknown'}",
        f"Primary use case: {payload.primary_use_case or 'unknown'}",
        f"Pricing model: {payload.pricing_model or 'unknown'}",
        f"Deal size: {payload.deal_size or 'unknown'}",
        f"Segment: {payload.segment_name}",
        f"Campaign goal: {payload.campaign_goal}",
        "Provide 2 to 4 concrete value points and a realistic confidence level.",
    ]
    if retry_issue is not None:
        instructions.append(f"Previous output issue: {retry_issue}")
    return [LLMMessage(role="user", content="\n".join(instructions))]


def _objection_messages(validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]:
    payload = ObjectionHandlingInput.model_validate(validated_input.model_dump(mode="json"))
    instructions = [
        "Return only JSON that satisfies the provided schema.",
        "List likely sales objections and concise responses tailored to this offer.",
        f"Company: {payload.company_name}",
        f"Product: {payload.product_name}",
        f"Segment: {payload.segment_name}",
        f"Headline: {payload.headline}",
        f"Value points: {', '.join(payload.value_points)}",
        f"Pricing model: {payload.pricing_model or 'unknown'}",
        f"Deal size: {payload.deal_size or 'unknown'}",
        f"Primary sales constraint: {payload.primary_sales_constraint or 'unknown'}",
        "Return 2 to 4 objections with practical responses.",
    ]
    if retry_issue is not None:
        instructions.append(f"Previous output issue: {retry_issue}")
    return [LLMMessage(role="user", content="\n".join(instructions))]


def _outreach_messages(validated_input: BaseModel, retry_issue: str | None) -> list[LLMMessage]:
    payload = OutreachSequenceInput.model_validate(validated_input.model_dump(mode="json"))
    objections = "; ".join(
        f"{item.objection}: {item.response}" for item in payload.likely_objections
    )
    instructions = [
        "Return only JSON that satisfies the provided schema.",
        "Draft practical first-touch outreach for a salesperson.",
        f"Company: {payload.company_name}",
        f"Product: {payload.product_name}",
        f"Segment: {payload.segment_name}",
        f"Headline: {payload.headline}",
        f"Why now: {payload.why_now}",
        f"Value points: {', '.join(payload.value_points)}",
        f"Objections and responses: {objections}",
        "Produce 2 to 3 subject lines, one email opener, one call opener, and one call to action.",
    ]
    if retry_issue is not None:
        instructions.append(f"Previous output issue: {retry_issue}")
    return [LLMMessage(role="user", content="\n".join(instructions))]


def build_sales_campaign_blueprint_definition() -> WorkerDefinition:
    """Return the workflow-only top-level campaign worker definition."""

    return WorkerDefinition(
        worker_name="sales-campaign-blueprint",
        display_name="Sales Campaign Blueprint",
        description="Compose product and segment sales assets from persisted company context.",
        input_model=SalesCampaignBlueprintInput,
        output_model=SalesCampaignBlueprintOutput,
        prompt=WorkerPromptDefinition(
            metadata=PromptMetadata(
                prompt_id="worker.sales-campaign-blueprint.workflow",
                version="v1",
                owner_kind="worker",
                owner_id="sales-campaign-blueprint",
                purpose="workflow",
            ),
            build_messages=_workflow_only_messages,
        ),
        supports_direct_execution=False,
        max_attempts=1,
        timeout_seconds=90.0,
        use_backup_on_final_attempt=False,
    )


def build_sales_angle_definition() -> WorkerDefinition:
    """Return the product and segment positioning worker definition."""

    return WorkerDefinition(
        worker_name="sales-angle",
        display_name="Sales Angle",
        description="Generate a concise positioning angle for one product and segment.",
        input_model=SalesAngleInput,
        output_model=SalesAngleOutput,
        prompt=WorkerPromptDefinition(
            metadata=PromptMetadata(
                prompt_id="worker.sales-angle.generation",
                version="v1",
                owner_kind="worker",
                owner_id="sales-angle",
                purpose="generation",
            ),
            build_messages=_sales_angle_messages,
        ),
        max_attempts=3,
        timeout_seconds=25.0,
        use_backup_on_final_attempt=True,
    )


def build_objection_handling_definition() -> WorkerDefinition:
    """Return the objection-mapping worker definition."""

    return WorkerDefinition(
        worker_name="objection-handling",
        display_name="Objection Handling",
        description="Map likely objections and responses for one product and segment.",
        input_model=ObjectionHandlingInput,
        output_model=ObjectionHandlingOutput,
        prompt=WorkerPromptDefinition(
            metadata=PromptMetadata(
                prompt_id="worker.objection-handling.generation",
                version="v1",
                owner_kind="worker",
                owner_id="objection-handling",
                purpose="generation",
            ),
            build_messages=_objection_messages,
        ),
        max_attempts=3,
        timeout_seconds=25.0,
        use_backup_on_final_attempt=True,
    )


def build_outreach_sequence_definition() -> WorkerDefinition:
    """Return the outreach asset worker definition."""

    return WorkerDefinition(
        worker_name="outreach-sequence",
        display_name="Outreach Sequence",
        description="Draft first-touch outreach assets for one product and segment.",
        input_model=OutreachSequenceInput,
        output_model=OutreachSequenceOutput,
        prompt=WorkerPromptDefinition(
            metadata=PromptMetadata(
                prompt_id="worker.outreach-sequence.generation",
                version="v1",
                owner_kind="worker",
                owner_id="outreach-sequence",
                purpose="generation",
            ),
            build_messages=_outreach_messages,
        ),
        max_attempts=3,
        timeout_seconds=25.0,
        use_backup_on_final_attempt=True,
    )
