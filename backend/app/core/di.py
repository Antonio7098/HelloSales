"""Dependency injection container."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.ai.providers import (
    get_llm_provider,
    get_stt_provider,
    get_tts_provider,
)
from app.ai.providers.base import (
    LLMProvider,
    STTProvider,
    TTSProvider,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.domains.chat.service import ChatService


@dataclass
class Container:
    """DI container for AI providers."""

    llm_provider: LLMProvider
    stt_provider: STTProvider
    tts_provider: TTSProvider

    def create_chat_service(self, db: "AsyncSession") -> "ChatService":
        """Create a ChatService instance with the given database session.

        Args:
            db: SQLAlchemy async session

        Returns:
            ChatService instance
        """
        from app.domains.chat.service import ChatService

        return ChatService(
            db=db,
            llm_provider=self.llm_provider,
        )


def get_container() -> Container:
    """Get the DI container with provider instances."""
    return Container(
        llm_provider=get_llm_provider(),
        stt_provider=get_stt_provider(),
        tts_provider=get_tts_provider(),
    )
