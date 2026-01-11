"""Chat stages using stageflow.

These stages implement the Stage protocol for the chat pipeline.
"""

import logging
from datetime import datetime
from uuid import UUID

from stageflow import StageContext, StageKind, StageOutput

from app.ai.providers.factory import get_llm_provider
from app.config import get_settings

logger = logging.getLogger("chat")


class ChatRouterStage:
    """Route chat message to appropriate handler.

    For basic chat, this routes everything to the LLM stage.
    """

    name = "router"
    kind = StageKind.ROUTE

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute routing logic.

        For a simple chat bot, all messages go to the "chat" route.
        This can be extended to route to different behaviors based on intent.
        """
        input_text = ctx.snapshot.input_text or ""

        # Simple routing - all chat messages go to the general route
        route = "chat"
        confidence = 1.0

        logger.debug(
            f"Routing message: '{input_text[:50]}...' -> {route}",
            extra={"service": "chat", "route": route, "confidence": confidence},
        )

        return StageOutput.ok(
            route=route,
            confidence=confidence,
            input_text=input_text,
        )


class ChatLLMStage:
    """Generate LLM response for chat message.

    This stage calls the configured LLM provider to generate a response.
    """

    name = "llm"
    kind = StageKind.TRANSFORM

    def __init__(self, llm_provider=None):
        """Initialize the LLM stage.

        Args:
            llm_provider: Optional LLM provider instance. Defaults to factory provider.
        """
        self._llm_provider = llm_provider

    @property
    def llm_provider(self):
        """Get the LLM provider, lazily loading from factory if needed."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute LLM generation.

        Builds messages from conversation history and input,
        then calls the LLM to generate a response.
        """
        from stageflow.context import Message

        # Get input from context
        input_text = ctx.snapshot.input_text or ""
        messages = ctx.snapshot.messages or []

        # Get routing decision from router stage
        inputs = ctx.config.get("inputs")
        if inputs:
            route = inputs.get("route", "chat")
        else:
            route = "chat"

        # Build system prompt based on route
        system_prompt = self._get_system_prompt(route)

        # Prepare messages for LLM
        llm_messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages for context)
        for msg in messages[-20:]:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Add current user input
        if input_text:
            llm_messages.append({"role": "user", "content": input_text})

        try:
            settings = get_settings()
            model_id = settings.llm_model1_id

            # Call LLM
            response = await self.llm_provider.chat(
                messages=llm_messages,
                model=model_id,
                temperature=0.7,
                max_tokens=1024,
            )

            logger.info(
                "LLM response generated",
                extra={
                    "service": "chat",
                    "model": model_id,
                    "response_length": len(response),
                },
            )

            return StageOutput.ok(
                response=response,
                route=route,
                model=model_id,
            )

        except Exception as e:
            logger.error(
                f"LLM call failed: {e}",
                extra={"service": "chat", "error": str(e)},
                exc_info=True,
            )
            return StageOutput.fail(
                error=f"LLM call failed: {str(e)}",
                data={"error_type": type(e).__name__},
            )

    def _get_system_prompt(self, route: str) -> str:
        """Get system prompt based on route.

        Args:
            route: The routing decision from the router stage.

        Returns:
            System prompt string for the LLM.
        """
        prompts = {
            "chat": "You are a helpful, friendly AI assistant. Be concise and helpful in your responses.",
            "support": "You are a helpful support agent. Be empathetic, patient, and focus on solving the user's problem.",
            "sales": "You are a friendly sales assistant. Be helpful, not pushy. Focus on understanding the user's needs.",
        }
        return prompts.get(route, prompts["chat"])


class ChatLLMStreamStage:
    """Generate streaming LLM response for chat message.

    This stage streams tokens from the LLM and emits them as events.
    """

    name = "llm_stream"
    kind = StageKind.TRANSFORM

    def __init__(self, llm_provider=None):
        """Initialize the streaming LLM stage.

        Args:
            llm_provider: Optional LLM provider instance. Defaults to factory provider.
        """
        self._llm_provider = llm_provider
        self._full_response = ""

    @property
    def llm_provider(self):
        """Get the LLM provider, lazily loading from factory if needed."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Execute streaming LLM generation.

        Streams tokens from the LLM and emits chat.token events.
        """
        from stageflow.context import Message

        # Reset response buffer
        self._full_response = ""

        # Get input from context
        input_text = ctx.snapshot.input_text or ""
        messages = ctx.snapshot.messages or []

        # Get routing decision from router stage
        inputs = ctx.config.get("inputs")
        if inputs:
            route = inputs.get("route", "chat")
        else:
            route = "chat"

        # Build system prompt based on route
        system_prompt = self._get_system_prompt(route)

        # Prepare messages for LLM
        llm_messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (last 20 messages for context)
        for msg in messages[-20:]:
            llm_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Add current user input
        if input_text:
            llm_messages.append({"role": "user", "content": input_text})

        try:
            settings = get_settings()
            model_id = settings.llm_model1_id

            # Check if provider supports streaming
            if not hasattr(self.llm_provider, 'stream_chat'):
                # Fall back to non-streaming
                response = await self.llm_provider.chat(
                    messages=llm_messages,
                    model=model_id,
                    temperature=0.7,
                    max_tokens=1024,
                )
                return StageOutput.ok(
                    response=response,
                    route=route,
                    model=model_id,
                )

            # Stream the response
            async for chunk in self.llm_provider.stream_chat(
                messages=llm_messages,
                model=model_id,
                temperature=0.7,
                max_tokens=1024,
            ):
                self._full_response += chunk

                # Emit streaming token event
                ctx.emit_event("chat.token", {
                    "token": chunk,
                    "isComplete": False,
                })

            # Emit completion event
            ctx.emit_event("chat.complete", {
                "messageId": str(ctx.snapshot.interaction_id),
                "content": self._full_response,
                "sessionId": str(ctx.snapshot.session_id),
            })

            logger.info(
                "LLM streaming response complete",
                extra={
                    "service": "chat",
                    "model": model_id,
                    "response_length": len(self._full_response),
                },
            )

            return StageOutput.ok(
                response=self._full_response,
                route=route,
                model=model_id,
            )

        except Exception as e:
            logger.error(
                f"LLM streaming failed: {e}",
                extra={"service": "chat", "error": str(e)},
                exc_info=True,
            )
            return StageOutput.fail(
                error=f"LLM streaming failed: {str(e)}",
                data={"error_type": type(e).__name__},
            )

    def _get_system_prompt(self, route: str) -> str:
        """Get system prompt based on route.

        Args:
            route: The routing decision from the router stage.

        Returns:
            System prompt string for the LLM.
        """
        prompts = {
            "chat": "You are a helpful, friendly AI assistant. Be concise and helpful in your responses.",
            "support": "You are a helpful support agent. Be empathetic, patient, and focus on solving the user's problem.",
            "sales": "You are a friendly sales assistant. Be helpful, not pushy. Focus on understanding the user's needs.",
        }
        return prompts.get(route, prompts["chat"])


class ChatPersistStage:
    """Persist chat messages to the database.

    This stage saves user and assistant messages as Interaction records.
    """

    name = "persist"
    kind = StageKind.WORK

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Persist chat messages to database."""
        from app.database import get_session_context
        from app.models import Interaction

        inputs = ctx.config.get("inputs")
        if inputs:
            response = inputs.get("response")
        else:
            response = None

        if not response:
            return StageOutput.ok(persisted=False, reason="No response to persist")

        try:
            async with get_session_context() as db:
                interaction = Interaction(
                    id=ctx.snapshot.interaction_id,
                    session_id=ctx.snapshot.session_id,
                    role="assistant",
                    content=response,
                    created_at=datetime.utcnow(),
                )
                db.add(interaction)
                await db.commit()

            logger.info(
                "Chat message persisted",
                extra={
                    "service": "chat",
                    "interaction_id": str(ctx.snapshot.interaction_id),
                    "session_id": str(ctx.snapshot.session_id),
                },
            )

            return StageOutput.ok(
                persisted=True,
                interaction_id=str(ctx.snapshot.interaction_id),
            )

        except Exception as e:
            logger.error(
                f"Failed to persist chat message: {e}",
                extra={"service": "chat", "error": str(e)},
                exc_info=True,
            )
            return StageOutput.fail(
                error=f"Failed to persist: {str(e)}",
                data={"error_type": type(e).__name__},
            )


class ChatUserPersistStage:
    """Persist user chat message to the database.

    This stage saves the user's message as an Interaction record.
    """

    name = "user_persist"
    kind = StageKind.WORK

    async def execute(self, ctx: StageContext) -> StageOutput:
        """Persist user chat message to database."""
        from app.database import get_session_context
        from app.models import Interaction

        input_text = ctx.snapshot.input_text or ""
        if not input_text:
            return StageOutput.ok(persisted=False, reason="No input to persist")

        try:
            async with get_session_context() as db:
                interaction = Interaction(
                    id=ctx.snapshot.interaction_id,
                    session_id=ctx.snapshot.session_id,
                    role="user",
                    content=input_text,
                    created_at=datetime.utcnow(),
                )
                db.add(interaction)
                await db.commit()

            logger.info(
                "User message persisted",
                extra={
                    "service": "chat",
                    "interaction_id": str(ctx.snapshot.interaction_id),
                    "session_id": str(ctx.snapshot.session_id),
                },
            )

            return StageOutput.ok(
                persisted=True,
                interaction_id=str(ctx.snapshot.interaction_id),
            )

        except Exception as e:
            logger.error(
                f"Failed to persist user message: {e}",
                extra={"service": "chat", "error": str(e)},
                exc_info=True,
            )
            return StageOutput.fail(
                error=f"Failed to persist: {str(e)}",
                data={"error_type": type(e).__name__},
            )
