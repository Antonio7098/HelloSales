"""AST-backed SQL validation for the governed analytics tool."""

from __future__ import annotations

import hashlib
from typing import cast

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from hello_sales_backend.modules.analytics_query.use_cases.ports import (
    AnalyticsCatalog,
    QueryProjection,
    ValidatedAnalyticsQuery,
)
from hello_sales_backend.shared.errors import app_error

_FORBIDDEN_NODE_KEYS = {
    "alter",
    "analyze",
    "attach",
    "command",
    "copy",
    "create",
    "delete",
    "describe",
    "detach",
    "drop",
    "except",
    "grant",
    "insert",
    "intersect",
    "into",
    "lock",
    "merge",
    "rollback",
    "show",
    "star",
    "transaction",
    "truncate",
    "union",
    "update",
    "use",
    "vacuum",
}
_AGGREGATE_NODE_KEYS = {"avg", "count", "max", "min", "sum"}


class SqlglotAnalyticsQueryValidator:
    """Validate one SQL statement against the semantic analytics catalog."""

    def __init__(self, *, default_max_rows: int) -> None:
        self._default_max_rows = default_max_rows

    def validate(
        self,
        *,
        catalog: AnalyticsCatalog,
        sql: str,
        max_rows: int,
    ) -> ValidatedAnalyticsQuery:
        statement = self._parse_statement(sql=sql, dialect=catalog.dialect)
        self._ensure_read_only(statement)
        relation_names, table_aliases = self._resolve_relations(statement=statement, catalog=catalog)
        projections = self._resolve_projections(
            statement=statement,
            catalog=catalog,
            relation_names=relation_names,
            table_aliases=table_aliases,
        )
        normalized_sql = statement.sql(dialect=catalog.dialect, pretty=False)
        risk_flags = self._build_risk_flags(
            statement=statement,
            relations=relation_names,
            projections=projections,
        )
        bounded_max_rows = max_rows or self._default_max_rows
        return ValidatedAnalyticsQuery(
            catalog_id=catalog.catalog_id,
            catalog_version=catalog.catalog_version,
            dialect=catalog.dialect,
            normalized_sql=normalized_sql,
            query_fingerprint=hashlib.sha256(normalized_sql.encode("utf-8")).hexdigest()[:16],
            relations=tuple(sorted(relation_names)),
            projections=tuple(projections),
            risk_flags=tuple(sorted(risk_flags)),
            max_rows=bounded_max_rows,
        )

    def _parse_statement(self, *, sql: str, dialect: str) -> exp.Expression:
        try:
            statements = [item for item in sqlglot.parse(sql, read=dialect) if item is not None]
        except ParseError as exc:
            raise app_error(
                "SQL did not parse successfully",
                code="analytics_query.validation.invalid_sql",
                category="validation",
                status_code=400,
                details={"dialect": dialect},
                operation="analytics_query.validator.parse",
                component="analytics_query",
                exc=exc,
            ) from exc
        if len(statements) != 1:
            raise app_error(
                "Exactly one SQL statement is allowed",
                code="analytics_query.validation.multiple_statements",
                category="validation",
                status_code=400,
                details={"statement_count": len(statements), "dialect": dialect},
                operation="analytics_query.validator.parse",
                component="analytics_query",
            )
        statement = statements[0]
        if not any(True for _ in statement.find_all(exp.Select)):
            raise app_error(
                "Only SELECT statements are allowed",
                code="analytics_query.validation.non_read_only",
                category="validation",
                status_code=400,
                details={"statement_type": statement.key},
                operation="analytics_query.validator.parse",
                component="analytics_query",
            )
        return cast(exp.Expression, statement)

    def _ensure_read_only(self, statement: exp.Expression) -> None:
        for node in statement.walk():
            if node.key in _FORBIDDEN_NODE_KEYS:
                raise app_error(
                    "SQL contains an unapproved construct",
                    code="analytics_query.validation.unsupported_construct",
                    category="validation",
                    status_code=400,
                    details={"construct": node.key},
                    operation="analytics_query.validator.ensure_read_only",
                    component="analytics_query",
                )
            if isinstance(node, exp.Anonymous) and node.name.lower() == "pg_sleep":
                raise app_error(
                    "SQL references an unapproved function",
                    code="analytics_query.validation.unsupported_construct",
                    category="validation",
                    status_code=400,
                    details={"construct": node.name.lower()},
                    operation="analytics_query.validator.ensure_read_only",
                    component="analytics_query",
                )

    def _resolve_relations(
        self,
        *,
        statement: exp.Expression,
        catalog: AnalyticsCatalog,
    ) -> tuple[set[str], dict[str, str]]:
        cte_names = self._cte_names(statement)
        relation_names: set[str] = set()
        table_aliases: dict[str, str] = {}
        for table in statement.find_all(exp.Table):
            table_name = table.name
            if not table_name or table_name in cte_names:
                continue
            if table_name not in catalog.relations:
                raise app_error(
                    "SQL references a relation outside the approved analytics catalog",
                    code="analytics_query.validation.forbidden_relation",
                    category="validation",
                    status_code=403,
                    details={
                        "relation": table_name,
                        "catalog_id": catalog.catalog_id,
                        "allowed_relations": sorted(catalog.relations),
                    },
                    operation="analytics_query.validator.resolve_relations",
                    component="analytics_query",
                )
            relation_names.add(table_name)
            table_aliases[table_name] = table_name
            alias_name = table.alias
            if alias_name:
                table_aliases[alias_name] = table_name
        if not relation_names:
            raise app_error(
                "SQL must read from at least one approved analytics relation",
                code="analytics_query.validation.missing_relation",
                category="validation",
                status_code=400,
                details={"catalog_id": catalog.catalog_id},
                operation="analytics_query.validator.resolve_relations",
                component="analytics_query",
            )
        return relation_names, table_aliases

    def _resolve_projections(
        self,
        *,
        statement: exp.Expression,
        catalog: AnalyticsCatalog,
        relation_names: set[str],
        table_aliases: dict[str, str],
    ) -> list[QueryProjection]:
        outer_select = statement if isinstance(statement, exp.Select) else statement.find(exp.Select)
        if not isinstance(outer_select, exp.Select):
            raise app_error(
                "Analytics query must resolve to one SELECT statement",
                code="analytics_query.validation.unsupported_construct",
                category="validation",
                status_code=400,
                details={"statement_type": statement.key},
                operation="analytics_query.validator.resolve_projections",
                component="analytics_query",
            )
        projections: list[QueryProjection] = []
        seen_output_names: set[str] = set()
        for projection in outer_select.expressions:
            output_name = projection.alias_or_name or projection.sql(dialect=catalog.dialect, pretty=False)
            if output_name in seen_output_names:
                raise app_error(
                    "Analytics query result columns must have unique output names",
                    code="analytics_query.validation.duplicate_output_column",
                    category="validation",
                    status_code=400,
                    details={"output_name": output_name},
                    operation="analytics_query.validator.resolve_projections",
                    component="analytics_query",
                )
            seen_output_names.add(output_name)
            source_columns = self._resolve_source_columns(
                expression=projection.unnest(),
                catalog=catalog,
                relation_names=relation_names,
                table_aliases=table_aliases,
            )
            projections.append(
                QueryProjection(
                    output_name=output_name,
                    data_type=source_columns[0][2] if source_columns else "derived",
                    semantic_type=source_columns[0][3] if source_columns else "derived",
                    description=source_columns[0][4] if len(source_columns) == 1 else None,
                    sensitivity=self._effective_sensitivity(source_columns),
                    source_columns=tuple(f"{relation}.{column}" for relation, column, *_ in source_columns),
                )
            )
        if not projections:
            raise app_error(
                "Analytics query must select at least one output column",
                code="analytics_query.validation.empty_projection",
                category="validation",
                status_code=400,
                operation="analytics_query.validator.resolve_projections",
                component="analytics_query",
            )
        return projections

    def _resolve_source_columns(
        self,
        *,
        expression: exp.Expression,
        catalog: AnalyticsCatalog,
        relation_names: set[str],
        table_aliases: dict[str, str],
    ) -> list[tuple[str, str, str, str, str | None, str]]:
        resolved: list[tuple[str, str, str, str, str | None, str]] = []
        for column in expression.find_all(exp.Column):
            table_name = column.text("table")
            column_name = column.name
            relation_name = self._resolve_column_relation(
                relation_names=relation_names,
                table_aliases=table_aliases,
                catalog=catalog,
                table_name=table_name,
                column_name=column_name,
            )
            column_meta = catalog.relations[relation_name].columns[column_name]
            resolved.append(
                (
                    relation_name,
                    column_name,
                    column_meta.data_type,
                    column_meta.semantic_type,
                    column_meta.description,
                    column_meta.sensitivity,
                )
            )
        return resolved

    def _resolve_column_relation(
        self,
        *,
        relation_names: set[str],
        table_aliases: dict[str, str],
        catalog: AnalyticsCatalog,
        table_name: str,
        column_name: str,
    ) -> str:
        if not column_name:
            raise app_error(
                "Analytics query contains an unsupported column reference",
                code="analytics_query.validation.unsupported_construct",
                category="validation",
                status_code=400,
                operation="analytics_query.validator.resolve_column_relation",
                component="analytics_query",
            )
        if table_name:
            mapped_relation = table_aliases.get(table_name)
            if mapped_relation is None:
                matching_relations = [
                    relation
                    for relation in relation_names
                    if column_name in catalog.relations[relation].columns
                ]
                if len(matching_relations) == 1:
                    return matching_relations[0]
                raise app_error(
                    "Analytics query references an unknown or derived relation alias",
                    code="analytics_query.validation.forbidden_relation",
                    category="validation",
                    status_code=403,
                    details={"relation_alias": table_name, "column": column_name},
                    operation="analytics_query.validator.resolve_column_relation",
                    component="analytics_query",
                )
            if column_name not in catalog.relations[mapped_relation].columns:
                raise app_error(
                    "Analytics query references an unknown catalog column",
                    code="analytics_query.validation.unknown_column",
                    category="validation",
                    status_code=400,
                    details={"relation": mapped_relation, "column": column_name},
                    operation="analytics_query.validator.resolve_column_relation",
                    component="analytics_query",
                )
            return mapped_relation
        candidates = [
            relation for relation in relation_names if column_name in catalog.relations[relation].columns
        ]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise app_error(
                "Analytics query references an unknown catalog column",
                code="analytics_query.validation.unknown_column",
                category="validation",
                status_code=400,
                details={"column": column_name},
                operation="analytics_query.validator.resolve_column_relation",
                component="analytics_query",
            )
        raise app_error(
            "Analytics query must qualify ambiguous columns when joining relations",
            code="analytics_query.validation.ambiguous_column",
            category="validation",
            status_code=400,
            details={"column": column_name, "candidate_relations": sorted(candidates)},
            operation="analytics_query.validator.resolve_column_relation",
            component="analytics_query",
        )

    def _build_risk_flags(
        self,
        *,
        statement: exp.Expression,
        relations: set[str],
        projections: list[QueryProjection],
    ) -> set[str]:
        risk_flags: set[str] = {"bounded_results"}
        if len(relations) > 1:
            risk_flags.add("joins_multiple_relations")
        if any(node.key in _AGGREGATE_NODE_KEYS for node in statement.walk()):
            risk_flags.add("aggregate_query")
        sensitivities = {projection.sensitivity for projection in projections}
        if "internal" in sensitivities:
            risk_flags.add("internal_columns_selected")
        if "restricted" in sensitivities:
            risk_flags.add("restricted_columns_selected")
        return risk_flags

    @staticmethod
    def _effective_sensitivity(
        source_columns: list[tuple[str, str, str, str, str | None, str]],
    ) -> str:
        if any(item[5] == "restricted" for item in source_columns):
            return "restricted"
        if any(item[5] == "internal" for item in source_columns):
            return "internal"
        return "public"

    @staticmethod
    def _cte_names(statement: exp.Expression) -> set[str]:
        with_expression = statement.args.get("with_")
        if with_expression is None:
            return set()
        return {cte.alias_or_name for cte in with_expression.expressions if cte.alias_or_name}
