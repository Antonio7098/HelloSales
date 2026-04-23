"""Opaque context entity refs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from hello_sales_backend.modules.entity_operations.use_cases.ports import (
    ContextEntityRefResolverPort,
    EntityMutationExecutorPort,
    EntitySnapshot,
    IssuedEntityRef,
)
from hello_sales_backend.modules.entity_operations.use_cases.views import EntityOperationContext
from hello_sales_backend.shared.errors import app_error


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class _EntityRefPayload:
    entity_type: str
    entity_id: str
    display_label: str
    version: str
    allowed_operations: tuple[str, ...]
    session_id: str | None
    actor_id: str | None
    origin_run_id: str | None
    expires_at: str | None


class SignedContextEntityRefResolver(ContextEntityRefResolverPort):
    """Issue and validate signed opaque entity refs."""

    def __init__(
        self,
        *,
        executor: EntityMutationExecutorPort,
        signing_secret: str,
    ) -> None:
        self._executor = executor
        self._signing_secret = signing_secret.encode("utf-8")

    def issue_ref(
        self,
        *,
        snapshot: EntitySnapshot,
        allowed_operations: tuple[str, ...],
        ttl_seconds: int,
        context: EntityOperationContext,
    ) -> IssuedEntityRef:
        expires_at = _utc_now() + timedelta(seconds=ttl_seconds)
        payload = _EntityRefPayload(
            entity_type=snapshot.entity_type,
            entity_id=snapshot.entity_id,
            display_label=snapshot.display_label,
            version=snapshot.version,
            allowed_operations=allowed_operations,
            session_id=context.session_id,
            actor_id=context.actor_id,
            origin_run_id=context.run_id,
            expires_at=expires_at.isoformat(),
        )
        token = self._encode(payload)
        return IssuedEntityRef(
            entity_ref=f"ctx_entity_{token}",
            entity_type=snapshot.entity_type,
            entity_id=snapshot.entity_id,
            display_label=snapshot.display_label,
            version=snapshot.version,
            allowed_operations=allowed_operations,
            expires_at=expires_at,
        )

    async def resolve_ref(
        self,
        *,
        entity_ref: str,
        required_operation: str,
        context: EntityOperationContext,
    ) -> IssuedEntityRef:
        payload = self._decode(entity_ref)
        expires_at = self._parse_expiry(payload.expires_at, entity_ref=entity_ref)
        if expires_at is not None and expires_at <= _utc_now():
            raise app_error(
                "Context entity ref has expired",
                code="entity_ref.expired",
                category="validation",
                status_code=410,
                severity="warning",
                details={"entity_ref": entity_ref},
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        if payload.session_id is not None and context.session_id != payload.session_id:
            raise app_error(
                "Context entity ref belongs to a different session",
                code="entity_ref.wrong_session",
                category="validation",
                status_code=403,
                severity="warning",
                details={
                    "entity_ref": entity_ref,
                    "session_id": context.session_id,
                },
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        if payload.actor_id is not None and context.actor_id != payload.actor_id:
            raise app_error(
                "Context entity ref is not authorized for this actor",
                code="entity_ref.unauthorized",
                category="validation",
                status_code=403,
                severity="warning",
                details={"entity_ref": entity_ref},
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        if required_operation not in payload.allowed_operations:
            raise app_error(
                "Context entity ref does not allow the requested operation",
                code="entity_ref.unauthorized",
                category="validation",
                status_code=403,
                severity="warning",
                details={
                    "entity_ref": entity_ref,
                    "required_operation": required_operation,
                    "allowed_operations": list(payload.allowed_operations),
                },
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        snapshot = await self._executor.get_entity(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
        )
        if snapshot is None:
            raise app_error(
                "Context entity ref does not resolve to a known entity",
                code="entity_ref.unknown",
                category="validation",
                status_code=404,
                severity="warning",
                details={"entity_ref": entity_ref},
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        if snapshot.version != payload.version:
            raise app_error(
                "Context entity ref is stale for the current entity version",
                code="entity_ref.stale",
                category="validation",
                status_code=409,
                severity="warning",
                details={
                    "entity_ref": entity_ref,
                    "entity_type": payload.entity_type,
                    "expected_version": payload.version,
                    "current_version": snapshot.version,
                },
                operation="entity_ref.resolve",
                component="entity_operations",
            )
        return IssuedEntityRef(
            entity_ref=entity_ref,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            display_label=payload.display_label,
            version=payload.version,
            allowed_operations=payload.allowed_operations,
            expires_at=expires_at,
        )

    def _encode(self, payload: _EntityRefPayload) -> str:
        payload_json = json.dumps(asdict(payload), separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(self._signing_secret, payload_json, hashlib.sha256).hexdigest()
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode("ascii").rstrip("=")
        return f"{payload_b64}.{signature}"

    def _decode(self, entity_ref: str) -> _EntityRefPayload:
        prefix = "ctx_entity_"
        if not entity_ref.startswith(prefix):
            raise self._unknown(entity_ref)
        token = entity_ref.removeprefix(prefix)
        payload_part, separator, signature = token.partition(".")
        if separator != "." or not payload_part or not signature:
            raise self._unknown(entity_ref)
        try:
            padding = "=" * (-len(payload_part) % 4)
            payload_json = base64.urlsafe_b64decode(f"{payload_part}{padding}".encode("ascii"))
            expected_signature = hmac.new(self._signing_secret, payload_json, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_signature, signature):
                raise self._unknown(entity_ref)
            payload = json.loads(payload_json.decode("utf-8"))
            return _EntityRefPayload(
                entity_type=str(payload["entity_type"]),
                entity_id=str(payload["entity_id"]),
                display_label=str(payload["display_label"]),
                version=str(payload["version"]),
                allowed_operations=tuple(str(item) for item in payload.get("allowed_operations", [])),
                session_id=None if payload.get("session_id") is None else str(payload["session_id"]),
                actor_id=None if payload.get("actor_id") is None else str(payload["actor_id"]),
                origin_run_id=None if payload.get("origin_run_id") is None else str(payload["origin_run_id"]),
                expires_at=None if payload.get("expires_at") is None else str(payload["expires_at"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise self._unknown(entity_ref, exc=exc) from exc

    @staticmethod
    def _parse_expiry(expires_at: str | None, *, entity_ref: str) -> datetime | None:
        if expires_at is None:
            return None
        try:
            parsed = datetime.fromisoformat(expires_at)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        except ValueError as exc:
            raise app_error(
                "Context entity ref expiry could not be parsed",
                code="entity_ref.unknown",
                category="validation",
                status_code=400,
                severity="warning",
                details={"entity_ref": entity_ref},
                operation="entity_ref.resolve",
                component="entity_operations",
                exc=exc,
            ) from exc

    @staticmethod
    def _unknown(entity_ref: str, *, exc: Exception | None = None) -> Exception:
        return app_error(
            "Context entity ref is invalid or unknown",
            code="entity_ref.unknown",
            category="validation",
            status_code=404,
            severity="warning",
            details={"entity_ref": entity_ref},
            operation="entity_ref.resolve",
            component="entity_operations",
            exc=exc,
        )
