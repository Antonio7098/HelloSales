"""Views for dashboard data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DashboardDataEntryView(BaseModel):
    """One governed dashboard data entry."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str
    dataset_key: str
    sequence_no: int
    section_label: str
    prompt_text: str
    answer_type: str
    example_answer: str


class DashboardDataSectionView(BaseModel):
    """One section of dashboard data entries."""

    model_config = ConfigDict(extra="forbid")

    dataset_key: str
    section_label: str
    entries: list[DashboardDataEntryView] = Field(default_factory=list)


class DashboardDataListView(BaseModel):
    """Top-level dashboard data response."""

    model_config = ConfigDict(extra="forbid")

    total_entries: int
    sections: list[DashboardDataSectionView] = Field(default_factory=list)
