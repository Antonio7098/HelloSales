"""Unified StageRegistry for substrate architecture.

This module provides a single registry for all stage types:
- TRANSFORM stages (STT, TTS, LLM)
- ENRICH stages (Profile, Memory, Skills)
- ROUTE stages (Router, Dispatcher)
- GUARD stages (Guardrails, Policy)
- WORK stages (Assessment, Triage, Persist)
- AGENT stages (Coach, Interviewer)

The registry replaces 7 separate registries with one unified system
while maintaining backward compatibility through shim decorators.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Stage, StageKind


@dataclass(frozen=True)
class StageRegistration:
    """Registration information for a single stage.

    All components are registered as Stages with a StageKind discriminator.
    """
    name: str
    kind: StageKind
    stage_class: type[Stage]
    triggers: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


class StageRegistry:
    """Central registry for all stage implementations.

    This is a project-level singleton. Concrete projects (like
    Eloquence) register their own stages. Substrate only
    provides the registration mechanism.

    The registry supports:
    - Single unified registration with kind discriminator
    - Lookup by name, kind, or trigger
    - Backward compatibility shims for old registry APIs
    """

    _registry: dict[str, StageRegistration] = {}
    _kind_index: dict[StageKind, list[str]] = {}
    _class_index: dict[str, str] = {}  # Maps class name -> stage name

    @classmethod
    def register(
        cls,
        kind: StageKind,
        *,
        name: str | None = None,
        triggers: list[str] | None = None,
        dependencies: list[str] | None = None,
        description: str = "",
    ) -> Callable[[type[Stage]], type[Stage]]:
        """Decorator to register a stage class.

        Args:
            kind: StageKind discriminator (required)
            name: Optional stage name (defaults to class name)
            triggers: Optional trigger list for WORK stages
            dependencies: Optional stage dependencies
            description: Human-readable description

        Returns:
            Decorator that registers the stage class

        Usage:
            @register(kind=StageKind.WORK, triggers=["parallel"])
            class AssessmentStage(Stage):
                name = "assessment"
                kind = StageKind.WORK
                ...
        """
        def decorator(stage_class: type[Stage]) -> type[Stage]:
            stage_name = name or getattr(stage_class, "name", None) or stage_class.__name__

            if stage_name in cls._registry:
                existing = cls._registry[stage_name]
                raise ValueError(
                    f"Stage '{stage_name}' is already registered to class "
                    f"'{existing.stage_class.__name__}' as {existing.kind.value}. "
                    f"Cannot re-register to '{stage_class.__name__}' as {kind.value}."
                )

            registration = StageRegistration(
                name=stage_name,
                kind=kind,
                stage_class=stage_class,
                triggers=tuple(triggers) if triggers else (),
                dependencies=tuple(dependencies) if dependencies else (),
                description=description,
            )

            cls._registry[stage_name] = registration

            # Index by kind for fast lookup
            if kind not in cls._kind_index:
                cls._kind_index[kind] = []
            cls._kind_index[kind].append(stage_name)

            # Index by class name for backward compatibility
            cls._class_index[stage_class.__name__] = stage_name

            return stage_class

        return decorator

    @classmethod
    def get(cls, name: str) -> type[Stage] | None:
        """Get a stage class by name.

        Args:
            name: The stage identifier

        Returns:
            The stage class or None if not found
        """
        registration = cls._registry.get(name)
        return registration.stage_class if registration else None

    @classmethod
    def get_or_raise(cls, name: str) -> type[Stage]:
        """Get a stage class by name or class name, raising if not found.

        Args:
            name: The stage identifier (name) or class name

        Returns:
            The stage class

        Raises:
            KeyError: If stage is not registered
        """
        # Try direct lookup first
        registration = cls._registry.get(name)
        if registration is not None:
            return registration.stage_class

        # Try class name lookup for backward compatibility
        stage_name = cls._class_index.get(name)
        if stage_name is not None:
            registration = cls._registry.get(stage_name)
            if registration is not None:
                return registration.stage_class

        available = cls.list()
        raise KeyError(
            f"Stage '{name}' not found in registry. "
            f"Available stages: {available}"
        )

    @classmethod
    def get_registration(cls, name: str) -> StageRegistration | None:
        """Get the full registration for a stage.

        Args:
            name: The stage identifier

        Returns:
            StageRegistration or None if not found
        """
        return cls._registry.get(name)

    @classmethod
    def list(cls) -> list[str]:
        """List all registered stage names.

        Returns:
            List of stage identifiers
        """
        return list(cls._registry.keys())

    @classmethod
    def list_with_details(cls) -> list[dict[str, str | tuple[str, ...]]]:
        """List all stages with their details.

        Returns:
            List of dicts with name, kind, triggers, and description
        """
        return [
            {
                "name": reg.name,
                "kind": reg.kind.value,
                "triggers": reg.triggers,
                "description": reg.description,
            }
            for reg in cls._registry.values()
        ]

    @classmethod
    def get_by_kind(cls, kind: StageKind) -> list[type[Stage]]:
        """Get all stages of a specific kind.

        Args:
            kind: The StageKind to filter by

        Returns:
            List of stage classes of this kind
        """
        names = cls._kind_index.get(kind, [])
        return [cls._registry[n].stage_class for n in names if n in cls._registry]

    @classmethod
    def get_by_trigger(cls, trigger: str) -> list[type[Stage]]:
        """Get all stages that handle a specific trigger.

        Args:
            trigger: The trigger type ("parallel", "pre_agent", "post_turn", etc.)

        Returns:
            List of stage classes that handle this trigger
        """
        return [
            reg.stage_class for reg in cls._registry.values()
            if trigger in reg.triggers
        ]

    @classmethod
    def get_all(cls) -> dict[str, StageRegistration]:
        """Get all registrations.

        Returns:
            Dictionary mapping stage name to registration
        """
        return cls._registry.copy()

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a stage is registered.

        Args:
            name: The stage identifier

        Returns:
            True if registered, False otherwise
        """
        return name in cls._registry

    @classmethod
    def register_alias(cls, alias_name: str, target_name: str) -> None:
        """Register a class name alias that points to an existing stage.

        This allows backward compatibility by supporting multiple class names
        for the same stage (e.g., 'ChatContextBuildStage' -> 'voice_context_build').

        Args:
            alias_name: The alias class name to register
            target_name: The existing stage name to alias to

        Raises:
            ValueError: If target stage doesn't exist
        """
        if target_name not in cls._registry:
            raise ValueError(f"Cannot create alias: target stage '{target_name}' not found")

        # Add alias to class index
        cls._class_index[alias_name] = target_name

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations.

        WARNING: This is primarily for testing. Do not call
        in production unless you know what you're doing.
        """
        cls._registry.clear()
        cls._kind_index.clear()
        cls._class_index.clear()


# Global registry instance
stage_registry = StageRegistry()


# Backward compatibility shims for old registry APIs
# These delegate to the unified StageRegistry with appropriate StageKind

def register_worker(
    name: str | None = None,
    *,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for WorkerRegistry.register - delegates to StageKind.WORK."""
    from app.ai.substrate.stages.base import StageKind
    return stage_registry.register(
        name=name,
        kind=StageKind.WORK,
        description=description,
    )


def register_dispatcher(
    name: str | None = None,
    *,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for DispatcherRegistry.register - delegates to StageKind.ROUTE."""
    from app.ai.substrate.stages.base import StageKind
    return stage_registry.register(
        name=name,
        kind=StageKind.ROUTE,
        description=description,
    )


def register_router(
    name: str | None = None,
    *,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for RouterRegistry.register - delegates to StageKind.ROUTE."""
    from app.ai.substrate.stages.base import StageKind
    return stage_registry.register(
        name=name,
        kind=StageKind.ROUTE,
        description=description,
    )


def register_enricher(
    name: str | None = None,
    *,
    phases: list[str] | None = None,
    _domains: list[str] | None = None,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for EnricherRegistry.register - delegates to StageKind.ENRICH."""
    from app.ai.substrate.stages.base import StageKind
    # Map phases to triggers for unified registry
    triggers = phases or []
    return stage_registry.register(
        name=name,
        kind=StageKind.ENRICH,
        triggers=triggers,
        description=description,
    )


def register_agent(
    name: str | None = None,
    *,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for AgentRegistry.register - delegates to StageKind.AGENT."""
    from app.ai.substrate.stages.base import StageKind
    return stage_registry.register(
        name=name,
        kind=StageKind.AGENT,
        description=description,
    )


def register_guardrails(
    name: str | None = None,
    *,
    checkpoints: list[str] | None = None,
    description: str = "",
) -> Callable[[type], type]:
    """Shim for GuardrailsRegistry.register - delegates to StageKind.GUARD."""
    from app.ai.substrate.stages.base import StageKind
    # Map checkpoints to triggers for unified registry
    triggers = checkpoints or []
    return stage_registry.register(
        name=name,
        kind=StageKind.GUARD,
        triggers=triggers,
        description=description,
    )


def register_stage(
    name: str | None = None,
    *,
    alias: str | None = None,
    kind: StageKind | None = None,
) -> Callable[[type], type]:
    """Shim for StageRegistry.register - delegates to unified register().

    Args:
        name: Optional stage name (defaults to class name or name attribute)
        alias: Optional alias for the stage
        kind: Optional StageKind (defaults to TRANSFORM for backward compat)

    Note: For explicit StageKind, use register() directly.
    """
    from .base import StageKind

    actual_kind = kind or StageKind.TRANSFORM

    def decorator(stage_class: type) -> type:
        stage_name = name or getattr(stage_class, "name", None) or stage_class.__name__
        registered = stage_registry.register(
            kind=actual_kind,
            name=name,
            description="",
        )(stage_class)
        # Also register alias if provided (after main registration)
        if alias and alias != stage_name:
            reg = stage_registry._registry.get(stage_name)
            if reg:
                stage_registry._registry[alias] = reg
        return registered

    return decorator


# Convenience functions matching old registry APIs

def get_worker(name: str) -> type | None:
    """Shim for WorkerRegistry.get."""
    return stage_registry.get(name)


def get_worker_or_raise(name: str) -> type:
    """Shim for WorkerRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_dispatcher(name: str) -> type | None:
    """Shim for DispatcherRegistry.get."""
    return stage_registry.get(name)


def get_dispatcher_or_raise(name: str) -> type:
    """Shim for DispatcherRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_router(name: str) -> type | None:
    """Shim for RouterRegistry.get."""
    return stage_registry.get(name)


def get_router_or_raise(name: str) -> type:
    """Shim for RouterRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_enricher(name: str) -> type | None:
    """Shim for EnricherRegistry.get."""
    return stage_registry.get(name)


def get_enricher_or_raise(name: str) -> type:
    """Shim for EnricherRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_agent(name: str) -> type | None:
    """Shim for AgentRegistry.get."""
    return stage_registry.get(name)


def get_agent_or_raise(name: str) -> type:
    """Shim for AgentRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_guardrails(name: str) -> type | None:
    """Shim for GuardrailsRegistry.get."""
    return stage_registry.get(name)


def get_guardrails_or_raise(name: str) -> type:
    """Shim for GuardrailsRegistry.get_or_raise."""
    return stage_registry.get_or_raise(name)


def get_stage(name: str) -> type | None:
    """Shim for StageRegistry.get."""
    return stage_registry.get(name)


def list_stages() -> list[str]:
    """Shim for StageRegistry.list."""
    return stage_registry.list()


def list_workers() -> list[str]:
    """Shim for WorkerRegistry.list - returns WORK kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.WORK]


def list_dispatchers() -> list[str]:
    """Shim for DispatcherRegistry.list - returns ROUTE kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.ROUTE]


def list_routers() -> list[str]:
    """Shim for RouterRegistry.list - returns ROUTE kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.ROUTE]


def list_enrichers() -> list[str]:
    """Shim for EnricherRegistry.list - returns ENRICH kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.ENRICH]


def get_enrichers_by_phase(phase: str) -> list[type]:
    """Get all enrichers that run in a specific phase.

    Maps to stages with matching trigger (phase).
    """
    return stage_registry.get_by_trigger(phase)


def get_enrichers_by_domain(_domain: str) -> list[type]:
    """Get all enrichers that apply to a specific domain.

    Note: Unified registry uses triggers only. This returns all ENRICH stages.
    """
    from app.ai.substrate.stages.base import StageKind
    return [reg.stage_class for reg in stage_registry._registry.values()
            if reg.kind == StageKind.ENRICH]


def list_agents() -> list[str]:
    """Shim for AgentRegistry.list - returns AGENT kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.AGENT]


def list_guardrails() -> list[str]:
    """Shim for GuardrailsRegistry.list - returns GUARD kind stages."""
    from app.ai.substrate.stages.base import StageKind
    return [reg.name for reg in stage_registry._registry.values()
            if reg.kind == StageKind.GUARD]


def clear_all_registries() -> None:
    """Clear all registries - useful for testing."""
    stage_registry.clear()


__all__ = [
    "StageRegistration",
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
    "get_dispatcher",
    "get_router",
    "get_enricher",
    "get_agent",
    "get_guardrails",
    "get_stage",
    # Shim listers
    "list_stages",
    "list_workers",
    "list_dispatchers",
    "list_routers",
    "list_enrichers",
    "list_agents",
    "list_guardrails",
    # Utility
    "clear_all_registries",
]
