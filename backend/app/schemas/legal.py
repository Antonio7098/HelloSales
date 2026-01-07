from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LegalPublicConfig(BaseModel):
    version: str
    termsUrl: str | None = None
    privacyUrl: str | None = None
    dpaUrl: str | None = None


class LegalConfigResponse(LegalPublicConfig):
    acceptedVersion: str | None = None
    acceptedAt: datetime | None = None
    needsAcceptance: bool


class LegalAcceptRequest(BaseModel):
    version: str | None = None
