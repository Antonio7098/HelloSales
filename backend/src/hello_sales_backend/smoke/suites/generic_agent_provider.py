"""Real-provider smoke suites for the agent runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel

from hello_sales_backend.shared.errors import app_error

from ..contracts import SmokeCase, SmokeContext
from ..support import app_client, parse_sse_events, wait_for_terminal_run_state


class SmokeScenarioResult(BaseModel):
    """One provider-backed smoke scenario outcome."""

    name: str
    status: str
    run_id: str | None = None
    details: dict[str, object] = {}


class GenericAgentProviderSmokeResult(BaseModel):
    """Serializable result payload for provider-backed smoke execution."""

    run_id: str
    status: str
    provider: str
    model: str
    response_text: str | None = None
    turns: list[dict[str, object]] = []
    scenarios: list[SmokeScenarioResult] = []


@dataclass(slots=True)
class ProviderSmokeHarness:
    """Shared helper for provider-backed smoke scenarios."""

    context: SmokeContext

    @property
    def settings(self) -> Any:
        return self.context.settings

    def validate_provider_configuration(self) -> None:
        settings = self.settings
        if not settings.resolved_generic_agent_provider:
            raise app_error(
                "Generic-agent provider is not configured",
                code="smoke.generic_agent_provider.missing_provider",
                category="config",
                status_code=500,
                details={"required_env": ["GENERIC_AGENT_PROVIDER", "GENERIC_AGENT_MODEL"]},
                operation="smoke.generic_agent_provider.preflight",
                component="smoke",
            )
        if not settings.resolved_generic_agent_model:
            raise app_error(
                "Generic-agent model is not configured",
                code="smoke.generic_agent_provider.missing_model",
                category="config",
                status_code=500,
                details={"required_env": ["GENERIC_AGENT_MODEL"]},
                operation="smoke.generic_agent_provider.preflight",
                component="smoke",
            )
        if not settings.resolved_generic_agent_api_key:
            raise app_error(
                "Generic-agent API key is not configured",
                code="smoke.generic_agent_provider.missing_api_key",
                category="config",
                status_code=500,
                details={"provider": settings.resolved_generic_agent_provider},
                operation="smoke.generic_agent_provider.preflight",
                component="smoke",
            )

    @staticmethod
    def extract_response_text(payload: dict[str, object]) -> str | None:
        turns = payload.get("turns")
        if not isinstance(turns, list) or not turns:
            return None
        last_turn = turns[-1]
        if not isinstance(last_turn, dict):
            return None
        response_text = last_turn.get("response_text")
        return str(response_text) if response_text is not None else None

    @staticmethod
    def extract_turns(payload: dict[str, object]) -> list[dict[str, object]]:
        turns = payload.get("turns")
        if not isinstance(turns, list):
            return []
        return [item for item in turns if isinstance(item, dict)]

    async def start_run(
        self,
        client: httpx.AsyncClient,
        *,
        input_text: str,
        profile_name: str = "generic",
    ) -> str:
        response = await client.post(
            f"{self.settings.api_prefix}/agent-runs",
            json={"input_text": input_text, "profile_name": profile_name},
        )
        response.raise_for_status()
        return str(response.json()["data"]["run_id"])

    async def get_events(self, client: httpx.AsyncClient, *, run_id: str) -> list[dict[str, object]]:
        response = await client.get(f"{self.settings.api_prefix}/agent-runs/{run_id}/events")
        response.raise_for_status()
        payload = response.json()["data"]
        return [item for item in payload if isinstance(item, dict)]

    async def run_completed_turn(
        self,
        client: httpx.AsyncClient,
        *,
        input_text: str,
        profile_name: str,
        name: str,
    ) -> tuple[SmokeScenarioResult, dict[str, object]]:
        run_id = await self.start_run(client, input_text=input_text, profile_name=profile_name)
        payload = await wait_for_terminal_run_state(
            client,
            path=f"{self.settings.api_prefix}/agent-runs/{run_id}",
            terminal_statuses={"completed", "failed", "cancelled"},
        )
        if payload["status"] != "completed":
            raise app_error(
                "Provider-backed smoke scenario did not complete successfully",
                code="smoke.generic_agent_provider.scenario_failed",
                category="runtime",
                status_code=500,
                details={"scenario": name, "run_id": run_id, "status": payload["status"]},
                operation="smoke.generic_agent_provider.completed_turn",
                component="smoke",
            )
        turns = self.extract_turns(payload)
        return (
            SmokeScenarioResult(
                name=name,
                status="completed",
                run_id=run_id,
                details={
                    "profile_name": profile_name,
                    "turn_count": len(turns),
                    "response_text_present": self.extract_response_text(payload) is not None,
                },
            ),
            payload,
        )

    async def scenario_generic_status_completion(self, client: httpx.AsyncClient) -> tuple[SmokeScenarioResult, dict[str, object]]:
        return await self.run_completed_turn(
            client,
            input_text="show me the current system status",
            profile_name="generic",
            name="generic_status_completion",
        )

    async def scenario_observer_status_completion(self, client: httpx.AsyncClient) -> tuple[SmokeScenarioResult, dict[str, object]]:
        scenario, payload = await self.run_completed_turn(
            client,
            input_text="observer: show me the current system status",
            profile_name="observer",
            name="observer_status_completion",
        )
        observer_turns = self.extract_turns(payload)
        observer_tools_obj = observer_turns[0].get("tools") if observer_turns else []
        observer_tools = observer_tools_obj if isinstance(observer_tools_obj, list) else []
        return (
            scenario.model_copy(
                update={
                    "details": {
                        **scenario.details,
                        "tool_names": [
                            item["tool_name"]
                            for item in observer_tools
                            if isinstance(item, dict) and isinstance(item.get("tool_name"), str)
                        ],
                    }
                }
            ),
            payload,
        )

    async def scenario_append_turn_completion(
        self,
        client: httpx.AsyncClient,
        *,
        existing_run_id: str | None = None,
    ) -> tuple[SmokeScenarioResult, dict[str, object]]:
        run_id = existing_run_id or await self.start_run(
            client,
            input_text="show me the current system status",
            profile_name="generic",
        )
        append_response = await client.post(
            f"{self.settings.api_prefix}/agent-runs/{run_id}/turns",
            json={"input_text": "list recent tasks"},
        )
        append_response.raise_for_status()
        payload = await wait_for_terminal_run_state(
            client,
            path=f"{self.settings.api_prefix}/agent-runs/{run_id}",
            terminal_statuses={"completed", "failed", "cancelled"},
        )
        turns = self.extract_turns(payload)
        if payload["status"] != "completed" or len(turns) < 2:
            raise app_error(
                "Append-turn provider smoke scenario did not complete successfully",
                code="smoke.generic_agent_provider.append_failed",
                category="runtime",
                status_code=500,
                details={"run_id": run_id, "status": payload["status"]},
                operation="smoke.generic_agent_provider.append_turn",
                component="smoke",
            )
        return (
            SmokeScenarioResult(
                name="append_turn_completion",
                status="completed",
                run_id=run_id,
                details={
                    "turn_count": len(turns),
                    "latest_turn_sequence_no": turns[-1].get("sequence_no"),
                },
            ),
            payload,
        )

    async def scenario_approval_boundary(self, client: httpx.AsyncClient) -> tuple[SmokeScenarioResult, dict[str, object]]:
        run_id = await self.start_run(
            client,
            input_text="please run diagnostic job now",
            profile_name="generic",
        )
        payload = await wait_for_terminal_run_state(
            client,
            path=f"{self.settings.api_prefix}/agent-runs/{run_id}",
            terminal_statuses={"awaiting_approval", "failed", "cancelled", "completed"},
        )
        if payload["status"] != "awaiting_approval":
            raise app_error(
                "Approval-boundary provider smoke scenario did not pause for approval",
                code="smoke.generic_agent_provider.approval_failed",
                category="runtime",
                status_code=500,
                details={"run_id": run_id, "status": payload["status"]},
                operation="smoke.generic_agent_provider.approval_boundary",
                component="smoke",
            )
        turns = self.extract_turns(payload)
        approval_id = None
        if turns:
            first_tools = turns[0].get("tools")
            if isinstance(first_tools, list) and first_tools and isinstance(first_tools[0], dict):
                approval_id = first_tools[0].get("approval_id")
        events = await self.get_events(client, run_id=run_id)
        return (
            SmokeScenarioResult(
                name="approval_boundary",
                status="completed",
                run_id=run_id,
                details={
                    "approval_id_present": approval_id is not None,
                    "event_types": [
                        item["event_type"] for item in events if isinstance(item.get("event_type"), str)
                    ],
                },
            ),
            payload,
        )

    async def scenario_event_stream_replay(
        self,
        client: httpx.AsyncClient,
        *,
        existing_run_id: str | None = None,
    ) -> tuple[SmokeScenarioResult, dict[str, object]]:
        run_id = existing_run_id or await self.start_run(
            client,
            input_text="show me the current system status",
            profile_name="generic",
        )
        payload = await wait_for_terminal_run_state(
            client,
            path=f"{self.settings.api_prefix}/agent-runs/{run_id}",
            terminal_statuses={"completed", "failed", "cancelled"},
        )
        async with client.stream(
            "GET",
            f"{self.settings.api_prefix}/agent-runs/{run_id}/events/stream",
        ) as response:
            response.raise_for_status()
            stream_body = "".join([chunk async for chunk in response.aiter_text()])
        sse_events = parse_sse_events(stream_body)
        first_event_id = sse_events[0].get("id") if sse_events else None
        cutoff = first_event_id if isinstance(first_event_id, int) else 0
        async with client.stream(
            "GET",
            f"{self.settings.api_prefix}/agent-runs/{run_id}/events/stream?after_sequence={cutoff}",
        ) as response:
            response.raise_for_status()
            replay_body = "".join([chunk async for chunk in response.aiter_text()])
        replay_events = parse_sse_events(replay_body)
        return (
            SmokeScenarioResult(
                name="event_stream_replay",
                status="completed",
                run_id=run_id,
                details={
                    "stream_event_count": len(sse_events),
                    "replay_event_count": len(replay_events),
                    "first_event": sse_events[0]["event"] if sse_events else None,
                    "last_event": sse_events[-1]["event"] if sse_events else None,
                },
            ),
            payload,
        )


class _ProviderSmokeBase(SmokeCase):
    """Base implementation for provider-backed smoke suites."""

    async def run(self, context: SmokeContext) -> BaseModel:
        harness = ProviderSmokeHarness(context)
        harness.validate_provider_configuration()
        app = context.build_app()
        try:
            async with app_client(app) as client:
                return await self.execute(client, harness)
        except Exception as exc:
            raise app_error(
                "Generic-agent smoke failed during application startup or request execution",
                code="smoke.generic_agent_provider.execution_failed",
                category="infrastructure",
                status_code=500,
                details={
                    "provider": context.settings.resolved_generic_agent_provider,
                    "model": context.settings.resolved_generic_agent_model,
                    "database_url": context.settings.database_url,
                    "smoke_name": self.name,
                },
                operation="smoke.generic_agent_provider.run",
                component="smoke",
                exc=exc,
            ) from exc

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        raise NotImplementedError

    @staticmethod
    def _result(
        harness: ProviderSmokeHarness,
        payload: dict[str, object],
        scenarios: list[SmokeScenarioResult],
        *,
        run_id: str,
    ) -> GenericAgentProviderSmokeResult:
        return GenericAgentProviderSmokeResult(
            run_id=run_id,
            status=str(payload["status"]),
            provider=harness.settings.resolved_generic_agent_provider,
            model=harness.settings.resolved_generic_agent_model,
            response_text=harness.extract_response_text(payload),
            turns=harness.extract_turns(payload),
            scenarios=scenarios,
        )


class GenericAgentProviderSmoke(_ProviderSmokeBase):
    """Run the full provider-backed scenario suite."""

    name = "generic-agent-provider"
    description = "Runs the full real provider-backed agent smoke scenario suite through the HTTP API."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        scenarios: list[SmokeScenarioResult] = []
        baseline, payload = await harness.scenario_generic_status_completion(client)
        scenarios.append(baseline)
        run_id = str(baseline.run_id)
        observer, _observer_payload = await harness.scenario_observer_status_completion(client)
        scenarios.append(observer)
        appended, payload = await harness.scenario_append_turn_completion(client, existing_run_id=run_id)
        scenarios.append(appended)
        approval, _approval_payload = await harness.scenario_approval_boundary(client)
        scenarios.append(approval)
        replay, _replay_payload = await harness.scenario_event_stream_replay(client, existing_run_id=run_id)
        scenarios.append(replay)
        return self._result(harness, payload, scenarios, run_id=run_id)


class GenericAgentProviderBaselineSmoke(_ProviderSmokeBase):
    """Run a minimal provider-backed completion smoke."""

    name = "generic-agent-provider-baseline"
    description = "Runs one minimal real provider-backed generic-agent completion."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        scenario, payload = await harness.scenario_generic_status_completion(client)
        run_id = str(scenario.run_id)
        return self._result(harness, payload, [scenario], run_id=run_id)


class ObserverAgentProviderSmoke(_ProviderSmokeBase):
    """Run the observer profile with a real provider."""

    name = "observer-agent-provider"
    description = "Runs one real provider-backed observer-agent completion."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        scenario, payload = await harness.scenario_observer_status_completion(client)
        run_id = str(scenario.run_id)
        return self._result(harness, payload, [scenario], run_id=run_id)


class GenericAgentAppendTurnSmoke(_ProviderSmokeBase):
    """Run the append-turn scenario with a real provider."""

    name = "generic-agent-provider-append-turn"
    description = "Runs a provider-backed append-turn lifecycle on an existing run."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        baseline, _baseline_payload = await harness.scenario_generic_status_completion(client)
        run_id = str(baseline.run_id)
        scenario, payload = await harness.scenario_append_turn_completion(client, existing_run_id=run_id)
        return self._result(harness, payload, [baseline, scenario], run_id=run_id)


class GenericAgentApprovalBoundarySmoke(_ProviderSmokeBase):
    """Run the approval-boundary scenario with a real provider."""

    name = "generic-agent-provider-approval-boundary"
    description = "Runs a provider-backed approval-boundary scenario and verifies the pause state."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        scenario, payload = await harness.scenario_approval_boundary(client)
        run_id = str(scenario.run_id)
        return self._result(harness, payload, [scenario], run_id=run_id)


class GenericAgentEventStreamSmoke(_ProviderSmokeBase):
    """Run the SSE replay scenario with a real provider."""

    name = "generic-agent-provider-event-stream"
    description = "Runs a provider-backed event stream and replay verification scenario."

    async def execute(
        self,
        client: httpx.AsyncClient,
        harness: ProviderSmokeHarness,
    ) -> GenericAgentProviderSmokeResult:
        baseline, _baseline_payload = await harness.scenario_generic_status_completion(client)
        run_id = str(baseline.run_id)
        scenario, payload = await harness.scenario_event_stream_replay(client, existing_run_id=run_id)
        return self._result(harness, payload, [baseline, scenario], run_id=run_id)
