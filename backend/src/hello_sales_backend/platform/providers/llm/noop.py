"""Backward-compatible noop provider shim."""

from hello_sales_backend.platform.llm.providers.noop import NoopLLMProvider as NoopChatModel

__all__ = ["NoopChatModel"]
