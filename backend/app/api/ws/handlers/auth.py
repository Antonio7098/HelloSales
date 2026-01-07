"""Authentication WebSocket handler - Enterprise Edition (WorkOS only)."""

import asyncio
import logging
import uuid
from typing import Any
from uuid import uuid4

from fastapi import WebSocket
from sqlalchemy import select

from app.ai.providers.factory import get_llm_provider
from app.api.ws.manager import ConnectionManager
from app.api.ws.router import get_router
from app.auth.identity import IdentityTokenError, verify_identity_token
from app.database import get_session_context
from app.domains.assessment.meta_summary import MetaSummaryService
from app.domains.assessment.service import AssessmentService
from app.domains.assessment.triage import TriageService
from app.domains.organization.service import OrganizationService
from app.logging_config import set_request_context
from app.models import Session, User

logger = logging.getLogger("auth")
router = get_router()


@router.handler("auth")
async def handle_auth(
    websocket: WebSocket,
    payload: dict[str, Any],
    manager: ConnectionManager,
) -> None:
    """Handle authentication message - WorkOS only.

    Expected payload:
        {
            "token": "<workos_jwt>"
        }

    Responses:
        - auth.success: { userId, sessionId, orgId }
        - auth.error: { code, message }
    """
    token = payload.get("token")
    platform_raw = payload.get("platform")
    requested_session_id_raw = payload.get("sessionId")

    if not token:
        logger.warning(
            "Auth attempt without token",
            extra={"service": "auth", "ws_id": id(websocket)},
        )
        await manager.send_message(
            websocket,
            {
                "type": "auth.error",
                "payload": {
                    "code": "MISSING_TOKEN",
                    "message": "Authentication token is required",
                },
            },
        )
        return

    try:
        identity = await verify_identity_token(token)
        subject = identity.subject
        email = identity.email

        # Enterprise: org_id is required
        org_id_value: str | None = identity.org_id
        if not org_id_value:
            await manager.send_message(
                websocket,
                {
                    "type": "auth.error",
                    "payload": {
                        "code": "MISSING_ORG_ID",
                        "message": "Enterprise token must include organization context",
                    },
                },
            )
            return

        raw_claims = identity.raw_claims or {}
        role_raw = raw_claims.get("role")
        role = str(role_raw) if role_raw is not None else None
        permissions_raw = raw_claims.get("permissions")
        permissions = permissions_raw if isinstance(permissions_raw, dict) else None

        # Set request context for logging
        request_id = str(uuid4())
        set_request_context(request_id=request_id)

        logger.info(
            "WorkOS JWT verified",
            extra={
                "service": "auth",
                "auth_provider": identity.provider,
                "auth_subject": subject,
                "org_id": org_id_value,
                "request_id": request_id,
            },
        )

        # Get or create user
        async with get_session_context() as db_session:
            # Find existing user by auth_subject (WorkOS ID)
            result = await db_session.execute(
                select(User).where(User.auth_subject == subject)
            )
            user = result.scalar_one_or_none()

            if not user:
                # Create new user
                user = User(
                    auth_provider="workos",
                    auth_subject=subject,
                    email=email,
                    display_name=email.split("@")[0] if email else None,
                )
                db_session.add(user)
                await db_session.flush()
                logger.info(
                    "New enterprise user created",
                    extra={
                        "service": "auth",
                        "user_id": str(user.id),
                        "auth_provider": "workos",
                        "auth_subject": subject,
                    },
                )
            else:
                # Update email if changed
                if email and user.email != email:
                    user.email = email

            # Enterprise: Bootstrap organization membership
            org_service = OrganizationService(db_session)
            org = await org_service.upsert_organization(
                org_id=org_id_value,
                user_id=user.id,
            )
            await org_service.ensure_membership(
                user_id=user.id,
                organization_id=org.id,
                role=role,
                permissions=permissions,
            )

            logger.info(
                "Enterprise user authenticated",
                extra={
                    "service": "auth",
                    "user_id": str(user.id),
                    "org_id": str(org.id),
                },
            )

            # Handle session resume
            resumed_session_id: uuid.UUID | None = None
            if requested_session_id_raw:
                try:
                    requested_session_id = uuid.UUID(str(requested_session_id_raw))
                    result = await db_session.execute(
                        select(Session.id).where(
                            Session.id == requested_session_id,
                            Session.user_id == user.id,
                        )
                    )
                    resumed_session_id = result.scalar_one_or_none()
                except Exception:
                    resumed_session_id = None

            if requested_session_id_raw:
                logger.info(
                    "Auth session resume attempted",
                    extra={
                        "service": "auth",
                        "user_id": str(user.id),
                        "requested_session_id": str(requested_session_id_raw),
                        "resumed_session_id": str(resumed_session_id)
                        if resumed_session_id
                        else None,
                    },
                )

            # Mark connection as authenticated
            manager.authenticate(websocket, user.id, session_id=resumed_session_id)

            conn = manager.get_connection(websocket)
            if conn:
                conn.org_id = org.id

            # Optional platform hint ("web" | "native")
            if conn and platform_raw in ("web", "native"):
                conn.platform = platform_raw

            # Update logging context
            set_request_context(
                user_id=str(user.id),
                org_id=str(org.id),
            )

            # Send success response
            await manager.send_message(
                websocket,
                {
                    "type": "auth.success",
                    "payload": {
                        "userId": str(user.id),
                        "sessionId": str(resumed_session_id)
                        if resumed_session_id
                        else None,
                        "orgId": str(org.id),
                    },
                },
            )

            if conn and conn.platform == "web":

                async def _run_meta_catch_up() -> None:
                    try:
                        async with get_session_context() as meta_db:
                            result = await MetaSummaryService(
                                meta_db
                            ).merge_latest_unprocessed_summaries(
                                user_id=user.id,
                                max_sessions=1,
                            )

                        if result is None:
                            return

                        meta, merged = result
                        source = merged[-1]

                        await manager.send_message(
                            websocket,
                            {
                                "type": "meta_summary.updated",
                                "payload": {
                                    "userId": str(user.id),
                                    "trigger": "meta_summary.catch_up.auth.success",
                                    "metaSummaryId": str(meta.id),
                                    "text": meta.summary_text,
                                    "updatedAt": meta.updated_at.isoformat(),
                                    "sourceSessionId": str(source.session_id),
                                    "sourceSessionSummaryId": str(source.id),
                                },
                            },
                        )
                    except Exception as exc:
                        logger.warning(
                            "Meta summary catch-up failed during auth.success",
                            extra={
                                "service": "auth",
                                "user_id": str(user.id),
                                "error": str(exc),
                            },
                        )

                asyncio.create_task(_run_meta_catch_up())

            # Send initial status update
            await manager.send_message(
                websocket,
                {
                    "type": "status.update",
                    "payload": {
                        "service": "ws",
                        "status": "connected",
                        "metadata": {},
                    },
                },
            )

            # Send tenancy bootstrap complete status
            await manager.send_message(
                websocket,
                {
                    "type": "status.update",
                    "payload": {
                        "service": "auth",
                        "status": "tenancy_bootstrap_complete",
                        "metadata": {
                            "orgId": str(org.id),
                        },
                    },
                },
            )

            # Warm up STT provider to reduce first-request latency
            try:
                from app.ai.providers.factory import get_stt_provider

                stt = get_stt_provider()
                if hasattr(stt, "warm_up"):
                    await stt.warm_up()

                triage_service = TriageService(db_session, llm_provider=get_llm_provider())
                if hasattr(triage_service, "warm_up"):
                    await triage_service.warm_up()

                assessment_service = AssessmentService(db_session, llm_provider=get_llm_provider())
                if hasattr(assessment_service, "warm_up"):
                    await assessment_service.warm_up()
            except Exception as warm_up_err:
                logger.debug(
                    "STT warm-up failed (non-critical)",
                    extra={"service": "auth", "error": str(warm_up_err)},
                )

    except IdentityTokenError as e:
        logger.warning(
            "JWT verification failed",
            extra={
                "service": "auth",
                "error": str(e),
                "ws_id": id(websocket),
            },
        )
        await manager.send_message(
            websocket,
            {
                "type": "auth.error",
                "payload": {
                    "code": "INVALID_TOKEN",
                    "message": str(e),
                },
            },
        )

    except Exception as e:
        logger.error(
            "Auth handler error",
            extra={
                "service": "auth",
                "error": str(e),
                "ws_id": id(websocket),
            },
            exc_info=True,
        )
        await manager.send_message(
            websocket,
            {
                "type": "auth.error",
                "payload": {
                    "code": "AUTH_ERROR",
                    "message": "Authentication failed",
                },
            },
        )
