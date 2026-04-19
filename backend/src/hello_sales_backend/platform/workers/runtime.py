"""Worker execution runtime."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from pydantic import ValidationError

from hello_sales_backend.platform.llm import LLMCallContext, LLMProviderPort, schema_hint_from_model
from hello_sales_backend.platform.observability.events import OperationalEvent
from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.runtime import ObservabilityRuntime
from hello_sales_backend.platform.workers.contracts import WorkerRegistryPort
from hello_sales_backend.platform.workers.models import (
    WorkerRun,
    WorkerRunEvent,
    WorkerRunStatus,
    utc_now,
)
from hello_sales_backend.platform.workers.persistence import WorkerStorePort
from hello_sales_backend.shared.errors import AppError, app_error, internal_error
from hello_sales_backend.shared.ids import new_id


class WorkerExecutionRuntime(Protocol):
    """Execution surface used by the worker-runs module."""

    async def process_run(self, *, run_id: str) -> None: ...


@dataclass(slots=True)
class WorkerRuntime:
    """Own the execution lifecycle for worker runs."""

    llm_provider: LLMProviderPort
    store: WorkerStorePort
    workers: WorkerRegistryPort
    observability: ObservabilityRuntime
    backup_provider: LLMProviderPort | None = None
    _logger: Any = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._logger = get_logger("hello_sales_backend.worker_runtime")

    async def process_run(self, *, run_id: str) -> None:
        run = await self.store.get_run(run_id)
        if run is None:
            raise app_error(
                "Worker run was not found",
                code="worker.run.not_found",
                category="validation",
                status_code=404,
                details={"run_id": run_id},
                operation="worker.process_run",
                component="worker",
            )
        definition = self.workers.require(run.worker_name)
        if run.prompt is None:
            run.prompt = definition.effective_prompt_ref()
        started_at = perf_counter()
        await self._mark_running(run)
        self.observability.on_worker_run_started(
            worker_name=run.worker_name,
            execution_mode=run.execution_mode.value,
        )
        with self.observability.start_worker_run_span(
            run_id=run.run_id,
            worker_name=run.worker_name,
            prompt=run.prompt,
            request_id=run.request_id,
            trace_id=run.trace_id,
            execution_mode=run.execution_mode.value,
        ) as span:
            try:
                validated_input = definition.input_model.model_validate(run.input_payload)
                schema_hint = schema_hint_from_model(definition.output_model, name=f"{definition.worker_name}_result")
                last_issue: str | None = None
                for attempt in range(1, run.max_attempts + 1):
                    provider = self._select_provider(definition=definition, attempt=attempt, run=run)
                    provider_name = provider.provider_name
                    if attempt > 1:
                        run.status = WorkerRunStatus.RETRYING
                        run.updated_at = utc_now()
                        await self.store.update_run(run)
                        await self._append_event(
                            run=run,
                            event_type="worker.attempt.retry_scheduled",
                            severity="warning",
                            code="worker.attempt.retry_scheduled",
                            payload={"attempt": attempt, "max_attempts": run.max_attempts, "worker_name": run.worker_name},
                        )
                    run.status = WorkerRunStatus.RUNNING
                    run.attempt_count = attempt
                    run.updated_at = utc_now()
                    await self.store.update_run(run)
                    if provider is self.backup_provider:
                        await self._append_event(
                            run=run,
                            event_type="worker.fallback.selected",
                            severity="warning",
                            code="worker.fallback.selected",
                            payload={"attempt": attempt, "provider": provider_name},
                        )
                    await self._append_event(
                        run=run,
                        event_type="worker.attempt.started",
                        severity="info",
                        code="worker.attempt.started",
                        payload={"attempt": attempt, "provider": provider_name},
                    )
                    try:
                        async with asyncio.timeout(run.timeout_seconds):
                            result = await provider.generate_json(
                                definition.build_messages(validated_input, last_issue),
                                schema_hint=schema_hint,
                                context=LLMCallContext(
                                    request_id=run.request_id,
                                    trace_id=run.trace_id,
                                    actor_id=run.actor_id,
                                    timeout_seconds=run.timeout_seconds,
                                    operation="worker.llm.generate_json",
                                    prompt=run.prompt,
                                ),
                            )
                    except TimeoutError as exc:
                        last_issue = f"timed out after {run.timeout_seconds} seconds"
                        structured = app_error(
                            "Worker execution attempt timed out",
                            code="worker.timeout",
                            category="worker",
                            status_code=504,
                            retryable=attempt < run.max_attempts,
                            details={
                                "run_id": run.run_id,
                                "worker_name": run.worker_name,
                                "attempt": attempt,
                                "timeout_seconds": run.timeout_seconds,
                            },
                            operation="worker.process_run",
                            component="worker",
                            exc=exc,
                        )
                        if attempt < run.max_attempts:
                            await self._append_event(
                                run=run,
                                event_type="worker.attempt.timeout",
                                severity="warning",
                                code=structured.code,
                                payload={"attempt": attempt, "error": structured.to_dict()},
                            )
                            continue
                        raise structured from exc
                    except AppError as exc:
                        last_issue = exc.message
                        if exc.retryable and attempt < run.max_attempts:
                            await self._append_event(
                                run=run,
                                event_type="worker.attempt.provider_failed",
                                severity="warning",
                                code=exc.code,
                                payload={"attempt": attempt, "error": exc.to_dict()},
                            )
                            continue
                        raise
                    if result.output_json is None:
                        last_issue = f"provider returned non-JSON output: {result.raw_text[:500]}"
                        await self._append_event(
                            run=run,
                            event_type="worker.attempt.validation_failed",
                            severity="warning",
                            code="worker.output.invalid_json",
                            payload={"attempt": attempt, "raw_text": result.raw_text[:500]},
                        )
                        if attempt < run.max_attempts:
                            continue
                        raise app_error(
                            "Worker output was not valid JSON",
                            code="worker.output.invalid_json",
                            category="validation",
                            status_code=502,
                            details={"run_id": run.run_id, "worker_name": run.worker_name, "attempt": attempt},
                            operation="worker.process_run",
                            component="worker",
                        )
                    try:
                        validated_output = definition.output_model.model_validate(result.output_json)
                        if definition.validate_output is not None:
                            definition.validate_output(validated_output)
                    except (ValidationError, ValueError, AppError) as exc:
                        if isinstance(exc, AppError):
                            issue_code = exc.code
                            issue_payload = exc.to_dict()
                            last_issue = exc.message
                        else:
                            issue_code = "worker.output.validation_failed"
                            issue_payload = {"message": str(exc)}
                            last_issue = str(exc)
                        await self._append_event(
                            run=run,
                            event_type="worker.attempt.validation_failed",
                            severity="warning",
                            code=issue_code,
                            payload={"attempt": attempt, "error": issue_payload},
                        )
                        if attempt < run.max_attempts:
                            continue
                        raise app_error(
                            "Worker output did not satisfy the local contract",
                            code="worker.output.validation_failed",
                            category="validation",
                            status_code=502,
                            details={
                                "run_id": run.run_id,
                                "worker_name": run.worker_name,
                                "attempt": attempt,
                                "issue": last_issue,
                            },
                            operation="worker.process_run",
                            component="worker",
                            exc=exc if isinstance(exc, BaseException) else None,
                        ) from exc
                    await self._mark_completed(
                        run=run,
                        output_payload=validated_output.model_dump(mode="json"),
                        provider_name=result.provider,
                        model_name=result.model,
                    )
                    await self._append_event(
                        run=run,
                        event_type="worker.run.completed",
                        severity="info",
                        code="worker.run.completed",
                        payload={
                            "attempt": attempt,
                            "provider": result.provider,
                            "model": result.model,
                            "output": validated_output.model_dump(mode="json"),
                        },
                    )
                    self.observability.finish_worker_run_span(
                        span,
                        run_id=run.run_id,
                        worker_name=run.worker_name,
                        status=run.status.value,
                        error_type=None,
                    )
                    return
                raise internal_error(
                    "Worker run exhausted attempts without terminal state",
                    code="worker.run.invalid_state",
                    details={"run_id": run.run_id, "worker_name": run.worker_name},
                    operation="worker.process_run",
                    component="worker",
                )
            except asyncio.CancelledError:
                await self._mark_cancelled(run)
                await self._append_event(
                    run=run,
                    event_type="worker.run.cancelled",
                    severity="warning",
                    code="worker.run.cancelled",
                    payload={"task_id": run.task_id, "worker_name": run.worker_name},
                )
                self.observability.finish_worker_run_span(
                    span,
                    run_id=run.run_id,
                    worker_name=run.worker_name,
                    status=run.status.value,
                    error_type="CancelledError",
                )
                raise
            except Exception as exc:
                structured = exc if isinstance(exc, AppError) else internal_error(
                    "Worker execution failed unexpectedly",
                    code="worker.run.failed_unexpected",
                    details={"run_id": run.run_id, "worker_name": run.worker_name},
                    operation="worker.process_run",
                    component="worker",
                    exc=exc,
                )
                await self._mark_failed(run, structured)
                await self._append_event(
                    run=run,
                    event_type="worker.run.failed",
                    severity=structured.severity,
                    code=structured.code,
                    payload={"error": structured.to_dict()},
                )
                self.observability.finish_worker_run_span(
                    span,
                    run_id=run.run_id,
                    worker_name=run.worker_name,
                    status=run.status.value,
                    error_type=structured.__class__.__name__,
                )
                raise structured from exc
            finally:
                duration_seconds = perf_counter() - started_at
                self.observability.on_worker_run_finished(
                    worker_name=run.worker_name,
                    status=run.status.value,
                    duration_seconds=duration_seconds,
                )

    def _select_provider(self, *, definition: Any, attempt: int, run: WorkerRun) -> LLMProviderPort:
        if (
            definition.use_backup_on_final_attempt
            and self.backup_provider is not None
            and run.max_attempts > 1
            and attempt == run.max_attempts
        ):
            return self.backup_provider
        return self.llm_provider

    async def _mark_running(self, run: WorkerRun) -> None:
        now = utc_now()
        run.status = WorkerRunStatus.RUNNING
        run.started_at = run.started_at or now
        run.updated_at = now
        await self.store.update_run(run)
        await self._append_event(
            run=run,
            event_type="worker.run.started",
            severity="info",
            code="worker.run.started",
            payload={"worker_name": run.worker_name, "execution_mode": run.execution_mode.value},
        )

    async def _mark_completed(
        self,
        run: WorkerRun,
        *,
        output_payload: dict[str, object],
        provider_name: str,
        model_name: str,
    ) -> None:
        now = utc_now()
        run.status = WorkerRunStatus.COMPLETED
        run.output_payload = output_payload
        run.provider_name = provider_name
        run.model_name = model_name
        run.completed_at = now
        run.updated_at = now
        run.error_code = None
        run.error_category = None
        run.error_message = None
        run.error_details = None
        await self.store.update_run(run)

    async def _mark_failed(self, run: WorkerRun, exc: AppError) -> None:
        now = utc_now()
        run.status = WorkerRunStatus.FAILED
        run.completed_at = now
        run.updated_at = now
        run.error_code = exc.code
        run.error_category = exc.category
        run.error_message = exc.message
        run.error_details = exc.to_dict()
        await self.store.update_run(run)

    async def _mark_cancelled(self, run: WorkerRun) -> None:
        now = utc_now()
        run.status = WorkerRunStatus.CANCELLED
        run.completed_at = now
        run.updated_at = now
        run.error_code = "worker.run.cancelled"
        run.error_category = "worker"
        run.error_message = "Worker run was cancelled"
        run.error_details = {
            "run_id": run.run_id,
            "worker_name": run.worker_name,
            "task_id": run.task_id,
        }
        await self.store.update_run(run)

    async def _append_event(
        self,
        *,
        run: WorkerRun,
        event_type: str,
        severity: str,
        code: str | None,
        payload: dict[str, object],
    ) -> None:
        event = WorkerRunEvent(
            event_id=new_id(),
            run_id=run.run_id,
            sequence_no=await self.store.next_event_sequence(run.run_id),
            event_type=event_type,
            severity=severity,
            code=code,
            payload={**self._prompt_fields(run.prompt), **payload},
            request_id=run.request_id,
            trace_id=run.trace_id,
            actor_id=run.actor_id,
        )
        await self.store.append_event(event)
        await self.observability.emit(
            OperationalEvent(
                event_type=event_type,
                severity=severity,
                component="worker",
                operation=run.worker_name,
                correlation_id=run.request_id,
                trace_id=run.trace_id,
                code=code,
                payload={
                    "run_id": run.run_id,
                    "worker_name": run.worker_name,
                    **self._prompt_fields(run.prompt),
                    "severity": severity,
                    "code": code,
                    "message": event_type,
                    **json.loads(json.dumps(payload)),
                },
            )
        )
        self._logger.info(
            "worker.event",
            run_id=run.run_id,
            worker_name=run.worker_name,
            event_type=event_type,
            severity=severity,
            code=code,
            **self._prompt_fields(run.prompt),
            payload=payload,
        )

    @staticmethod
    def _prompt_fields(prompt: object | None) -> dict[str, object]:
        if prompt is None:
            return {}
        payload: dict[str, object] = {
            "prompt_id": prompt.prompt_id,
            "prompt_version": prompt.version,
            "prompt_owner_kind": prompt.owner_kind,
            "prompt_owner_id": prompt.owner_id,
            "prompt_purpose": prompt.purpose,
        }
        checksum = prompt.checksum
        if checksum is not None:
            payload["prompt_checksum"] = checksum
        return payload
