from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from hello_sales_backend.modules.salesbook.infra.memory import (
    InMemorySalesbookClientContactRepository,
    InMemorySalesbookCommentRepository,
    InMemorySalesbookEngagementRepository,
    InMemorySalesbookOnboardingRepository,
    InMemorySalesbookPipelineRepository,
    InMemorySalesbookPinRepository,
    InMemorySalesbookTeamMembershipRepository,
    NullProductReadPort,
)
from hello_sales_backend.modules.salesbook.use_cases.salesbook_service import SalesbookService
from hello_sales_backend.modules.salesbook.use_cases.views import (
    PipelineDealCreateRequest,
    PipelineDealUpdateRequest,
)
from hello_sales_backend.platform.tasks.runner import BackgroundTaskRunner
from hello_sales_backend.shared.errors import AppError, app_error


class FailingSheetsProvider:
    def __init__(self) -> None:
        self.attempts = 0

    async def push(self, action: str, payload: dict[str, object]) -> None:
        self.attempts += 1
        raise app_error(
            "Sheets provider timed out",
            code="provider.sheets.timeout",
            category="provider",
            status_code=504,
            retryable=True,
            details={"action": action, "payload_keys": sorted(payload.keys())},
            operation="salesbook.sheets.push",
            component="salesbook",
        )


class FlakySheetsProvider:
    def __init__(self, succeed_on_attempt: int) -> None:
        self.attempts = 0
        self._succeed_on_attempt = succeed_on_attempt

    async def push(self, action: str, payload: dict[str, object]) -> None:
        self.attempts += 1
        if self.attempts >= self._succeed_on_attempt:
            return
        raise app_error(
            "Sheets provider timed out",
            code="provider.sheets.timeout",
            category="provider",
            status_code=504,
            retryable=True,
            details={"action": action, "payload_keys": sorted(payload.keys())},
            operation="salesbook.sheets.push",
            component="salesbook",
        )


def _build_service(*, tasks: BackgroundTaskRunner | None = None, sheets_provider: object | None = None) -> SalesbookService:
    return SalesbookService(
        contact_repo=InMemorySalesbookClientContactRepository(),
        onboarding_repo=InMemorySalesbookOnboardingRepository(),
        pipeline_repo=InMemorySalesbookPipelineRepository(),
        engagement_repo=InMemorySalesbookEngagementRepository(),
        team_repo=InMemorySalesbookTeamMembershipRepository(),
        product_read=NullProductReadPort(),
        comment_repo=InMemorySalesbookCommentRepository(),
        pin_repo=InMemorySalesbookPinRepository(),
        sheets_provider=sheets_provider,  # type: ignore[arg-type]
        tasks=tasks,
    )


@pytest.mark.asyncio
async def test_salesbook_missing_deal_raises_structured_error() -> None:
    service = _build_service()

    with pytest.raises(AppError) as exc_info:
        await service.update_deal("missing-deal", PipelineDealUpdateRequest(stage="qualified"))

    assert exc_info.value.code == "salesbook.deal.not_found"
    assert exc_info.value.category == "domain"
    assert exc_info.value.status_code == 404
    assert exc_info.value.component == "salesbook"
    assert exc_info.value.details["deal_id"] == "missing-deal"


@pytest.mark.asyncio
async def test_salesbook_missing_comment_raises_structured_error() -> None:
    repo = InMemorySalesbookCommentRepository()

    with pytest.raises(AppError) as exc_info:
        await repo.update_status("missing-comment", status="approved", approved_by="admin@example.com")

    assert exc_info.value.code == "salesbook.comment.not_found"
    assert exc_info.value.category == "domain"
    assert exc_info.value.status_code == 404
    assert exc_info.value.details["comment_id"] == "missing-comment"


@pytest.mark.asyncio
async def test_salesbook_sheets_failures_are_recorded_as_background_task_failures() -> None:
    runner = BackgroundTaskRunner()
    provider = FailingSheetsProvider()
    service = _build_service(tasks=runner, sheets_provider=provider)

    await service.create_deal(
        "profile-1",
        PipelineDealCreateRequest(
            stage="new_lead",
            lead_score=10,
            deal_value=Decimal("100.00"),
            deal_probability=Decimal("0.25"),
        ),
        request_id="req-salesbook",
        trace_id="trace-salesbook",
    )
    await asyncio.sleep(0.25)

    failures = runner.pop_failures()
    assert len(failures) == 1
    assert provider.attempts == 3
    assert failures[0].code == "salesbook.sheets.retry_exhausted"
    assert failures[0].category == "provider"
    assert failures[0].metadata.request_id == "req-salesbook"
    assert failures[0].metadata.trace_id == "trace-salesbook"
    assert failures[0].metadata.purpose == "salesbook.sheets.push.create_deal"
    assert failures[0].details is not None
    assert failures[0].details["details"]["last_issue_code"] == "provider.sheets.timeout"
    assert failures[0].details["details"]["max_attempts"] == 3

    snapshots = runner.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].status.value == "failed"
    assert snapshots[0].error_code == "salesbook.sheets.retry_exhausted"


@pytest.mark.asyncio
async def test_salesbook_sheets_retryable_failures_can_recover_before_budget_exhaustion() -> None:
    runner = BackgroundTaskRunner()
    provider = FlakySheetsProvider(succeed_on_attempt=3)
    service = _build_service(tasks=runner, sheets_provider=provider)

    await service.create_deal(
        "profile-1",
        PipelineDealCreateRequest(
            stage="new_lead",
            lead_score=10,
            deal_value=Decimal("100.00"),
            deal_probability=Decimal("0.25"),
        ),
        request_id="req-salesbook",
        trace_id="trace-salesbook",
    )
    await asyncio.sleep(0.2)

    assert provider.attempts == 3
    assert runner.pop_failures() == []
    snapshots = runner.list_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].status.value == "completed"
