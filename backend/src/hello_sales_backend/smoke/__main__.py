"""CLI entrypoint for smoke execution."""

from __future__ import annotations

import argparse
import asyncio
import json

from hello_sales_backend.shared.errors import AppError

from .contracts import SmokeContext
from .registry import SmokeRegistry
from .runner import SmokeRunner
from .suites.generic_agent_provider import (
    GenericAgentAppendTurnSmoke,
    GenericAgentApprovalBoundarySmoke,
    GenericAgentEntityMutationSmoke,
    GenericAgentEventStreamSmoke,
    GenericAgentProviderBaselineSmoke,
    GenericAgentProviderSmoke,
    GenericAgentSemanticCatalogReadSmoke,
    GenericAgentWebSearchSmoke,
    ObserverAgentProviderSmoke,
)
from .suites.worker_provider import WorkerProviderBaselineSmoke


def build_registry() -> SmokeRegistry:
    """Return the central smoke registry."""

    return SmokeRegistry(
        [
            GenericAgentProviderSmoke(),
            GenericAgentProviderBaselineSmoke(),
            ObserverAgentProviderSmoke(),
            GenericAgentAppendTurnSmoke(),
            GenericAgentApprovalBoundarySmoke(),
            GenericAgentEventStreamSmoke(),
            GenericAgentWebSearchSmoke(),
            GenericAgentSemanticCatalogReadSmoke(),
            GenericAgentEntityMutationSmoke(),
            WorkerProviderBaselineSmoke(),
        ]
    )


async def _run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hello_sales_backend.smoke")
    parser.add_argument("smoke_name", nargs="?", help="registered smoke name to execute")
    parser.add_argument("--list", action="store_true", dest="list_smokes")
    args = parser.parse_args(argv)

    registry = build_registry()
    runner = SmokeRunner(registry, SmokeContext.create())

    if args.list_smokes:
        print(json.dumps([item.model_dump(mode="json") for item in runner.definitions()], indent=2))
        return 0

    try:
        result = await runner.run(args.smoke_name)
    except AppError as exc:
        print(json.dumps({"error": exc.to_dict()}, indent=2))
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "smoke.unhandled_exception",
                        "message": str(exc),
                        "type": exc.__class__.__name__,
                    }
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps(result.model_dump(mode="json"), indent=2))
    status = str(result.payload.get("status", ""))
    if status == "completed":
        return 0
    if status == "timeout":
        return 3
    return 2


def main() -> int:
    """Run the smoke CLI."""

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
