"""Tavily web-search provider adapter."""

from __future__ import annotations

from typing import Any, cast

import httpx
from pydantic import ValidationError

from hello_sales_backend.platform.observability.logging import get_logger
from hello_sales_backend.platform.observability.redaction import redact_mapping
from hello_sales_backend.platform.web_search.contracts import (
    WebSearchCallContext,
    WebSearchProviderPort,
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)
from hello_sales_backend.shared.errors import AppError, app_error

_MAX_PROVIDER_ERROR_BODY_LENGTH = 1200


def _response_body_for_diagnostics(response: httpx.Response | None) -> object:
    """Return a bounded provider response body for error diagnostics."""

    if response is None:
        return None
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if isinstance(payload, str) and len(payload) > _MAX_PROVIDER_ERROR_BODY_LENGTH:
        return f"{payload[:_MAX_PROVIDER_ERROR_BODY_LENGTH]}..."
    return payload


class TavilyWebSearchProvider(WebSearchProviderPort):
    """Provider adapter for Tavily's search API."""

    provider_name = "tavily"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        base_url: str = "https://api.tavily.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._logger = get_logger("hello_sales_backend.providers.web_search")
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None

    async def search(
        self,
        request: WebSearchRequest,
        *,
        context: WebSearchCallContext | None = None,
    ) -> WebSearchResponse:
        endpoint = f"{self._base_url}/search"
        payload: dict[str, object] = {
            "api_key": self._api_key,
            "query": request.query,
            "max_results": request.max_results,
            "search_depth": request.search_depth,
            "topic": request.topic,
            "include_raw_content": request.include_raw_content,
        }
        if request.time_range:
            payload["time_range"] = request.time_range
        if request.include_domains:
            payload["include_domains"] = list(request.include_domains)
        if request.exclude_domains:
            payload["exclude_domains"] = list(request.exclude_domains)
        if request.country:
            payload["country"] = request.country
        self._logger.info(
            "provider.web_search.started",
            provider=self.provider_name,
            endpoint=endpoint,
            request=redact_mapping(
                {
                    "api_key": self._api_key,
                    "query_length": len(request.query),
                    "max_results": request.max_results,
                    "search_depth": request.search_depth,
                    "topic": request.topic,
                    "request_id": context.request_id if context else None,
                    "trace_id": context.trace_id if context else None,
                }
            ),
        )
        try:
            response = await self._http_client.post(endpoint, json=payload)
            response.raise_for_status()
            body = cast(dict[str, Any], response.json())
            provider_request_id = response.headers.get("x-request-id") or response.headers.get("x-tavily-request-id")
            normalized = self._normalize_response(
                body,
                request=request,
                provider_request_id=provider_request_id,
            )
            self._logger.info(
                "provider.web_search.completed",
                provider=self.provider_name,
                result_count=len(normalized.results),
                request_id=context.request_id if context else None,
                trace_id=context.trace_id if context else None,
            )
            return normalized
        except (ValueError, TypeError, ValidationError) as exc:
            raise app_error(
                "Web search provider returned a malformed response",
                code="provider.web_search.malformed_response",
                category="provider",
                status_code=502,
                retryable=False,
                details={"provider": self.provider_name, "endpoint": endpoint},
                operation="provider.web_search.search",
                component="provider",
                exc=exc,
            ) from exc
        except httpx.HTTPError as exc:
            raise self._map_http_error(exc, endpoint=endpoint) from exc

    def _normalize_response(
        self,
        payload: dict[str, Any],
        *,
        request: WebSearchRequest,
        provider_request_id: str | None,
    ) -> WebSearchResponse:
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise ValueError("Tavily response results must be a list")
        results: list[WebSearchResult] = []
        for raw_result in raw_results:
            if not isinstance(raw_result, dict):
                continue
            title = str(raw_result.get("title") or "").strip()
            url = str(raw_result.get("url") or "").strip()
            if not title or not url:
                continue
            published_at = raw_result.get("published_date") or raw_result.get("published_at")
            score = raw_result.get("score")
            results.append(
                WebSearchResult(
                    title=title,
                    url=url,
                    snippet=str(raw_result.get("content") or "").strip() or None,
                    content=str(raw_result.get("raw_content") or "").strip() or None,
                    published_at=str(published_at).strip() if published_at else None,
                    score=float(score) if isinstance(score, (int, float)) else None,
                    source_provider=self.provider_name,
                    provider_request_id=provider_request_id,
                    raw_metadata={
                        "favicon": raw_result.get("favicon"),
                        "score": score,
                    },
                )
            )
        return WebSearchResponse(
            provider=self.provider_name,
            query=str(payload.get("query") or request.query),
            results=results,
            provider_request_id=provider_request_id,
            answer=str(payload.get("answer")).strip() if payload.get("answer") else None,
            raw_metadata={
                "response_time": payload.get("response_time"),
                "follow_up_questions": payload.get("follow_up_questions"),
            },
        )

    def _map_http_error(self, exc: httpx.HTTPError, *, endpoint: str) -> AppError:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", 502) or 502
        response_body = _response_body_for_diagnostics(response)
        self._logger.exception(
            "provider.web_search.failed",
            provider=self.provider_name,
            endpoint=endpoint,
            response_status_code=status_code if isinstance(exc, httpx.HTTPStatusError) else None,
            provider_response=response_body,
        )
        error_code = "provider.web_search.http_failure"
        if isinstance(exc, httpx.TimeoutException):
            error_code = "provider.web_search.timeout"
        elif isinstance(exc, httpx.HTTPStatusError):
            if status_code == 400:
                error_code = "provider.web_search.bad_request"
            elif status_code in {401, 403}:
                error_code = "provider.web_search.authentication_failed"
            elif status_code == 429:
                error_code = "provider.web_search.rate_limit"
            elif status_code >= 500:
                error_code = "provider.web_search.remote_5xx"
        return app_error(
            "Web search provider request failed",
            code=error_code,
            category="provider",
            status_code=status_code if isinstance(exc, httpx.HTTPStatusError) else 502,
            retryable=isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))
            or (isinstance(exc, httpx.HTTPStatusError) and status_code in {408, 409, 425, 429, 500, 502, 503, 504}),
            details={
                "provider": self.provider_name,
                "endpoint": endpoint,
                "timeout_seconds": self._timeout_seconds,
                "response_status_code": status_code if isinstance(exc, httpx.HTTPStatusError) else None,
                "provider_request_id": getattr(response, "headers", {}).get("x-request-id"),
                "provider_response": response_body,
            },
            operation="provider.web_search.search",
            component="provider",
            exc=exc,
        )

    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()
