"""AI substrate: Core infrastructure for agentic pipeline execution."""

from app.ai.substrate.agent import (
    ContextSnapshot,
    DocumentEnrichment,
    MemoryEnrichment,
    Message,
    ProfileEnrichment,
    RoutingDecision,
    SkillsEnrichment,
)
from app.ai.substrate.events import EventSink, emit_event, register_event_sink
from app.ai.substrate.observability import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    PipelineEventLogger,
    PipelineRunLogger,
    ProviderCallLogger,
    error_summary_to_stages_patch,
    error_summary_to_string,
    get_circuit_breaker,
    summarize_pipeline_error,
)
from app.ai.substrate.policy import (
    PolicyCheckpoint,
    PolicyContext,
    PolicyDecision,
    PolicyGateway,
    PolicyResult,
)
from app.ai.substrate.projector import ProjectorService
from app.ai.substrate.stages import (
    PipelineContext,
    PipelineOrchestrator,
    SendStatus,
    SendToken,
    Stage,
    StageError,
    StageResult,
    StageStatus,
    is_cancel_requested,
    request_cancel,
)
from app.ai.substrate.stages.agent import (
    Action,
    ActionType,
    AgentResult,
    ToolExecutionError,
    ToolExecutor,
    ToolNotFoundError,
    ToolRegistry,
    handle_agent_output_runtime,
)

__all__ = [
    # Agent module
    "AgentRequest",
    "AgentPlan",  # Backwards compatibility
    "RoutingPlan",
    "Plan",
    "Action",
    "Artifact",
    "BaseAgent",
    "AgentError",
    "ActionType",
    "ArtifactType",
    "ContextSnapshot",
    "Message",
    "RoutingDecision",
    "ProfileEnrichment",
    "MemoryEnrichment",
    "SkillsEnrichment",
    "DocumentEnrichment",
    "handle_agent_output_runtime",
    # Agent stages
    "AgentResult",
    "ToolExecutionError",
    "ToolExecutor",
    "ToolNotFoundError",
    "ToolRegistry",
    # Pipeline
    "PipelineContext",
    "Stage",
    "StageResult",
    "StageError",
    "StageStatus",
    "PipelineOrchestrator",
    "SendStatus",
    "SendToken",
    "is_cancel_requested",
    "request_cancel",
    # Projector
    "ProjectorService",
    # Policy
    "PolicyGateway",
    "PolicyCheckpoint",
    "PolicyContext",
    "PolicyDecision",
    "PolicyResult",
    # Events
    "EventSink",
    "register_event_sink",
    "emit_event",
    # Observability
    "ProviderCallLogger",
    "PipelineRunLogger",
    "PipelineEventLogger",
    "get_circuit_breaker",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "error_summary_to_stages_patch",
    "error_summary_to_string",
    "summarize_pipeline_error",
]
