from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, unquote

import pyarrow as pa
import pyarrow.parquet as pq
import pyiceberg
from pyiceberg.catalog import load_catalog

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.live_lakehouse_smoke import (
    DEFAULT_BUILT_AT,
    DEFAULT_EVALUATION_TIME,
    DEFAULT_FINANCE_SCHEMA_ID,
    DEFAULT_GENERATED_AT,
    DEFAULT_INGESTED_AT,
    DEFAULT_SNAPSHOT_ID,
    write_live_lakehouse_smoke_report,
)


@dataclass(frozen=True)
class IcebergCatalogSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_iceberg_catalog_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    catalog_name: str = "local_finance_iceberg",
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-iceberg-catalog-smoke",
    environment: str = "local",
    generated_at: str | None = None,
) -> IcebergCatalogSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    live_report_path, live_report = load_or_create_live_report(
        platform_root,
        target_dir,
        live_lakehouse_smoke_report_path=live_lakehouse_smoke_report_path,
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated,
    )
    catalog_dir = target_dir / "catalog"
    warehouse_dir = target_dir / "warehouse"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    warehouse_dir.mkdir(parents=True, exist_ok=True)
    catalog_db_path = catalog_dir / "iceberg-catalog.db"
    catalog_uri = f"sqlite:///{catalog_db_path.resolve()}"
    warehouse_uri = warehouse_dir.resolve().as_uri()
    catalog = load_catalog(
        catalog_name,
        **{
            "type": "sql",
            "uri": catalog_uri,
            "warehouse": warehouse_uri,
        },
    )

    table_results = [
        commit_iceberg_table(catalog, commit)
        for commit in live_report.get("table_commits", [])
        if isinstance(commit, dict)
    ]
    failed_checks = failed_iceberg_checks(live_report, table_results, catalog_db_path)
    report = {
        "artifact_type": "iceberg_catalog_smoke_report.v1",
        "report_version": 1,
        "capability_id": "bronze-lakehouse-evidence",
        "report_id": f"iceberg-catalog-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "primary_output": live_report.get("primary_output"),
        "runtime_scope": {
            "mode": "local_pyiceberg_sql_catalog_file_warehouse",
            "covered": [
                "pyiceberg_dependency_loaded",
                "sqlite_iceberg_catalog_created",
                "bronze_silver_gold_iceberg_namespaces_created",
                "bronze_silver_gold_iceberg_tables_created",
                "iceberg_snapshot_committed",
                "iceberg_metadata_file_hash_evidence",
                "iceberg_table_scan_readback",
            ],
            "not_covered": [
                "minio_object_store_iceberg_warehouse",
                "trino_iceberg_connector",
                "minio_federated_query",
                "hive_nessie_or_rest_catalog_service",
                "production_catalog_concurrency_locking",
                "runtime_security_enforcement",
            ],
        },
        "iceberg": {
            "pyiceberg_version": pyiceberg.__version__,
            "catalog_name": catalog_name,
            "catalog_type": "sql",
            "catalog_uri": catalog_uri,
            "catalog_db_path": catalog_db_path.as_posix(),
            "catalog_db_hash": hash_file(catalog_db_path) if catalog_db_path.is_file() else None,
            "warehouse_uri": warehouse_uri,
            "warehouse_path": warehouse_dir.as_posix(),
        },
        "live_lakehouse_smoke": {
            "path": live_report_path.as_posix(),
            "hash": hash_file(live_report_path),
            "passed": live_report.get("passed") is True,
        },
        "table_commits": table_results,
        "summary": {
            "table_count": len(table_results),
            "iceberg_table_passed_count": sum(1 for item in table_results if item.get("passed") is True),
            "snapshot_commit_count": sum(1 for item in table_results if item.get("snapshot_id") is not None),
            "metadata_file_count": sum(1 for item in table_results if item.get("metadata_hash")),
            "readback_passed_count": sum(1 for item in table_results if item.get("readback_passed") is True),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return IcebergCatalogSmokeResult(output_path=target, report=report)


def load_or_create_live_report(
    platform_root: Path,
    target_dir: Path,
    *,
    live_lakehouse_smoke_report_path: str | Path | None,
    use_case_id: str,
    release_id: str,
    environment: str,
    generated_at: str,
) -> tuple[Path, dict[str, Any]]:
    if live_lakehouse_smoke_report_path:
        live_report_path = Path(live_lakehouse_smoke_report_path)
        return live_report_path, load_json(live_report_path)
    live_result = write_live_lakehouse_smoke_report(
        platform_root,
        target_dir / "live-lakehouse-smoke-report.json",
        output_dir=target_dir / "live-lakehouse-run",
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated_at,
        ingested_at=DEFAULT_INGESTED_AT,
        built_at=DEFAULT_BUILT_AT,
        evaluation_time=DEFAULT_EVALUATION_TIME,
        schema_id=DEFAULT_FINANCE_SCHEMA_ID,
        snapshot_id=DEFAULT_SNAPSHOT_ID,
    )
    return live_result.output_path, live_result.report


def commit_iceberg_table(catalog: Any, commit: dict[str, Any]) -> dict[str, Any]:
    data_product = str(commit.get("data_product"))
    namespace, table_name = split_data_product(data_product)
    identifier = f"{namespace}.{table_name}"
    parquet_path = Path(str(commit.get("parquet_path")))
    source_table = normalize_table_for_iceberg(pq.read_table(parquet_path))
    catalog.create_namespace_if_not_exists(namespace)
    iceberg_table = catalog.create_table(identifier, schema=source_table.schema)
    iceberg_table.append(source_table)
    loaded_table = catalog.load_table(identifier)
    readback = loaded_table.scan().to_arrow()
    snapshots = loaded_table.snapshots()
    snapshot = snapshots[-1] if snapshots else None
    metadata_location = str(getattr(loaded_table, "metadata_location", "") or "")
    metadata_path = file_uri_to_path(metadata_location)
    manifest_list = str(getattr(snapshot, "manifest_list", "") or "") if snapshot else None
    manifest_list_path = file_uri_to_path(manifest_list) if manifest_list else None
    readback_passed = readback.num_rows == commit.get("row_count") == source_table.num_rows
    return {
        "data_product": data_product,
        "namespace": namespace,
        "table": table_name,
        "identifier": identifier,
        "source_parquet_path": parquet_path.as_posix(),
        "source_parquet_hash": hash_file(parquet_path),
        "source_row_count": source_table.num_rows,
        "source_column_count": source_table.num_columns,
        "null_type_columns_normalized": null_type_columns(pq.read_table(parquet_path).schema),
        "iceberg_schema": [{"name": field.name, "type": str(field.type)} for field in source_table.schema],
        "metadata_location": metadata_location,
        "metadata_hash": hash_file(metadata_path) if metadata_path and metadata_path.is_file() else None,
        "manifest_list": manifest_list,
        "manifest_list_hash": hash_file(manifest_list_path) if manifest_list_path and manifest_list_path.is_file() else None,
        "snapshot_id": str(getattr(snapshot, "snapshot_id", "")) if snapshot else None,
        "sequence_number": getattr(snapshot, "sequence_number", None) if snapshot else None,
        "snapshot_summary": snapshot_summary(snapshot),
        "readback_row_count": readback.num_rows,
        "readback_column_count": readback.num_columns,
        "readback_passed": readback_passed,
        "passed": readback_passed and snapshot is not None and metadata_path is not None and metadata_path.is_file(),
    }


def normalize_table_for_iceberg(table: pa.Table) -> pa.Table:
    normalized_schema = pa.schema([normalize_field_for_iceberg(field) for field in table.schema])
    if normalized_schema.equals(table.schema, check_metadata=False):
        return table
    return table.cast(normalized_schema)


def normalize_field_for_iceberg(field: pa.Field) -> pa.Field:
    return pa.field(field.name, normalize_type_for_iceberg(field.type), nullable=field.nullable, metadata=field.metadata)


def normalize_type_for_iceberg(data_type: pa.DataType) -> pa.DataType:
    if pa.types.is_null(data_type):
        return pa.string()
    if pa.types.is_struct(data_type):
        return pa.struct([normalize_field_for_iceberg(field) for field in data_type])
    if pa.types.is_list(data_type):
        return pa.list_(normalize_type_for_iceberg(data_type.value_type))
    if pa.types.is_large_list(data_type):
        return pa.large_list(normalize_type_for_iceberg(data_type.value_type))
    if pa.types.is_map(data_type):
        return pa.map_(normalize_type_for_iceberg(data_type.key_type), normalize_type_for_iceberg(data_type.item_type))
    return data_type


def null_type_columns(schema: pa.Schema) -> list[str]:
    columns: list[str] = []
    for field in schema:
        collect_null_type_columns(field, field.name, columns)
    return columns


def collect_null_type_columns(field: pa.Field, path: str, columns: list[str]) -> None:
    data_type = field.type
    if pa.types.is_null(data_type):
        columns.append(path)
        return
    if pa.types.is_struct(data_type):
        for child in data_type:
            collect_null_type_columns(child, f"{path}.{child.name}", columns)
    elif pa.types.is_list(data_type) or pa.types.is_large_list(data_type):
        child = pa.field("item", data_type.value_type)
        collect_null_type_columns(child, f"{path}[]", columns)
    elif pa.types.is_map(data_type):
        collect_null_type_columns(pa.field("key", data_type.key_type), f"{path}.key", columns)
        collect_null_type_columns(pa.field("value", data_type.item_type), f"{path}.value", columns)


def split_data_product(data_product: str) -> tuple[str, str]:
    if "." not in data_product:
        return "default", data_product.replace("-", "_")
    namespace, table = data_product.split(".", 1)
    return namespace.replace("-", "_"), table.replace("-", "_").replace(".", "_")


def failed_iceberg_checks(
    live_report: dict[str, Any],
    table_results: list[dict[str, Any]],
    catalog_db_path: Path,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if live_report.get("passed") is not True:
        failed.append({"check": "live_lakehouse_smoke_passed", "passed": live_report.get("passed")})
    if not catalog_db_path.is_file():
        failed.append({"check": "sqlite_catalog_db_created", "path": catalog_db_path.as_posix()})
    if not table_results:
        failed.append({"check": "iceberg_table_commits_present"})
    for item in table_results:
        if item.get("passed") is not True:
            failed.append(
                {
                    "check": "iceberg_table_commit",
                    "data_product": item.get("data_product"),
                    "snapshot_id": item.get("snapshot_id"),
                    "readback_passed": item.get("readback_passed"),
                }
            )
    return failed


def snapshot_summary(snapshot: Any) -> dict[str, Any]:
    if snapshot is None:
        return {}
    summary = getattr(snapshot, "summary", None)
    if summary is None:
        return {}
    if hasattr(summary, "model_dump"):
        return dict(summary.model_dump())
    if isinstance(summary, dict):
        return dict(summary)
    try:
        return dict(summary)
    except Exception:
        return {"value": str(summary)}


def file_uri_to_path(uri: str | None) -> Path | None:
    if not uri:
        return None
    parsed = urlparse(uri)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme == "":
        return Path(uri)
    return None
