"""Pydantic schemas for triage annotation datasets."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TriageDatasetCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = None


class TriageDatasetRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    created_by: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TriageDatasetListResponse(BaseModel):
    items: list[TriageDatasetRead]
    total: int


class TriageSliceMessageRead(BaseModel):
    interaction_id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class TriageSliceRead(BaseModel):
    session_id: UUID
    messages: list[TriageSliceMessageRead]


class TriageSlicesResponse(BaseModel):
    items: list[TriageSliceRead]


class TriageSlicesRequest(BaseModel):
    num_slices: int = Field(10, ge=1, le=200)
    slice_length: int = Field(8, ge=1, le=200)
    context_n: int = Field(4, ge=0, le=50)
    session_id: UUID | None = None
    seed: int | None = None


class TriageAnnotationUpsert(BaseModel):
    interaction_id: UUID
    expected_decision: str = Field(..., max_length=50, description="Usually 'assess' | 'skip'")
    notes: str | None = None
    context_n: int | None = Field(default=None, ge=0, le=50)


class TriageAnnotationsUpsertRequest(BaseModel):
    items: list[TriageAnnotationUpsert]


class TriageAnnotationRead(BaseModel):
    id: UUID
    dataset_id: UUID
    interaction_id: UUID
    expected_decision: str
    context_n: int
    context_messages: list[dict[str, Any]] | None
    notes: str | None
    labeled_by: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TriageAnnotationListResponse(BaseModel):
    items: list[TriageAnnotationRead]
    total: int


class TriageDatasetDetailResponse(BaseModel):
    dataset: TriageDatasetRead
    annotations: TriageAnnotationListResponse


class TriageExportToSuiteRequest(BaseModel):
    annotation_ids: list[UUID] | None = None
    limit: int | None = Field(default=None, ge=1, le=5000)
    seed: int | None = None
    suite_name: str | None = None


class TriageExportToSuiteResponse(BaseModel):
    suite_id: UUID
    created_cases: int
