"""Salesbook application service. /Oliviercontribution.

Single facade exposing 14 public methods covering: client contact upsert,
onboarding response storage with auto-progress recompute, pipeline CRUD with
stage-transition stamping, engagement log append + queries, team membership
roster, and the exhaustive view that drives the searchable salesbook frontend.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from hello_sales_backend.modules.salesbook.domain.value_objects import (
    PHASE_1_TOTAL_QUESTIONS,
    PHASE_2_TOTAL_QUESTIONS,
    PHASE_3_TOTAL_QUESTIONS,
    TOTAL_ONBOARDING_QUESTIONS,
)
from hello_sales_backend.modules.salesbook.use_cases.ports import (
    SalesbookClientContactRepositoryPort,
    SalesbookCommentRepositoryPort,
    SalesbookEngagementRepositoryPort,
    SalesbookOnboardingRepositoryPort,
    SalesbookPinRepositoryPort,
    SalesbookPipelineRepositoryPort,
    SalesbookProductReadPort,
    SalesbookTeamMembershipRepositoryPort,
    SheetPushPort,
)
from hello_sales_backend.modules.salesbook.use_cases.views import (
    ClientContactUpsertRequest,
    ClientContactView,
    EngagementLogCreateRequest,
    EngagementLogView,
    OnboardingBatchSubmit,
    OnboardingProgressView,
    OnboardingResponseSubmit,
    OnboardingResponseView,
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
    PipelineDealView,
    SalesbookCommentApproveRequest,
    SalesbookCommentCreateRequest,
    SalesbookCommentView,
    SalesbookExhaustiveOnboardingEntry,
    SalesbookExhaustiveView,
    SalesbookPinRequest,
    SalesbookPinView,
    TeamMembershipCreateRequest,
    TeamMembershipView,
)
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.tasks.models import TaskMetadata
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import AppError, app_error, internal_error
from hello_sales_backend.shared.ids import new_id

PHASE_TOTALS = {
    1: PHASE_1_TOTAL_QUESTIONS,
    2: PHASE_2_TOTAL_QUESTIONS,
    3: PHASE_3_TOTAL_QUESTIONS,
}
SHEETS_PUSH_MAX_ATTEMPTS = 3
SHEETS_PUSH_RETRY_BACKOFF_SECONDS = 0.05


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SalesbookService:
    """Main service facade for the salesbook bounded context."""

    _logger = get_logger("hello_sales_backend.salesbook")

    def __init__(
        self,
        *,
        contact_repo: SalesbookClientContactRepositoryPort,
        onboarding_repo: SalesbookOnboardingRepositoryPort,
        pipeline_repo: SalesbookPipelineRepositoryPort,
        engagement_repo: SalesbookEngagementRepositoryPort,
        team_repo: SalesbookTeamMembershipRepositoryPort,
        product_read: SalesbookProductReadPort,
        comment_repo: SalesbookCommentRepositoryPort,
        pin_repo: SalesbookPinRepositoryPort,
        sheets_provider: SheetPushPort | None = None,
        tasks: BackgroundTaskRunner | None = None,
    ) -> None:
        self._contact = contact_repo
        self._onboarding = onboarding_repo
        self._pipeline = pipeline_repo
        self._engagement = engagement_repo
        self._team = team_repo
        self._product_read = product_read
        self._comments = comment_repo
        self._pins = pin_repo
        self._sheets = sheets_provider
        self._tasks = tasks

    # ---- Onboarding registry passthrough (avoids importing in route layer) ----
    def get_onboarding_registry(self, phase: int | None = None) -> dict[str, dict[str, object]]:
        from hello_sales_backend.modules.salesbook.domain.onboarding_registry import (
            ONBOARDING_QUESTIONS,
            get_phase_questions,
        )
        if phase is None:
            return ONBOARDING_QUESTIONS
        return get_phase_questions(phase)

    # ---- Client contact ----
    async def get_client_contact(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> ClientContactView | None:
        return await self._contact.get(profile_id)

    async def upsert_client_contact(
        self,
        profile_id: str,
        request: ClientContactUpsertRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> ClientContactView:
        view = await self._contact.upsert(profile_id, request)
        self._maybe_push(
            "upsert_client_contact",
            view.model_dump(mode="json"),
            request_id=request_id,
            trace_id=trace_id,
        )
        return view

    # ---- Onboarding ----
    async def get_onboarding_progress(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> OnboardingProgressView:
        return await self._onboarding.get_progress(profile_id)

    async def list_responses(
        self,
        profile_id: str,
        phase: int | None = None,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[OnboardingResponseView]:
        return await self._onboarding.list_responses(profile_id, phase=phase)

    async def submit_response(
        self,
        profile_id: str,
        request: OnboardingResponseSubmit,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> OnboardingResponseView:
        view = await self._onboarding.upsert_response(profile_id, request)
        await self._recompute_progress(profile_id)
        self._maybe_push(
            "submit_onboarding_response",
            {"profile_id": profile_id, **view.model_dump(mode="json")},
            request_id=request_id,
            trace_id=trace_id,
        )
        return view

    async def submit_batch(
        self,
        profile_id: str,
        request: OnboardingBatchSubmit,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[OnboardingResponseView]:
        out: list[OnboardingResponseView] = []
        for item in request.responses:
            out.append(await self._onboarding.upsert_response(profile_id, item))
        await self._recompute_progress(profile_id)
        self._maybe_push(
            "submit_onboarding_batch",
            {
                "profile_id": profile_id,
                "phase": request.phase,
                "responses": [r.model_dump(mode="json") for r in out],
            },
            request_id=request_id,
            trace_id=trace_id,
        )
        return out

    async def _recompute_progress(self, profile_id: str) -> OnboardingProgressView:
        counts = await self._onboarding.count_answered_by_phase(profile_id)
        existing = await self._onboarding.get_progress(profile_id)

        def pct(answered: int, total: int) -> float:
            if total <= 0:
                return 0.0
            return round(answered / total * 100, 2)

        p1 = pct(counts.get(1, 0), PHASE_TOTALS[1])
        p2 = pct(counts.get(2, 0), PHASE_TOTALS[2])
        p3 = pct(counts.get(3, 0), PHASE_TOTALS[3])
        total_pct = round(
            (counts.get(1, 0) + counts.get(2, 0) + counts.get(3, 0))
            / TOTAL_ONBOARDING_QUESTIONS * 100,
            2,
        )

        if p1 < 100:
            current_phase = 1
        elif p2 < 100:
            current_phase = 2
        else:
            current_phase = 3

        now_iso = _utc_now_iso()
        return await self._onboarding.upsert_progress(
            profile_id,
            current_phase=current_phase,
            phase1_pct=p1, phase2_pct=p2, phase3_pct=p3, total_pct=total_pct,
            phase1_completed_at_iso=(
                now_iso if p1 >= 100 and existing.phase1_completed_at is None
                else (existing.phase1_completed_at.isoformat() if existing.phase1_completed_at else None)
            ),
            phase2_completed_at_iso=(
                now_iso if p2 >= 100 and existing.phase2_completed_at is None
                else (existing.phase2_completed_at.isoformat() if existing.phase2_completed_at else None)
            ),
            phase3_completed_at_iso=(
                now_iso if p3 >= 100 and existing.phase3_completed_at is None
                else (existing.phase3_completed_at.isoformat() if existing.phase3_completed_at else None)
            ),
        )

    # ---- Pipeline ----
    async def list_deals(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> list[PipelineDealView]:
        return await self._pipeline.list_deals(profile_id)

    async def create_deal(
        self,
        profile_id: str,
        request: PipelineDealCreateRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> PipelineDealView:
        view = await self._pipeline.create_deal(profile_id, request)
        self._maybe_push("create_deal", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def update_deal(
        self,
        deal_id: str,
        request: PipelineDealUpdateRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> PipelineDealView:
        view = await self._pipeline.update_deal(deal_id, request)
        self._maybe_push("update_deal", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    # ---- Engagement ----
    async def log_engagement(
        self, request: EngagementLogCreateRequest, *, request_id: str | None = None, trace_id: str | None = None
    ) -> EngagementLogView:
        view = await self._engagement.create(request)
        self._maybe_push("log_engagement", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def list_engagements(
        self,
        profile_id: str,
        deal_id: str | None = None,
        limit: int = 100,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[EngagementLogView]:
        return await self._engagement.list_for_profile(profile_id, deal_id=deal_id, limit=limit)

    async def list_all_engagements(
        self, limit: int = 200, *, request_id: str | None = None, trace_id: str | None = None
    ) -> list[EngagementLogView]:
        return await self._engagement.list_all(limit=limit)

    # ---- Team ----
    async def list_team(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> list[TeamMembershipView]:
        return await self._team.list_team(profile_id)

    async def add_team_member(
        self,
        profile_id: str,
        request: TeamMembershipCreateRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> TeamMembershipView:
        view = await self._team.add(profile_id, request)
        self._maybe_push("add_team_member", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def remove_team_member(
        self, membership_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> None:
        await self._team.remove(membership_id)
        self._maybe_push(
            "remove_team_member",
            {"membership_id": membership_id},
            request_id=request_id,
            trace_id=trace_id,
        )

    # ---- Exhaustive view (drives the searchable salesbook viewer) ----
    async def get_exhaustive_view(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> SalesbookExhaustiveView:
        registry = self.get_onboarding_registry()
        responses = await self._onboarding.list_responses(profile_id)
        answer_by_key = {r.question_key: r for r in responses}
        onboarding_entries: list[SalesbookExhaustiveOnboardingEntry] = []
        for key, meta in registry.items():
            r = answer_by_key.get(key)
            raw_phase = meta.get("phase")
            phase_val = int(raw_phase) if isinstance(raw_phase, (int, float, str)) else 0
            section_val = meta.get("section")
            question_val = meta.get("question") or meta.get("question_text")
            type_val = (
                (r.response_type if r else None)
                or meta.get("answer_type")
                or meta.get("type")
            )
            onboarding_entries.append(SalesbookExhaustiveOnboardingEntry(
                phase=phase_val,
                section=str(section_val) if section_val is not None else None,
                question_key=key,
                question_text=str(question_val) if question_val is not None else None,
                response_value=r.response_value if r else None,
                response_type=str(type_val) if type_val is not None else None,
                answered_at=r.answered_at if r else None,
            ))
        return SalesbookExhaustiveView(
            profile_id=profile_id,
            contact=await self._contact.get(profile_id),
            progress=await self._onboarding.get_progress(profile_id),
            onboarding=onboarding_entries,
            products=await self._product_read.list_products_for_profile(profile_id),
            pipeline=await self._pipeline.list_deals(profile_id),
            engagement=await self._engagement.list_for_profile(profile_id, limit=500),
            team=await self._team.list_team(profile_id),
            comments=await self._comments.list_for_profile(profile_id, status="approved"),
            pinned=await self._pins.list_for_profile(profile_id),
        )

    # ---- Moderation: comments + pins ----
    async def add_comment(
        self,
        profile_id: str,
        request: SalesbookCommentCreateRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SalesbookCommentView:
        view = await self._comments.create(profile_id, request)
        self._maybe_push("add_comment", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def list_comments(
        self,
        profile_id: str,
        status: str | None = None,
        target_id: str | None = None,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[SalesbookCommentView]:
        return await self._comments.list_for_profile(profile_id, status=status, target_id=target_id)

    async def review_comment(
        self,
        comment_id: str,
        request: SalesbookCommentApproveRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SalesbookCommentView:
        view = await self._comments.update_status(
            comment_id,
            status=request.decision,
            approved_by=request.approved_by if request.decision == "approved" else None,
        )
        self._maybe_push("review_comment", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def list_pins(
        self, profile_id: str, *, request_id: str | None = None, trace_id: str | None = None
    ) -> list[SalesbookPinView]:
        return await self._pins.list_for_profile(profile_id)

    async def pin_entry(
        self,
        profile_id: str,
        request: SalesbookPinRequest,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> SalesbookPinView:
        view = await self._pins.upsert(profile_id, request)
        self._maybe_push("pin_entry", view.model_dump(mode="json"), request_id=request_id, trace_id=trace_id)
        return view

    async def unpin_entry(
        self,
        profile_id: str,
        target_type: str,
        target_id: str,
        *,
        request_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        await self._pins.remove(profile_id, target_type, target_id)
        self._maybe_push(
            "unpin_entry",
            {"profile_id": profile_id, "target_type": target_type, "target_id": target_id},
            request_id=request_id,
            trace_id=trace_id,
        )

    # ---- Sheets sync (owned background task; safe when provider is None) ----
    def _maybe_push(
        self,
        action: str,
        payload: dict[str, object],
        *,
        request_id: str | None,
        trace_id: str | None,
    ) -> None:
        if self._sheets is None:
            return
        if self._tasks is None:
            return
        task_id = new_id()
        metadata = TaskMetadata(
            task_id=task_id,
            purpose=f"salesbook.sheets.push.{action}",
            request_id=request_id,
            trace_id=trace_id,
            actor_id=None,
        )
        try:
            self._tasks.start(
                metadata,
                self._run_sheets_push(metadata=metadata, action=action, payload=payload),
            )
        except Exception as exc:
            self._logger.error(
                "salesbook.sheets.push.failed",
                code="salesbook.sheets.push_failed",
                component="salesbook",
                operation=f"salesbook.sheets.push.{action}",
                correlation_id=request_id,
                trace_id=trace_id,
                task_id=task_id,
                action=action,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                details={"payload_keys": list(payload.keys())},
            )
            self._emit_failure_event(
                action=action,
                task_id=task_id,
                request_id=request_id,
                trace_id=trace_id,
                exc=exc,
            )

    async def _run_sheets_push(
        self,
        *,
        metadata: TaskMetadata,
        action: str,
        payload: dict[str, object],
    ) -> None:
        last_error: AppError | None = None
        for attempt in range(1, SHEETS_PUSH_MAX_ATTEMPTS + 1):
            try:
                await self._sheets.push(action, payload)  # type: ignore[union-attr]
                return
            except AppError as exc:
                last_error = exc
            except Exception as exc:
                last_error = internal_error(
                    "Salesbook sheets push failed unexpectedly",
                    code="salesbook.sheets.push_unexpected",
                    details={
                        "action": action,
                        "attempt": attempt,
                        "max_attempts": SHEETS_PUSH_MAX_ATTEMPTS,
                        "payload_keys": sorted(payload.keys()),
                    },
                    operation=f"salesbook.sheets.push.{action}",
                    component="salesbook",
                    exc=exc,
                )

            if last_error.retryable and attempt < SHEETS_PUSH_MAX_ATTEMPTS:
                self._logger.warning(
                    "salesbook.sheets.push.retry_scheduled",
                    code="salesbook.sheets.retry_scheduled",
                    component="salesbook",
                    operation=f"salesbook.sheets.push.{action}",
                    correlation_id=metadata.request_id,
                    trace_id=metadata.trace_id,
                    task_id=metadata.task_id,
                    attempt=attempt,
                    next_attempt=attempt + 1,
                    max_attempts=SHEETS_PUSH_MAX_ATTEMPTS,
                    issue_code=last_error.code,
                    issue_category=last_error.category,
                    retryable=last_error.retryable,
                )
                await self._emit_operational_event(
                    event_type="salesbook.sheets.push.retry_scheduled",
                    severity="warning",
                    operation=f"salesbook.sheets.push.{action}",
                    correlation_id=metadata.request_id,
                    trace_id=metadata.trace_id,
                    code="salesbook.sheets.retry_scheduled",
                    payload={
                        "task_id": metadata.task_id,
                        "action": action,
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "max_attempts": SHEETS_PUSH_MAX_ATTEMPTS,
                        "issue_code": last_error.code,
                        "issue_category": last_error.category,
                        "retryable": last_error.retryable,
                    },
                )
                await asyncio.sleep(SHEETS_PUSH_RETRY_BACKOFF_SECONDS * attempt)
                continue

            break

        assert last_error is not None
        exhausted_error = app_error(
            "Salesbook sheets push exhausted retry budget",
            code="salesbook.sheets.retry_exhausted" if last_error.retryable else last_error.code,
            category="provider" if last_error.retryable else last_error.category,
            status_code=last_error.status_code,
            severity="error",
            retryable=False,
            details={
                "action": action,
                "attempt": SHEETS_PUSH_MAX_ATTEMPTS,
                "max_attempts": SHEETS_PUSH_MAX_ATTEMPTS,
                "task_id": metadata.task_id,
                "last_issue_code": last_error.code,
                "last_issue_category": last_error.category,
                "last_issue_details": last_error.details,
            },
            operation=f"salesbook.sheets.push.{action}",
            component="salesbook",
            exc=last_error,
        )
        self._logger.error(
            "salesbook.sheets.push.exhausted",
            code=exhausted_error.code,
            component="salesbook",
            operation=exhausted_error.operation,
            correlation_id=metadata.request_id,
            trace_id=metadata.trace_id,
            task_id=metadata.task_id,
            attempt=SHEETS_PUSH_MAX_ATTEMPTS,
            max_attempts=SHEETS_PUSH_MAX_ATTEMPTS,
            issue_code=last_error.code,
            issue_category=last_error.category,
        )
        await self._emit_operational_event(
            event_type="salesbook.sheets.push.exhausted",
            severity="error",
            operation=f"salesbook.sheets.push.{action}",
            correlation_id=metadata.request_id,
            trace_id=metadata.trace_id,
            code=exhausted_error.code,
            payload={
                "task_id": metadata.task_id,
                "action": action,
                "attempt": SHEETS_PUSH_MAX_ATTEMPTS,
                "max_attempts": SHEETS_PUSH_MAX_ATTEMPTS,
                "issue_code": last_error.code,
                "issue_category": last_error.category,
            },
        )
        raise exhausted_error

    def _emit_failure_event(
        self,
        *,
        action: str,
        task_id: str,
        request_id: str | None,
        trace_id: str | None,
        exc: Exception,
    ) -> None:
        if self._tasks is None or self._tasks._observability is None:
            return
        event = OperationalEvent(
            event_type="salesbook.sheets.push.failed",
            severity="error",
            component="salesbook",
            operation=f"salesbook.sheets.push.{action}",
            correlation_id=request_id,
            trace_id=trace_id,
            code="salesbook.sheets.push_failed",
            payload={
                "task_id": task_id,
                "action": action,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "severity": "error",
            },
        )
        self._tasks.start(
            TaskMetadata(
                task_id=new_id(),
                purpose="salesbook.operational_event.emit",
                request_id=request_id,
                trace_id=trace_id,
                actor_id=None,
            ),
            self._tasks._observability.emit(event),
        )

    async def _emit_operational_event(
        self,
        *,
        event_type: str,
        severity: str,
        operation: str,
        correlation_id: str | None,
        trace_id: str | None,
        code: str,
        payload: dict[str, object],
    ) -> None:
        if self._tasks is None or self._tasks._observability is None:
            return
        try:
            await self._tasks._observability.emit(
                OperationalEvent(
                    event_type=event_type,
                    severity=severity,
                    component="salesbook",
                    operation=operation,
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    code=code,
                    payload=payload,
                )
            )
        except Exception as exc:
            self._logger.error(
                "salesbook.operational_event.emit_failed",
                code="salesbook.operational_event.emit_failed",
                component="salesbook",
                operation=operation,
                correlation_id=correlation_id,
                trace_id=trace_id,
                event_type=event_type,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )


__all__ = ["SalesbookService"]
