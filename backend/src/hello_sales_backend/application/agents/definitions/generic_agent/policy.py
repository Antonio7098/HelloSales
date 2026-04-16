"""Tool selection policy for the baseline generic agent."""

from __future__ import annotations

import re
from dataclasses import dataclass

from hello_sales_backend.platform.agents.tools import AgentToolCatalog, AgentToolRequest


@dataclass(slots=True)
class KeywordToolSelectionPolicy:
    """Very small intent policy for the scaffold-stage generic agent."""

    def select(self, user_input: str, catalog: AgentToolCatalog) -> list[AgentToolRequest]:
        normalized = user_input.lower()
        requests: list[AgentToolRequest] = []
        if any(token in normalized for token in ("status", "runtime", "system", "health")) and catalog.has("get_runtime_status"):
            requests.append(AgentToolRequest(name="get_runtime_status", arguments={}))
        if any(token in normalized for token in ("tasks", "task list", "jobs", "recent task")) and catalog.has("list_recent_tasks"):
            requests.append(AgentToolRequest(name="list_recent_tasks", arguments={"limit": 10}))
        match = re.search(r"task[\s:]+([a-zA-Z0-9_-]+)", user_input)
        if match and catalog.has("get_task"):
            requests.append(AgentToolRequest(name="get_task", arguments={"task_id": match.group(1)}))
        if (("diagnostic" in normalized and "job" in normalized) or "run diagnostic" in normalized) and catalog.has("run_diagnostic_job"):
            requests.append(AgentToolRequest(name="run_diagnostic_job", arguments={"prompt": user_input}))
        return requests
