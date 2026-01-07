"""Provider registry for self-registration of AI service providers.

This module provides a registry system that allows providers to register
themselves at import time. This eliminates the need for a central factory
to know about all available providers.

Usage:
    # In provider module (e.g., app/ai/providers/llm/groq.py):
    from app.ai.providers.registry import register_llm_provider

    @register_llm_provider
    class GroqProvider(LLMProvider):
        ...

    # In factory.py or consumer code:
    from app.ai.providers.registry import get_llm_provider, get_stt_provider, get_tts_provider
"""

from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from app.ai.providers.base import LLMProvider, STTProvider, TTSProvider

# Type variables for generic registry
T = TypeVar("T")
LLM = TypeVar("LLM", bound="LLMProvider")
STT = TypeVar("STT", bound="STTProvider")
TTS = TypeVar("TTS", bound="TTSProvider")

# Registry dictionaries - populated by decorators at import time
_llm_registry: dict[str, type["LLMProvider"]] = {}
_stt_registry: dict[str, type["STTProvider"]] = {}
_tts_registry: dict[str, type["TTSProvider"]] = {}


class ProviderRegistryError(Exception):
    """Base error for provider registry issues."""
    pass


class ProviderNotFoundError(ProviderRegistryError):
    """Raised when a requested provider is not registered."""
    pass


class DuplicateProviderError(ProviderRegistryError):
    """Raised when trying to register a provider with a name that's already taken."""
    pass


def register_llm_provider(provider_class: type[LLM]) -> type[LLM]:
    """Register an LLM provider class.

    Args:
        provider_class: A subclass of LLMProvider with a `name` property.

    Returns:
        The provider class (unchanged).

    Raises:
        DuplicateProviderError: If a provider with this name is already registered.
    """
    # Get the name by calling the property getter on the class itself
    # This works because properties on classes can be called to get the value
    name = getattr(provider_class, "name", None)
    if name is None:
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} is missing required 'name' property"
        )
    # If it's a property descriptor, we need to extract the string value
    if isinstance(name, property):
        # Properties on the class are descriptors; we need to get the fget
        if name.fget is None:
            raise ProviderRegistryError(
                f"Provider {provider_class.__name__} has a 'name' property without a getter"
            )
        # Call the property getter to get the string value
        name = name.fget(provider_class)
    elif callable(name):
        # Some providers might define name as a class method
        name = name()
    elif not isinstance(name, str):
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} has an invalid 'name' property type: {type(name)}"
        )

    if name in _llm_registry:
        raise DuplicateProviderError(
            f"LLM provider '{name}' is already registered"
        )
    _llm_registry[name] = provider_class
    return provider_class


def register_stt_provider(provider_class: type[STT]) -> type[STT]:
    """Register an STT provider class.

    Args:
        provider_class: A subclass of STTProvider with a `name` property.

    Returns:
        The provider class (unchanged).

    Raises:
        DuplicateProviderError: If a provider with this name is already registered.
    """
    name = getattr(provider_class, "name", None)
    if name is None:
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} is missing required 'name' property"
        )
    # If it's a property descriptor, we need to extract the string value
    if isinstance(name, property):
        if name.fget is None:
            raise ProviderRegistryError(
                f"Provider {provider_class.__name__} has a 'name' property without a getter"
            )
        name = name.fget(provider_class)
    elif callable(name):
        name = name()
    elif not isinstance(name, str):
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} has an invalid 'name' property type: {type(name)}"
        )

    if name in _stt_registry:
        raise DuplicateProviderError(
            f"STT provider '{name}' is already registered"
        )
    _stt_registry[name] = provider_class
    return provider_class


def register_tts_provider(provider_class: type[TTS]) -> type[TTS]:
    """Register a TTS provider class.

    Args:
        provider_class: A subclass of TTSProvider with a `name` property.

    Returns:
        The provider class (unchanged).

    Raises:
        DuplicateProviderError: If a provider with this name is already registered.
    """
    name = getattr(provider_class, "name", None)
    if name is None:
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} is missing required 'name' property"
        )
    # If it's a property descriptor, we need to extract the string value
    if isinstance(name, property):
        if name.fget is None:
            raise ProviderRegistryError(
                f"Provider {provider_class.__name__} has a 'name' property without a getter"
            )
        name = name.fget(provider_class)
    elif callable(name):
        name = name()
    elif not isinstance(name, str):
        raise ProviderRegistryError(
            f"Provider {provider_class.__name__} has an invalid 'name' property type: {type(name)}"
        )

    if name in _tts_registry:
        raise DuplicateProviderError(
            f"TTS provider '{name}' is already registered"
        )
    _tts_registry[name] = provider_class
    return provider_class


def get_registered_llm_providers() -> dict[str, type["LLMProvider"]]:
    """Get a copy of the registered LLM providers."""
    return _llm_registry.copy()


def get_registered_stt_providers() -> dict[str, type["STTProvider"]]:
    """Get a copy of the registered STT providers."""
    return _stt_registry.copy()


def get_registered_tts_providers() -> dict[str, type["TTSProvider"]]:
    """Get a copy of the registered TTS providers."""
    return _tts_registry.copy()


def is_llm_provider_registered(name: str) -> bool:
    """Check if an LLM provider is registered."""
    return name in _llm_registry


def is_stt_provider_registered(name: str) -> bool:
    """Check if an STT provider is registered."""
    return name in _stt_registry


def is_tts_provider_registered(name: str) -> bool:
    """Check if a TTS provider is registered."""
    return name in _tts_registry
