"""Tests for worker registration via unified StageRegistry."""

import pytest

from app.ai.substrate.stages import (
    list_workers,
    register_worker,
    stage_registry,
)
from app.ai.substrate.stages.base import Stage, StageContext, StageKind, StageOutput


class TestWorkerRegistration:
    """Tests for worker registration."""

    def test_creation(self):
        """Test creating a worker via unified registry."""
        stage_registry.clear()

        @register_worker()
        class TestWorker(Stage):
            name = "test_worker"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        assert "test_worker" in stage_registry._registry


class TestWorkerRegistry:
    """Tests for worker registry functions."""

    def setup_method(self):
        """Clear registry before each test."""
        stage_registry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        stage_registry.clear()

    def test_register_single_worker(self):
        """Test registering a single worker."""

        @register_worker()
        class Worker1(Stage):
            name = "worker1"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        assert "worker1" in stage_registry._registry

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate raises error."""

        @register_worker()
        class DuplicateWorker(Stage):
            name = "duplicate_worker"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        # Trying to register again should fail
        with pytest.raises(ValueError, match="already registered"):
            @register_worker()
            class DuplicateWorker2(Stage):
                name = "duplicate_worker"
                kind = StageKind.WORK

                async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                    return StageOutput.ok()

    def test_get_returns_none_for_unknown(self):
        """Test that getting unknown worker returns None."""
        from app.ai.substrate.stages import get_stage
        assert get_stage("unknown_worker") is None

    def test_list_workers(self):
        """Test listing all workers (filtered by WORK kind)."""

        @register_worker()
        class Worker1(Stage):
            name = "list_test_worker1"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        @register_worker()
        class Worker2(Stage):
            name = "list_test_worker2"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        workers = list_workers()
        # Should include our registered workers
        assert "list_test_worker1" in workers
        assert "list_test_worker2" in workers

    def test_clear_registry(self):
        """Test clearing the registry."""

        @register_worker()
        class WorkerToClear(Stage):
            name = "worker_to_clear"
            kind = StageKind.WORK

            async def execute(self, ctx: StageContext) -> StageOutput:  # noqa: ARG002
                return StageOutput.ok()

        assert "worker_to_clear" in stage_registry._registry

        stage_registry.clear()

        assert "worker_to_clear" not in stage_registry._registry
