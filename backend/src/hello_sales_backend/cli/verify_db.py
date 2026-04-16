"""Database verification CLI."""

from __future__ import annotations

import asyncio

from hello_sales_backend.platform.config.settings import get_settings
from hello_sales_backend.platform.db.engine import build_engine
from hello_sales_backend.platform.db.session import build_session_factory, ping_database


async def _run() -> int:
    settings = get_settings()
    engine = build_engine(settings)
    try:
        session_factory = build_session_factory(engine)
        await ping_database(session_factory)
        print("database verification: ok")
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    """Run the database verification command."""

    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
