"""Agent output validation utilities.

This module provides validation functions for agent outputs, including
parsing JSON payloads and validating against the AgentOutput schema.
"""

import json
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.ai.substrate import PipelineEventLogger
from app.database import get_session_context
from app.schemas.agent_output import AgentOutput


def parse_agent_output(text: str) -> tuple[AgentOutput | None, str | None, bool]:
    """Parse agent output JSON and validate against AgentOutput schema.

    Args:
        text: Raw text output from the agent (expected to be JSON).

    Returns:
        Tuple of (parsed_output, error, attempted):
        - parsed_output: AgentOutput if valid, None otherwise
        - error: Error code string if parsing failed, None otherwise
        - attempted: True if parsing was attempted, False otherwise
    """
    stripped = (text or "").strip()
    if not stripped:
        return None, None, False

    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None, None, False

    attempted = True
    try:
        payload = json.loads(stripped)
    except Exception:
        return None, "invalid_json", attempted

    if not isinstance(payload, dict):
        return None, "not_object", attempted

    if not ("assistant_message" in payload or "actions" in payload or "artifacts" in payload):
        return None, None, False

    try:
        parsed = AgentOutput.model_validate(payload)
    except ValidationError:
        return None, "schema_validation_error", attempted

    return parsed, None, attempted


async def emit_agent_output_validation_event(
    *,
    pipeline_run_id: UUID | None,
    request_id: UUID | None,
    session_id: UUID | None,
    user_id: UUID | None,
    org_id: UUID | None,
    success: bool,
    error: str | None,
    parsed: dict[str, Any] | None,
    raw_excerpt: str | None,
) -> None:
    """Emit observability event for agent output validation results.

    Args:
        pipeline_run_id: Unique identifier for the pipeline run
        request_id: Unique identifier for the request
        session_id: Session identifier
        user_id: User identifier
        org_id: Organization identifier
        success: Whether validation succeeded
        error: Error code if validation failed
        parsed: Parsed validation result data
        raw_excerpt: Raw excerpt of the validated text
    """
    if pipeline_run_id is None:
        return

    data: dict[str, Any] = {
        "success": success,
        "error": error,
        "parsed": parsed,
        "raw_excerpt": raw_excerpt,
    }

    async with get_session_context() as db:
        event_logger = PipelineEventLogger(db)
        await event_logger.emit(
            pipeline_run_id=pipeline_run_id,
            type="validation.agent_output",
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            data=data,
        )
