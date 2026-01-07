"""Simple registry for code-defined pipelines.

Replaces pipelines.json with a Python registry.
"""

from __future__ import annotations

from typing import Any


class PipelineRegistry:
    """Simple mapping of names to Pipeline instances with lazy registration."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Any] = {}
        self._registered = False

    def register(self, name: str, pipeline: Any) -> None:
        """Register a pipeline by name."""
        self._pipelines[name] = pipeline

    def get(self, name: str) -> Any:
        """Get a pipeline by name.

        If pipelines haven't been registered yet, registers all pipelines first.
        """
        if not self._registered:
            self._register_all()
        if name not in self._pipelines:
            raise KeyError(f"Pipeline '{name}' not found in registry")
        return self._pipelines[name]

    def list(self) -> list[str]:
        """List all registered pipeline names."""
        if not self._registered:
            self._register_all()
        return list(self._pipelines.keys())

    def __contains__(self, name: str) -> bool:
        if not self._registered:
            self._register_all()
        return name in self._pipelines

    def _register_all(self) -> None:
        """Register all pipelines (called lazily on first access)."""
        if self._registered:
            return

        # Import and call register_all_pipelines to register all pipelines
        from app.ai.pipelines import register_all_pipelines
        register_all_pipelines()

        self._registered = True


# Global registry instance
pipeline_registry = PipelineRegistry()


def register_pipeline(name: str) -> type:
    """Decorator to register a pipeline class."""

    def decorator(cls: type) -> type:
        pipeline_registry.register(name, cls())
        return cls

    return decorator


__all__ = ["PipelineRegistry", "pipeline_registry", "register_pipeline"]
