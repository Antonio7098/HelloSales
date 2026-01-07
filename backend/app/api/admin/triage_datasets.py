"""Admin APIs for triage annotation datasets.

These endpoints support creating a triage-labeled dataset from production
interaction transcripts (slice sampling + per-message labeling).

They live under /admin/eval/triage/*.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin.dependencies import require_admin
from app.database import get_session
from app.models import (
    EvalTestCase,
    EvalTestSuite,
    Interaction,
    Session,
    TriageAnnotation,
    TriageDataset,
)
from app.schemas.triage_annotation import (
    TriageAnnotationListResponse,
    TriageAnnotationRead,
    TriageAnnotationsUpsertRequest,
    TriageDatasetCreate,
    TriageDatasetDetailResponse,
    TriageDatasetListResponse,
    TriageDatasetRead,
    TriageExportToSuiteRequest,
    TriageExportToSuiteResponse,
    TriageSliceMessageRead,
    TriageSliceRead,
    TriageSlicesRequest,
    TriageSlicesResponse,
)

router = APIRouter(prefix="/eval/triage", tags=["eval"])


def _map_expected_to_eval_label(value: str) -> str:
    raw = (value or "").strip().lower()
    if raw in {"assess", "skill_practice", "practice", "yes", "y", "true", "1"}:
        return "skill_practice"
    if raw in {"skip", "general_chatter", "chatter", "no", "n", "false", "0"}:
        return "general_chatter"
    # Default: treat unknown as skip to be conservative
    return "general_chatter"


@router.get("/datasets", response_model=TriageDatasetListResponse)
async def list_triage_datasets(
    session: AsyncSession = Depends(get_session),
) -> TriageDatasetListResponse:
    result = await session.execute(select(TriageDataset).order_by(TriageDataset.created_at.desc()))
    items = list(result.scalars().all())
    return TriageDatasetListResponse(
        items=[TriageDatasetRead.model_validate(x) for x in items],
        total=len(items),
    )


@router.post("/datasets", response_model=TriageDatasetRead)
async def create_triage_dataset(
    payload: TriageDatasetCreate,
    claims: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> TriageDatasetRead:
    created_by = None
    if isinstance(claims, dict):
        created_by = str(claims.get("email") or claims.get("sub") or "") or None

    dataset = TriageDataset(
        name=payload.name,
        description=payload.description,
        created_by=created_by,
    )
    session.add(dataset)
    await session.commit()
    await session.refresh(dataset)
    return TriageDatasetRead.model_validate(dataset)


@router.get("/datasets/{dataset_id}", response_model=TriageDatasetDetailResponse)
async def get_triage_dataset_detail(
    dataset_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> TriageDatasetDetailResponse:
    ds_result = await session.execute(select(TriageDataset).where(TriageDataset.id == dataset_id))
    dataset = ds_result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    total_result = await session.execute(
        select(func.count(TriageAnnotation.id)).where(TriageAnnotation.dataset_id == dataset_id)
    )
    total = int(total_result.scalar_one() or 0)

    ann_result = await session.execute(
        select(TriageAnnotation)
        .where(TriageAnnotation.dataset_id == dataset_id)
        .order_by(TriageAnnotation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    ann = list(ann_result.scalars().all())

    return TriageDatasetDetailResponse(
        dataset=TriageDatasetRead.model_validate(dataset),
        annotations=TriageAnnotationListResponse(
            items=[TriageAnnotationRead.model_validate(x) for x in ann],
            total=total,
        ),
    )


@router.post("/slices", response_model=TriageSlicesResponse)
async def sample_triage_slices(
    payload: TriageSlicesRequest,
    session: AsyncSession = Depends(get_session),
) -> TriageSlicesResponse:
    rng = random.Random(payload.seed)

    # Determine sessions to sample from
    session_ids: list[UUID] = []
    if payload.session_id is not None:
        session_ids = [payload.session_id]
    else:
        # Prefer sessions with enough interactions, using interaction_count when available.
        sess_result = await session.execute(
            select(Session.id)
            .where(Session.interaction_count >= payload.slice_length)
            .order_by(Session.created_at.desc())
            .limit(1000)
        )
        candidates = list(sess_result.scalars().all())
        if not candidates:
            return TriageSlicesResponse(items=[])
        session_ids = rng.choices(candidates, k=payload.num_slices)

    slices: list[TriageSliceRead] = []

    for sess_id in session_ids[: payload.num_slices]:
        count_result = await session.execute(
            select(func.count(Interaction.id)).where(Interaction.session_id == sess_id)
        )
        total = int(count_result.scalar_one() or 0)
        if total < payload.slice_length:
            continue

        start_idx = rng.randint(0, total - payload.slice_length)
        interactions_result = await session.execute(
            select(Interaction)
            .where(Interaction.session_id == sess_id)
            .order_by(Interaction.created_at.asc())
            .offset(start_idx)
            .limit(payload.slice_length)
        )
        interactions = list(interactions_result.scalars().all())
        if not interactions:
            continue

        messages = [
            TriageSliceMessageRead(
                interaction_id=it.id,
                session_id=it.session_id,
                role=it.role,
                content=it.content,
                created_at=it.created_at,
            )
            for it in interactions
        ]
        slices.append(TriageSliceRead(session_id=sess_id, messages=messages))

    return TriageSlicesResponse(items=slices)


@router.put("/datasets/{dataset_id}/annotations", response_model=TriageAnnotationListResponse)
async def upsert_triage_annotations(
    dataset_id: UUID,
    payload: TriageAnnotationsUpsertRequest,
    claims: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> TriageAnnotationListResponse:
    ds_result = await session.execute(select(TriageDataset).where(TriageDataset.id == dataset_id))
    dataset = ds_result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    labeled_by = None
    if isinstance(claims, dict):
        labeled_by = str(claims.get("email") or claims.get("sub") or "") or None

    saved: list[TriageAnnotation] = []

    for item in payload.items:
        interaction = await session.get(Interaction, item.interaction_id)
        if interaction is None:
            raise HTTPException(
                status_code=404, detail=f"Interaction not found: {item.interaction_id}"
            )

        if interaction.role != "user":
            raise HTTPException(
                status_code=400,
                detail=f"Only user interactions can be triage-labeled: {item.interaction_id}",
            )

        # Compute context snapshot to match production triage:
        # Take N preceding interactions within the same session (chronological order).
        context_n = item.context_n if item.context_n is not None else 4
        ctx_result = await session.execute(
            select(Interaction)
            .where(
                Interaction.session_id == interaction.session_id,
                Interaction.created_at < interaction.created_at,
            )
            .order_by(Interaction.created_at.desc())
            .limit(context_n)
        )
        previous = list(reversed(ctx_result.scalars().all()))
        context_messages: list[dict[str, Any]] = [
            {"role": ("user" if it.role == "user" else "assistant"), "content": it.content}
            for it in previous
        ]

        existing_result = await session.execute(
            select(TriageAnnotation).where(
                TriageAnnotation.dataset_id == dataset_id,
                TriageAnnotation.interaction_id == interaction.id,
            )
        )
        ann = existing_result.scalar_one_or_none()
        if ann is None:
            ann = TriageAnnotation(
                dataset_id=dataset_id,
                interaction_id=interaction.id,
                expected_decision=item.expected_decision,
                context_n=context_n,
                context_messages=context_messages,
                notes=item.notes,
                labeled_by=labeled_by,
            )
            session.add(ann)
        else:
            ann.expected_decision = item.expected_decision
            ann.context_n = context_n
            ann.context_messages = context_messages
            ann.notes = item.notes
            ann.labeled_by = labeled_by

        saved.append(ann)

    await session.commit()

    # Reload the saved annotations for response
    ids = [a.id for a in saved]
    rows_result = await session.execute(
        select(TriageAnnotation).where(TriageAnnotation.id.in_(ids))
    )
    rows = list(rows_result.scalars().all())

    return TriageAnnotationListResponse(
        items=[TriageAnnotationRead.model_validate(x) for x in rows],
        total=len(rows),
    )


@router.post("/datasets/{dataset_id}/export-suite", response_model=TriageExportToSuiteResponse)
async def export_triage_dataset_to_eval_suite(
    dataset_id: UUID,
    payload: TriageExportToSuiteRequest,
    claims: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> TriageExportToSuiteResponse:
    ds_result = await session.execute(select(TriageDataset).where(TriageDataset.id == dataset_id))
    dataset = ds_result.scalar_one_or_none()
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    rng = random.Random(payload.seed)

    # Choose annotations
    if payload.annotation_ids is not None:
        chosen_ids = payload.annotation_ids
    else:
        id_result = await session.execute(
            select(TriageAnnotation.id).where(TriageAnnotation.dataset_id == dataset_id)
        )
        all_ids = list(id_result.scalars().all())
        if not all_ids:
            raise HTTPException(status_code=400, detail="Dataset has no annotations")
        if payload.limit is not None and payload.limit < len(all_ids):
            chosen_ids = rng.sample(all_ids, k=payload.limit)
        else:
            chosen_ids = all_ids

    # Create suite
    created_by = None
    if isinstance(claims, dict):
        created_by = str(claims.get("email") or claims.get("sub") or "") or None

    name = (
        payload.suite_name
        or f"Triage: {dataset.name} ({datetime.utcnow().isoformat(timespec='seconds')})"
    )
    suite = EvalTestSuite(name=name, description=dataset.description, created_by=created_by)
    session.add(suite)
    await session.flush()

    # Load annotations + interactions
    ann_result = await session.execute(
        select(TriageAnnotation, Interaction)
        .join(Interaction, Interaction.id == TriageAnnotation.interaction_id)
        .where(
            TriageAnnotation.id.in_(chosen_ids),
            Interaction.role == "user",
        )
    )
    pairs = list(ann_result.all())

    created_cases = 0
    for ann, interaction in pairs:
        expected_eval = _map_expected_to_eval_label(ann.expected_decision)
        metadata: dict[str, Any] = {
            "triage_dataset_id": str(dataset.id),
            "triage_annotation_id": str(ann.id),
            "triage_expected_decision_raw": ann.expected_decision,
            "triage_context_n": ann.context_n,
            "triage_context_messages": ann.context_messages,
        }

        case = EvalTestCase(
            suite_id=suite.id,
            name=f"Triage {str(ann.id)[:8]}",
            source_interaction_id=interaction.id,
            source_session_id=interaction.session_id,
            transcript=interaction.content,
            context_summary=None,
            tracked_skills=None,
            expected_triage_decision=expected_eval,
            triage_notes=ann.notes,
            expected_assessments=None,
            metadata_json=metadata,
            labeled_by=ann.labeled_by,
            labeled_at=ann.updated_at,
        )
        session.add(case)
        created_cases += 1

    await session.commit()
    return TriageExportToSuiteResponse(suite_id=suite.id, created_cases=created_cases)
