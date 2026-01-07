import logging
import uuid
from typing import Any

from fastapi import WebSocket

from app.ai.substrate import PipelineEventLogger
from app.ai.substrate.stages import request_cancel
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.database import get_session_context
from app.models.observability import PipelineRun

logger = logging.getLogger("pipeline")

router = get_router()


@router.handler("pipeline.cancel_requested")
async def handle_pipeline_cancel_requested(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    conn = manager.get_connection(websocket)
    if not conn or not conn.authenticated or not conn.user_id:
        return

    pipeline_run_raw = payload.get("pipeline_run_id") or payload.get("pipelineRunId")
    if not pipeline_run_raw:
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "pipeline_run_id is required",
                },
            },
        )
        return

    try:
        pipeline_run_id = uuid.UUID(str(pipeline_run_raw))
    except (ValueError, TypeError):
        await manager.send_message(
            websocket,
            {
                "type": "error",
                "payload": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Invalid pipeline_run_id",
                },
            },
        )
        return

    request_id_raw = payload.get("request_id") or payload.get("requestId")
    try:
        request_id = uuid.UUID(str(request_id_raw)) if request_id_raw else uuid.uuid4()
    except (ValueError, TypeError):
        request_id = uuid.uuid4()

    async with get_session_context() as db:
        event_logger = PipelineEventLogger(db)

        run = await db.get(PipelineRun, pipeline_run_id)
        if run is None:
            return

        if run.user_id is not None and run.user_id != conn.user_id:
            await manager.send_message(
                websocket,
                {
                    "type": "error",
                    "payload": {
                        "code": "FORBIDDEN",
                        "message": "Cannot cancel a run that does not belong to the current user",
                    },
                },
            )
            return

        user_id = run.user_id
        session_id = run.session_id
        org_id = run.org_id
        run_mode: str | None = getattr(run, "mode", None)
        run_quality_mode: str | None = getattr(run, "quality_mode", None)
        run_status: str | None = getattr(run, "status", None)

        cancel_success = request_cancel(pipeline_run_id)
        canceled_now = False

        await event_logger.emit(
            pipeline_run_id=pipeline_run_id,
            type="pipeline.cancel_requested",
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            data=None,
        )

        if not cancel_success and (run.status not in ("completed", "failed", "canceled")):
            run.status = "canceled"
            run.success = False
            run.error = "canceled"
            run_status = "canceled"
            canceled_now = True
            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="pipeline.canceled",
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data=None,
            )

            await event_logger.emit(
                pipeline_run_id=pipeline_run_id,
                type="stage.pipeline.canceled",
                request_id=request_id,
                session_id=session_id,
                user_id=user_id,
                org_id=org_id,
                data={"mode": run_mode, "quality_mode": run_quality_mode},
            )

    metadata: dict[str, Any] = {
        "requestId": str(request_id),
        "pipelineRunId": str(pipeline_run_id),
        "request_id": str(request_id),
        "pipeline_run_id": str(pipeline_run_id),
    }
    if run_mode is not None:
        metadata["mode"] = run_mode
    if run_quality_mode is not None:
        metadata["quality_mode"] = run_quality_mode
    if run_status is not None:
        metadata["status"] = run_status

    if canceled_now:
        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": "pipeline",
                    "status": "canceled",
                    "metadata": metadata,
                },
            },
        )
    elif run_status in ("completed", "failed", "canceled"):
        await manager.send_message(
            websocket,
            {
                "type": "status.update",
                "payload": {
                    "service": "pipeline",
                    "status": run_status,
                    "metadata": metadata,
                },
            },
        )
