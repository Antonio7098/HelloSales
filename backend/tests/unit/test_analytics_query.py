from __future__ import annotations

from pathlib import Path

import pytest

from hello_sales_backend.modules.analytics_query.infra.catalogs import YamlAnalyticsCatalogStore
from hello_sales_backend.modules.analytics_query.infra.redaction import AnalyticsResultRedactor
from hello_sales_backend.modules.analytics_query.infra.validator import (
    SqlglotAnalyticsQueryValidator,
)
from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    AnalyticsCatalogColumn,
    AnalyticsCatalogRelation,
    ExecutedAnalyticsQuery,
    QueryProjection,
    ValidatedAnalyticsQuery,
)
from hello_sales_backend.shared.errors import AppError


def _catalog() -> AnalyticsCatalog:
    return AnalyticsCatalog(
        catalog_id="scaffold_stage",
        catalog_version="2026-04-21",
        dialect="postgres",
        description="test catalog",
        relations={
            "analytics_daily_pipeline": AnalyticsCatalogRelation(
                name="analytics_daily_pipeline",
                description="pipeline metrics",
                columns={
                    "lead_source": AnalyticsCatalogColumn(
                        name="lead_source",
                        data_type="text",
                        description="lead source",
                        semantic_type="dimension",
                        sensitivity="public",
                    ),
                    "meetings_booked": AnalyticsCatalogColumn(
                        name="meetings_booked",
                        data_type="integer",
                        description="meetings booked",
                        semantic_type="metric",
                        sensitivity="public",
                    ),
                    "pipeline_amount": AnalyticsCatalogColumn(
                        name="pipeline_amount",
                        data_type="numeric",
                        description="pipeline amount",
                        semantic_type="currency",
                        sensitivity="internal",
                    ),
                },
            ),
            "analytics_rep_performance": AnalyticsCatalogRelation(
                name="analytics_rep_performance",
                description="rep metrics",
                columns={
                    "rep_name": AnalyticsCatalogColumn(
                        name="rep_name",
                        data_type="text",
                        description="rep name",
                        semantic_type="dimension",
                        sensitivity="internal",
                    ),
                    "owner_email": AnalyticsCatalogColumn(
                        name="owner_email",
                        data_type="text",
                        description="owner email",
                        semantic_type="pii",
                        sensitivity="restricted",
                    ),
                },
            ),
        },
    )


def test_yaml_catalog_store_loads_manifest(tmp_path: Path) -> None:
    catalog_dir = tmp_path / "catalogs"
    catalog_dir.mkdir()
    (catalog_dir / "catalog.yaml").write_text(
        """
catalog_id: smoke_catalog
catalog_version: 1
dialect: postgres
description: Smoke catalog
relations:
  - name: analytics_daily_pipeline
    description: Daily pipeline metrics
    columns:
      - name: lead_source
        data_type: text
        semantic_type: dimension
        sensitivity: public
        description: Lead source
""".strip(),
        encoding="utf-8",
    )

    catalog = YamlAnalyticsCatalogStore(catalog_dir).get_catalog("smoke_catalog")

    assert catalog.catalog_id == "smoke_catalog"
    assert catalog.dialect == "postgres"
    assert "analytics_daily_pipeline" in catalog.relations


def test_validator_rejects_multiple_statements() -> None:
    validator = SqlglotAnalyticsQueryValidator(default_max_rows=25)

    with pytest.raises(AppError) as exc_info:
        validator.validate(
            catalog=_catalog(),
            sql="SELECT lead_source FROM analytics_daily_pipeline; SELECT 1",
            max_rows=10,
        )

    assert exc_info.value.code == "analytics_query.validation.multiple_statements"


def test_validator_classifies_join_and_sensitive_projections() -> None:
    validator = SqlglotAnalyticsQueryValidator(default_max_rows=25)

    result = validator.validate(
        catalog=_catalog(),
        sql=(
            "SELECT p.lead_source, p.pipeline_amount, r.rep_name, r.owner_email "
            "FROM analytics_daily_pipeline AS p "
            "JOIN analytics_rep_performance AS r ON 1 = 1"
        ),
        max_rows=10,
    )

    sensitivities = {projection.output_name: projection.sensitivity for projection in result.projections}
    assert sensitivities["lead_source"] == "public"
    assert sensitivities["pipeline_amount"] == "internal"
    assert sensitivities["rep_name"] == "internal"
    assert sensitivities["owner_email"] == "restricted"
    assert "joins_multiple_relations" in result.risk_flags
    assert "internal_columns_selected" in result.risk_flags
    assert "restricted_columns_selected" in result.risk_flags


def test_redactor_redacts_restricted_values_and_truncates_long_strings() -> None:
    redactor = AnalyticsResultRedactor(max_cell_length=12)
    query = ValidatedAnalyticsQuery(
        catalog_id="scaffold_stage",
        catalog_version="2026-04-21",
        dialect="postgres",
        normalized_sql="SELECT lead_source, owner_email, summary FROM analytics_rep_performance",
        query_fingerprint="abc123",
        relations=("analytics_rep_performance",),
        projections=(
            QueryProjection(
                output_name="lead_source",
                data_type="text",
                semantic_type="dimension",
                description="lead source",
                sensitivity="public",
            ),
            QueryProjection(
                output_name="owner_email",
                data_type="text",
                semantic_type="pii",
                description="owner email",
                sensitivity="restricted",
            ),
            QueryProjection(
                output_name="summary",
                data_type="text",
                semantic_type="derived",
                description="summary",
                sensitivity="public",
            ),
        ),
        risk_flags=("restricted_columns_selected",),
        max_rows=5,
    )
    execution = ExecutedAnalyticsQuery(
        columns=("lead_source", "owner_email", "summary"),
        rows=(
            {
                "lead_source": "web",
                "owner_email": "rep@example.com",
                "summary": "abcdefghijklmnopqrstuvwxyz",
            },
        ),
        truncated=False,
    )

    columns, rows = redactor.redact(
        catalog=_catalog(),
        query=query,
        execution=execution,
        execution_time_ms=5,
    )

    assert columns[1]["redacted"] is True
    assert rows[0]["lead_source"] == "web"
    assert rows[0]["owner_email"] == "***REDACTED***"
    assert rows[0]["summary"] == "abcdefghi..."
