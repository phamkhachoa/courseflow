from __future__ import annotations

from datetime import UTC, datetime
import re
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.contracts import ValidationResult, load_yaml
from enterprise_dp.semantic_metrics import validate_semantic_metric_registry


SUPPORTED_ENGINES = {"trino", "dremio"}
SQL_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$")


def write_semantic_view_manifest(
    root: str | Path,
    output_path: str | Path,
    *,
    engine: str = "all",
    generated_at: str | None = None,
) -> dict[str, Any]:
    manifest = build_semantic_view_manifest(root, engine=engine, generated_at=generated_at)
    result = validate_semantic_view_manifest(manifest)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return manifest


def build_semantic_view_manifest(
    root: str | Path,
    *,
    engine: str = "all",
    generated_at: str | None = None,
) -> dict[str, Any]:
    if engine != "all" and engine not in SUPPORTED_ENGINES:
        raise ValueError(f"engine must be one of {sorted(SUPPORTED_ENGINES | {'all'})}")
    platform_root = Path(root)
    registry_path = platform_root / "platform" / "serving" / "semantic-metrics.yaml"
    validation = validate_semantic_metric_registry(platform_root)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    registry = load_yaml(registry_path)
    engines = sorted(SUPPORTED_ENGINES) if engine == "all" else [engine]
    views = [
        build_metric_view(metric, engine_name)
        for metric in registry.get("metrics", [])
        if isinstance(metric, dict)
        for engine_name in engines
    ]
    return {
        "artifact_type": "semantic_views_manifest.v1",
        "manifest_version": 1,
        "generated_at": generated_at or utc_now(),
        "registry_uri": registry_path.as_posix(),
        "registry_hash": hash_file(registry_path),
        "engine": engine,
        "views": views,
        "summary": {
            "metric_count": len(registry.get("metrics", [])),
            "view_count": len(views),
            "engines": engines,
        },
    }


def build_metric_view(metric: dict[str, Any], engine: str) -> dict[str, Any]:
    metric_id = str(metric["metricId"])
    source = metric["source"]
    calculation = metric["calculation"]
    serving = metric["serving"]
    dimensions = list(metric.get("dimensions", []))
    grain = list(metric.get("grain", []))
    source_data_product = str(source["dataProduct"])
    view_name = serving["trinoView"] if engine == "trino" else serving["dremioVirtualDataset"]
    sql = render_metric_sql(
        view_name=str(view_name),
        source_data_product=source_data_product,
        group_columns=grain,
        expression=str(calculation["expressionSql"]),
        filters=metric.get("filters", []),
    )
    return {
        "metric_id": metric_id,
        "metric_name": metric.get("name"),
        "engine": engine,
        "view_name": view_name,
        "source_data_product": source_data_product,
        "time_column": source.get("timeColumn"),
        "grain": grain,
        "dimensions": dimensions,
        "expression_sql": calculation.get("expressionSql"),
        "referenced_columns": calculation.get("referencedColumns", []),
        "unit": calculation.get("unit"),
        "filters": metric.get("filters", []),
        "materialization": serving.get("materialization"),
        "use_cases": metric.get("useCases", []),
        "consumers": metric.get("consumers", []),
        "sql": sql,
    }


def render_metric_sql(
    *,
    view_name: str,
    source_data_product: str,
    group_columns: list[str],
    expression: str,
    filters: list[dict[str, Any]],
) -> str:
    select_lines = [f"  {column}" for column in group_columns]
    select_lines.append(f"  {expression} AS metric_value")
    select_sql = ",\n".join(select_lines)
    where_clause = render_where_clause(filters)
    group_by = f"\nGROUP BY {', '.join(group_columns)}" if group_columns else ""
    return (
        f"CREATE OR REPLACE VIEW {view_name} AS\n"
        f"SELECT\n"
        f"{select_sql}\n"
        f"FROM {source_data_product}"
        f"{where_clause}"
        f"{group_by};"
    )


def render_where_clause(filters: list[dict[str, Any]]) -> str:
    clauses = []
    for item in filters:
        if not isinstance(item, dict):
            continue
        column = item.get("column")
        operator = item.get("operator")
        values = item.get("values")
        if not isinstance(column, str) or not isinstance(operator, str) or not isinstance(values, list):
            continue
        clauses.append(render_filter(column, operator, values))
    return f"\nWHERE {' AND '.join(clauses)}" if clauses else ""


def render_filter(column: str, operator: str, values: list[Any]) -> str:
    rendered_values = [render_literal(value) for value in values]
    if operator == "equals":
        return f"{column} = {rendered_values[0]}"
    if operator == "in":
        return f"{column} IN ({', '.join(rendered_values)})"
    if operator == "not_in":
        return f"{column} NOT IN ({', '.join(rendered_values)})"
    operator_map = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    if operator in operator_map:
        return f"{column} {operator_map[operator]} {rendered_values[0]}"
    raise ValueError(f"unsupported filter operator: {operator}")


def render_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float):
        return str(value)
    text = str(value)
    if text.lower() == "true":
        return "TRUE"
    if text.lower() == "false":
        return "FALSE"
    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return text
    return "'" + text.replace("'", "''") + "'"


def validate_semantic_view_manifest(manifest: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    if manifest.get("artifact_type") != "semantic_views_manifest.v1":
        result.error(Path("semantic_views_manifest"), "artifact_type must be semantic_views_manifest.v1")
    if manifest.get("manifest_version") != 1:
        result.error(Path("semantic_views_manifest"), "manifest_version must be 1")
    views = manifest.get("views")
    if not isinstance(views, list) or not views:
        result.error(Path("semantic_views_manifest"), "views must be a non-empty list")
        return result
    result.checked_count += len(views)
    seen: set[tuple[str, str]] = set()
    for index, view in enumerate(views):
        validate_view(index, view, seen, result)
    return result


def validate_view(index: int, view: object, seen: set[tuple[str, str]], result: ValidationResult) -> None:
    path = Path(f"semantic_views_manifest.views[{index}]")
    if not isinstance(view, dict):
        result.error(path, "view must be an object")
        return
    metric_id = view.get("metric_id")
    engine = view.get("engine")
    view_name = view.get("view_name")
    source = view.get("source_data_product")
    sql = view.get("sql")
    if not isinstance(metric_id, str) or not metric_id:
        result.error(path, "metric_id must be a non-empty string")
    if engine not in SUPPORTED_ENGINES:
        result.error(path, f"engine must be one of {sorted(SUPPORTED_ENGINES)}")
    if not isinstance(view_name, str) or not SQL_IDENTIFIER.fullmatch(view_name):
        result.error(path, "view_name must be a dot-qualified SQL identifier")
    if not isinstance(source, str) or not SQL_IDENTIFIER.fullmatch(source):
        result.error(path, "source_data_product must be a dot-qualified SQL identifier")
    if isinstance(engine, str) and isinstance(view_name, str):
        key = (engine, view_name)
        if key in seen:
            result.error(path, f"duplicate view for engine/name: {engine} {view_name}")
        seen.add(key)
    if not isinstance(sql, str) or "CREATE OR REPLACE VIEW" not in sql:
        result.error(path, "sql must contain CREATE OR REPLACE VIEW")
    if isinstance(view_name, str) and isinstance(sql, str) and view_name not in sql:
        result.error(path, "sql must include view_name")
    if isinstance(source, str) and isinstance(sql, str) and source not in sql:
        result.error(path, "sql must include source_data_product")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
