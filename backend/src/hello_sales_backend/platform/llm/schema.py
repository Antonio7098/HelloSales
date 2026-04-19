"""Helpers for normalized JSON schema hints."""

from __future__ import annotations

from pydantic import BaseModel

from hello_sales_backend.platform.llm.contracts import JSONSchemaHint


def schema_hint_from_model(
    model_type: type[BaseModel],
    *,
    name: str | None = None,
    strict: bool = True,
) -> JSONSchemaHint:
    """Build a provider-facing schema hint from a Pydantic model."""

    return JSONSchemaHint(
        name=name or model_type.__name__.lower(),
        schema=model_type.model_json_schema(),
        strict=strict,
    )
