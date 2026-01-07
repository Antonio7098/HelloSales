"""Tests for GuardrailsRegistry."""
import pytest

from app.ai.substrate.policy.guardrails_registry import (
    GuardrailsRegistration,
    GuardrailsRegistry,
    get_guardrails,
    get_guardrails_by_checkpoint,
    get_guardrails_or_raise,
    list_guardrails,
    list_guardrails_with_details,
    register_guardrails,
)


class TestGuardrailsRegistration:
    """Tests for GuardrailsRegistration dataclass."""

    def test_creation(self):
        """Test creating a GuardrailsRegistration."""
        class DummyGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        registration = GuardrailsRegistration(
            name="test_guardrails",
            guardrails_class=DummyGuardrails,
            checkpoints=("pre_llm", "pre_action"),
            description="Test guardrails",
        )

        assert registration.name == "test_guardrails"
        assert registration.guardrails_class is DummyGuardrails
        assert registration.checkpoints == ("pre_llm", "pre_action")
        assert registration.description == "Test guardrails"


class TestGuardrailsRegistry:
    """Tests for GuardrailsRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        GuardrailsRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        GuardrailsRegistry.clear()

    def test_register_single_guardrails(self):
        """Test registering a single guardrails."""

        @register_guardrails(name="test_guardrails", description="Test guardrails")
        class TestGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        assert GuardrailsRegistry.has("test_guardrails")
        assert get_guardrails("test_guardrails") is not None

    def test_register_with_checkpoints(self):
        """Test registering guardrails with checkpoints."""

        @register_guardrails(
            name="content_moderation",
            checkpoints=["pre_llm", "pre_action"],
            description="Content moderation"
        )
        class ContentModerationGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        assert GuardrailsRegistry.has("content_moderation")
        details = GuardrailsRegistry.list_with_details()
        assert len(details) == 1
        assert details[0]["checkpoints"] == ("pre_llm", "pre_action")

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate guardrails raises error."""

        @register_guardrails(name="duplicate_guardrails", description="First")
        class Guardrails1:
            async def evaluate(self, checkpoint, context):
                pass

        with pytest.raises(ValueError, match="already registered"):
            register_guardrails(name="duplicate_guardrails", description="Second")(Guardrails1)

    def test_get_returns_none_for_unknown(self):
        """Test that get returns None for unknown guardrails."""
        assert get_guardrails("unknown_guardrails") is None

    def test_get_or_raise_raises_for_unknown(self):
        """Test that get_or_raise raises for unknown guardrails."""
        with pytest.raises(KeyError):
            get_guardrails_or_raise("unknown_guardrails")

    def test_list_guardrails(self):
        """Test listing all guardrails."""
        @register_guardrails(name="guardrails1")
        class Guardrails1:
            async def evaluate(self, checkpoint, context):
                pass

        @register_guardrails(name="guardrails2")
        class Guardrails2:
            async def evaluate(self, checkpoint, context):
                pass

        guardrails = list_guardrails()
        assert len(guardrails) == 2
        assert "guardrails1" in guardrails
        assert "guardrails2" in guardrails

    def test_list_guardrails_with_details(self):
        """Test listing guardrails with details."""
        @register_guardrails(
            name="detailed_guardrails",
            checkpoints=["pre_llm"],
            description="A detailed guardrails"
        )
        class DetailedGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        details = list_guardrails_with_details()
        assert len(details) == 1
        assert details[0]["name"] == "detailed_guardrails"
        assert details[0]["checkpoints"] == ("pre_llm",)
        assert details[0]["description"] == "A detailed guardrails"

    def test_get_by_checkpoint(self):
        """Test getting guardrails by checkpoint."""
        @register_guardrails(name="llm_guardrails", checkpoints=["pre_llm"])
        class LLmGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        @register_guardrails(name="action_guardrails", checkpoints=["pre_action"])
        class ActionGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        @register_guardrails(name="multi_guardrails", checkpoints=["pre_llm", "pre_action"])
        class MultiGuardrails:
            async def evaluate(self, checkpoint, context):
                pass

        pre_llm_guardrails = get_guardrails_by_checkpoint("pre_llm")
        assert len(pre_llm_guardrails) == 2
        pre_llm_names = [g.__name__ for g in pre_llm_guardrails]
        assert "LLmGuardrails" in pre_llm_names
        assert "MultiGuardrails" in pre_llm_names

        pre_action_guardrails = get_guardrails_by_checkpoint("pre_action")
        assert len(pre_action_guardrails) == 2

        pre_persist_guardrails = get_guardrails_by_checkpoint("pre_persist")
        assert len(pre_persist_guardrails) == 0

    def test_get_all(self):
        """Test getting all registrations."""
        @register_guardrails(name="guardrails1")
        class Guardrails1:
            async def evaluate(self, checkpoint, context):
                pass

        all_reg = GuardrailsRegistry.get_all()
        assert "guardrails1" in all_reg
        assert isinstance(all_reg["guardrails1"], GuardrailsRegistration)

    def test_clear(self):
        """Test clearing the registry."""
        @register_guardrails(name="guardrails_to_clear")
        class GuardrailsToClear:
            async def evaluate(self, checkpoint, context):
                pass

        assert GuardrailsRegistry.has("guardrails_to_clear")
        GuardrailsRegistry.clear()
        assert not GuardrailsRegistry.has("guardrails_to_clear")

    def test_unregister(self):
        """Test unregistering a guardrails."""
        @register_guardrails(name="guardrails_to_remove")
        class GuardrailsToRemove:
            async def evaluate(self, checkpoint, context):
                pass

        assert GuardrailsRegistry.has("guardrails_to_remove")
        GuardrailsRegistry.unregister("guardrails_to_remove")
        assert not GuardrailsRegistry.has("guardrails_to_remove")

    def test_unregister_unknown_raises_error(self):
        """Test that unregistering unknown raises error."""
        with pytest.raises(KeyError):
            GuardrailsRegistry.unregister("unknown_guardrails")
