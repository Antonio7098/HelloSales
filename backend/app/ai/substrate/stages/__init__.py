"""Unified stages module for substrate architecture.

This module provides the unified stage system:
- base.py: Core types (Stage, StageKind, StageOutput, StageContext)
- registry.py: Single registry for all stage types
- graph.py: DAG executor for unified Stage protocol

All components are Stages with a StageKind:
- TRANSFORM: STT, TTS, LLM
- ENRICH: Profile, Memory, Skills
- ROUTE: Router, Dispatcher
- GUARD: Guardrails, Policy
- WORK: Assessment, Triage, Persist
- AGENT: Coach, Interviewer
"""

from app.ai.substrate.stages.agent import (
    Action,
    ActionType,
    AgentResult,
    ToolExecutionError,
    ToolExecutor,
    ToolNotFoundError,
    ToolRegistration,
    ToolRegistry,
    execute_action,
    execute_actions,
)
from app.ai.substrate.stages.base import (
    Stage,
    StageArtifact,
    StageContext,
    StageEvent,
    StageKind,
    StageOutput,
    StageStatus,
    create_stage_context,
)
from app.ai.substrate.stages.context import (
    PipelineContext,
    extract_quality_mode,
    extract_service,
)
from app.ai.substrate.stages.errors import (
    StageRunner,
    create_error_context,
    handle_async_task_error,
    handle_provider_error,
    log_debug_failure,
    log_stage_error,
    safe_debug_log,
    with_error_handling,
)
from app.ai.substrate.stages.graph import (
    StageRunnerAdapter,
    UnifiedPipelineCancelled,
    UnifiedStageExecutionError,
    UnifiedStageGraph,
    UnifiedStageSpec,
    create_unified_spec_from_stage,
)
from app.ai.substrate.stages.orchestrator import (
    PipelineOrchestrator,
    SendStatus,
    SendToken,
    is_cancel_requested,
    request_cancel,
)
from app.ai.substrate.stages.registry import (
    StageRegistry,
    clear_all_registries,
    get_agent,
    get_agent_or_raise,
    get_dispatcher,
    get_dispatcher_or_raise,
    get_enricher,
    get_enricher_or_raise,
    get_enrichers_by_domain,
    get_enrichers_by_phase,
    get_guardrails,
    get_guardrails_or_raise,
    get_router,
    get_router_or_raise,
    get_stage,
    get_worker,
    get_worker_or_raise,
    list_agents,
    list_dispatchers,
    list_enrichers,
    list_guardrails,
    list_routers,
    list_stages,
    list_workers,
    register_agent,
    register_dispatcher,
    register_enricher,
    register_guardrails,
    register_router,
    register_stage,
    register_worker,
    stage_registry,
)
from app.ai.substrate.stages.result import (
    StageError,
    StageResult,
)

# Backward compatibility alias
StageExecutionError = UnifiedStageExecutionError

__all__ = [
    # Core types
    "StageKind",
    "StageStatus",
    "StageOutput",
    "StageArtifact",
    "StageEvent",
    "StageContext",
    "Stage",
    "create_stage_context",
    # Pipeline context
    "PipelineContext",
    "extract_quality_mode",
    "extract_service",
    # Result types
    "StageResult",
    "StageError",
    "StageExecutionError",
    # Agent types
    "Action",
    "ActionType",
    "AgentResult",
    # Tool registry
    "ToolRegistry",
    "ToolRegistration",
    # Tool executor
    "ToolExecutor",
    "ToolExecutionError",
    "ToolNotFoundError",
    # Convenience functions
    "execute_action",
    "execute_actions",
    # Registry
    "StageRegistry",
    "stage_registry",
    # Shim decorators
    "register_worker",
    "register_dispatcher",
    "register_router",
    "register_enricher",
    "register_agent",
    "register_guardrails",
    "register_stage",
    # Shim getters
    "get_worker",
    "get_worker_or_raise",
    "get_dispatcher",
    "get_dispatcher_or_raise",
    "get_router",
    "get_router_or_raise",
    "get_enricher",
    "get_enricher_or_raise",
    "get_agent",
    "get_agent_or_raise",
    "get_guardrails",
    "get_guardrails_or_raise",
    "get_stage",
    # Shim listers
    "list_stages",
    "list_workers",
    "list_dispatchers",
    "list_routers",
    "list_enrichers",
    "list_agents",
    "list_guardrails",
    "get_enrichers_by_phase",
    "get_enrichers_by_domain",
    # Graph
    "UnifiedStageSpec",
    "UnifiedStageExecutionError",
    "UnifiedPipelineCancelled",
    "UnifiedStageGraph",
    "StageRunnerAdapter",
    "create_unified_spec_from_stage",
    # Orchestrator
    "PipelineOrchestrator",
    "SendStatus",
    "SendToken",
    "request_cancel",
    "is_cancel_requested",
    # Error handling
    "log_stage_error",
    "log_debug_failure",
    "safe_debug_log",
    "handle_provider_error",
    "handle_async_task_error",
    "create_error_context",
    "with_error_handling",
    "StageRunner",
    # Utility
    "clear_all_registries",
]
