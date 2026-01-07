"""Core substrate protocols for stageflow architecture.

These protocols define a three-tier routing architecture:
- Router: Pre-kernel, lightweight, deterministic routing
- Dispatcher: Inside kernel, has full context, semantic selection
- Worker: Background processor, does NOT produce user-facing output
- Agent: Main interactor, produces message + actions + artifacts
"""

from .agent_protocol import Agent, StreamingAgent

__all__ = [
    # Routing
    "Router",
    "RouteRequest",
    "RouteDecision",
    # Dispatch
    "Dispatcher",
    "DispatchDecision",
    # Worker
    "Worker",
    "WorkerResult",
    # Agent
    "Agent",
    "StreamingAgent",
    # Common
    "ContextSnapshot",
    "PipelineEvent",
    "Mutation",
]
