"""Settings/config WebSocket handlers for runtime configuration."""

import logging
from typing import Any

from fastapi import WebSocket

from app.api.ws.manager import ConnectionManager, ModelChoice, PipelineMode
from app.api.ws.router import get_router
from app.config import get_settings

logger = logging.getLogger("settings")

router = get_router()


@router.handler("settings.setPipelineMode")
async def handle_set_pipeline_mode(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Set the pipeline mode for this connection.

    Expected payload:
    {
        "mode": "fast" | "accurate" | "accurate_filler" | null
    }

    Sending null resets to server default.

    Sends:
    - settings.pipelineModeSet (confirmation)
    - error (if invalid mode)
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before changing settings",
                },
            },
        )
        return

    mode_raw = payload.get("mode")

    # Validate mode
    valid_modes: set[PipelineMode | None] = {
        "fast",
        "accurate",
        "accurate_filler",
        None,
    }
    if mode_raw not in valid_modes:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid pipeline mode: {mode_raw}. Must be 'fast', 'accurate', 'accurate_filler', or null.",
                },
            },
        )
        return

    mode: PipelineMode | None = mode_raw

    # Set the mode
    manager.set_pipeline_mode(websocket, mode)

    # Get effective mode (for response)
    effective_mode = manager.get_pipeline_mode(websocket)

    await manager.send_message(
        websocket,
        {
            "type": "settings.pipelineModeSet",
            "payload": {
                "mode": mode,
                "effectiveMode": effective_mode,
                "serverDefault": get_settings().pipeline_mode,
            },
        },
    )

    logger.info(
        "Pipeline mode updated",
        extra={
            "service": "settings",
            "user_id": str(conn.user_id) if conn.user_id else None,
            "mode": mode,
            "effective_mode": effective_mode,
        },
    )


@router.handler("settings.getPipelineMode")
async def handle_get_pipeline_mode(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Get the current pipeline mode for this connection.

    Sends:
    - settings.pipelineMode
    """
    conn = manager.get_connection(websocket)
    if not conn:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_CONNECTED",
                    "message": "Connection not found",
                },
            },
        )
        return

    effective_mode = manager.get_pipeline_mode(websocket)

    await manager.send_message(
        websocket,
        {
            "type": "settings.pipelineMode",
            "payload": {
                "mode": conn.pipeline_mode,  # Connection override (may be None)
                "effectiveMode": effective_mode,
                "serverDefault": get_settings().pipeline_mode,
            },
        },
    )


@router.handler("settings.setModelChoice")
async def handle_set_model_choice(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Set the model choice for this connection.

    Expected payload:
    {
        "choice": "model1" | "model2" | null
    }

    Sending null resets to server default.

    Sends:
    - settings.modelChoiceSet (confirmation)
    - error (if invalid choice)
    """
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_AUTHENTICATED",
                    "message": "Must authenticate before changing settings",
                },
            },
        )
        return

    choice_raw = payload.get("choice")

    # Validate choice
    valid_choices: set[ModelChoice | None] = {"model1", "model2", None}
    if choice_raw not in valid_choices:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": f"Invalid model choice: {choice_raw}. Must be 'model1', 'model2', or null.",
                },
            },
        )
        return

    choice: ModelChoice | None = choice_raw

    # Set the choice
    manager.set_model_choice(websocket, choice)

    # Get effective values
    settings = get_settings()
    effective_choice = manager.get_model_choice(websocket)
    effective_model_id = manager.get_model_id(websocket)

    await manager.send_message(
        websocket,
        {
            "type": "settings.modelChoiceSet",
            "payload": {
                "choice": choice,
                "effectiveChoice": effective_choice,
                "effectiveModelId": effective_model_id,
                "serverDefault": settings.llm_model_choice,
                "model1Id": settings.llm_model1_id,
                "model2Id": settings.llm_model2_id,
            },
        },
    )

    logger.info(
        "Model choice updated",
        extra={
            "service": "settings",
            "user_id": str(conn.user_id) if conn.user_id else None,
            "choice": choice,
            "effective_choice": effective_choice,
            "effective_model_id": effective_model_id,
        },
    )


@router.handler("settings.getModelChoice")
async def handle_get_model_choice(
    websocket: WebSocket,
    _payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Get the current model choice for this connection.

    Sends:
    - settings.modelChoice
    """
    conn = manager.get_connection(websocket)
    if not conn:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "NOT_CONNECTED",
                    "message": "Connection not found",
                },
            },
        )
        return

    settings = get_settings()
    effective_choice = manager.get_model_choice(websocket)
    effective_model_id = manager.get_model_id(websocket)

    await manager.send_message(
        websocket,
        {
            "type": "settings.modelChoice",
            "payload": {
                "choice": conn.model_choice,  # Connection override (may be None)
                "effectiveChoice": effective_choice,
                "effectiveModelId": effective_model_id,
                "serverDefault": settings.llm_model_choice,
                "model1Id": settings.llm_model1_id,
                "model2Id": settings.llm_model2_id,
            },
        },
    )
