from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import csv
import io
import json

import dagster
from dagster import AssetMaterialization, DagsterInstance, RetryPolicy, job, op
import pyarrow as pa
import pyiceberg
from pyiceberg.catalog import load_catalog

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.dagster_orchestration_smoke import count_event_type, dagster_event_log, run_status_value
from enterprise_dp.event_backbone_smoke import CommandRunner, execute_step, stable_id
from enterprise_dp.live_bronze_ingestion_smoke import (
    DEFAULT_CATALOG_NAME,
    DEFAULT_CATALOG_URI,
    DEFAULT_ENDPOINT_URL,
    DEFAULT_GENERATED_AT,
    DEFAULT_REGION,
    DEFAULT_SCHEMA,
    DEFAULT_TABLE,
    write_live_bronze_ingestion_smoke_report,
)
from enterprise_dp.object_store_smoke import DEFAULT_ACCESS_KEY, DEFAULT_MINIO_SERVICE, DEFAULT_SECRET_KEY, ensure_bucket, s3_client
from enterprise_dp.pipelines.finance import (
    PIPELINE_FROM_BRONZE_NAME,
    build_gold_rows,
    build_manifest,
    build_silver_rows,
    validate_gold_rows,
    validate_silver_rows,
    write_jsonl,
)
from enterprise_dp.promotion import write_release_activation_manifest, write_release_promotion_manifest
from enterprise_dp.publication_ops import build_silver_gold_publication_ops_report, write_silver_gold_publication_ops_report
from enterprise_dp.trino_iceberg_minio_smoke import (
    DEFAULT_BUCKET,
    DEFAULT_CATALOG,
    DEFAULT_POSTGRES_SERVICE,
    DEFAULT_SERVICE,
    initialize_jdbc_catalog,
    metadata_count_probe,
)
from enterprise_dp.trino_sql_smoke import execute_trino_sql, sql_identifier, wait_for_trino
from enterprise_dp.event_backbone_smoke import resolve_compose_path, run_command


DEFAULT_RELEASE_ID = "local-orchestrated-live-publication-smoke"
DEFAULT_USE_CASE_ID = "finance-benefit-reconciliation"
DEFAULT_RUNNER_ID = PIPELINE_FROM_BRONZE_NAME
DEFAULT_PUBLICATION_SCHEMA = "publication_runtime_smoke"
DEFAULT_SILVER_TABLE = "finance_benefit_transactions"
DEFAULT_GOLD_TABLE = "finance_benefit_reconciliation"
DEFAULT_BRONZE_REPORT = "build/live-bronze-ingestion-smoke/live-bronze-ingestion-smoke-report.json"

TrinoExecutor = Callable[[str, str], Any]


@dataclass(frozen=True)
class OrchestratedPublicationSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_orchestrated_publication_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    live_bronze_ingestion_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    trino_service: str = DEFAULT_SERVICE,
    iceberg_postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    minio_service: str = DEFAULT_MINIO_SERVICE,
    bucket: str = DEFAULT_BUCKET,
    endpoint_url: str = DEFAULT_ENDPOINT_URL,
    access_key: str = DEFAULT_ACCESS_KEY,
    secret_key: str = DEFAULT_SECRET_KEY,
    region_name: str = DEFAULT_REGION,
    catalog: str = DEFAULT_CATALOG,
    catalog_name: str = DEFAULT_CATALOG_NAME,
    catalog_uri: str = DEFAULT_CATALOG_URI,
    bronze_schema: str = DEFAULT_SCHEMA,
    bronze_table: str = DEFAULT_TABLE,
    publication_schema: str = DEFAULT_PUBLICATION_SCHEMA,
    silver_table: str = DEFAULT_SILVER_TABLE,
    gold_table: str = DEFAULT_GOLD_TABLE,
    release_id: str = DEFAULT_RELEASE_ID,
    use_case_id: str = DEFAULT_USE_CASE_ID,
    runner_id: str = DEFAULT_RUNNER_ID,
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
    pyiceberg_catalog_override: Any | None = None,
    trino_executor_override: TrinoExecutor | None = None,
    live_bronze_report_override: dict[str, Any] | None = None,
) -> OrchestratedPublicationSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or DEFAULT_GENERATED_AT
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    safe_catalog = sql_identifier(catalog)
    safe_bronze_schema = sql_identifier(bronze_schema)
    safe_bronze_table = sql_identifier(bronze_table)
    safe_publication_schema = sql_identifier(publication_schema)
    safe_silver_table = sql_identifier(silver_table)
    safe_gold_table = sql_identifier(gold_table)
    warehouse = f"s3://{bucket}/warehouse"
    live_bronze_path, live_bronze_report = load_or_create_live_bronze_report(
        platform_root,
        target_dir,
        live_bronze_ingestion_smoke_report_path=live_bronze_ingestion_smoke_report_path,
        live_bronze_report_override=live_bronze_report_override,
        environment=environment,
        generated_at=generated,
        command_timeout_seconds=command_timeout_seconds,
    )
    object_store_probe: dict[str, Any] = {"passed": False}

    try:
        if pyiceberg_catalog_override is None:
            client = s3_client(
                endpoint_url=endpoint_url,
                access_key=access_key,
                secret_key=secret_key,
                region_name=region_name,
            )
            bucket_created = ensure_bucket(client, bucket)
            object_store_probe = {"passed": True, "bucket": bucket, "bucket_created": bucket_created}
            if start_runtime:
                execute_step(
                    command_log,
                    runner,
                    [
                        "docker",
                        "compose",
                        "-f",
                        compose_path.as_posix(),
                        "up",
                        "-d",
                        minio_service,
                        iceberg_postgres_service,
                        trino_service,
                    ],
                    cwd=platform_root,
                    timeout_seconds=command_timeout_seconds,
                    step="compose_up_orchestrated_publication_runtime",
                )
            initialize_jdbc_catalog(
                command_log,
                runner,
                compose_path=compose_path,
                postgres_service=iceberg_postgres_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
            )
            wait_for_trino(
                command_log,
                runner,
                compose_path=compose_path,
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                attempts=wait_attempts,
                interval_seconds=wait_interval_seconds,
            )
            catalog_client = load_catalog(
                catalog_name,
                **{
                    "type": "sql",
                    "uri": catalog_uri,
                    "warehouse": warehouse,
                    "s3.endpoint": endpoint_url,
                    "s3.access-key-id": access_key,
                    "s3.secret-access-key": secret_key,
                    "s3.region": region_name,
                },
            )
        else:
            object_store_probe = {"passed": True, "mode": "test_catalog_override"}
            catalog_client = pyiceberg_catalog_override

        def trino_executor(sql: str, step: str) -> Any:
            if trino_executor_override is not None:
                return trino_executor_override(sql, step)
            return execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step=step,
                sql=sql,
            )

        instance_dir = target_dir / "dagster-instance"
        instance_dir.mkdir(parents=True, exist_ok=True)
        (instance_dir / "dagster.yaml").write_text("telemetry:\n  enabled: false\n", encoding="utf-8")
        publication_job = build_publication_job(
            root=platform_root,
            output_dir=target_dir,
            generated_at=generated,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            runner_id=runner_id,
            catalog_client=catalog_client,
            trino_executor=trino_executor,
            catalog=safe_catalog,
            bronze_identifier=(safe_bronze_schema, safe_bronze_table),
            silver_identifier=(safe_publication_schema, safe_silver_table),
            gold_identifier=(safe_publication_schema, safe_gold_table),
            warehouse=warehouse,
            live_bronze_report=live_bronze_report,
        )
        with DagsterInstance.local_temp(tempdir=instance_dir.as_posix()) as instance:
            result = publication_job.execute_in_process(instance=instance, raise_on_error=False)
            run_id = result.run_id
            dagster_run = instance.get_run_by_id(run_id)
            event_log = dagster_event_log(list(instance.all_logs(run_id)))
            orchestration_summary = result.output_for_node("summarize_live_publication") if result.success else {}
    except Exception as exc:
        run_id = None
        dagster_run = None
        event_log = []
        orchestration_summary = {}
        failed_checks.append({"check": "orchestrated_live_publication_runtime", "message": f"{type(exc).__name__}: {exc}"})

    failed_checks.extend(
        failed_publication_checks(
            object_store_probe=object_store_probe,
            orchestration_summary=orchestration_summary,
            event_log=event_log,
        )
    )
    report = build_orchestrated_publication_report(
        root=platform_root,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=runner_id,
        compose_path=compose_path,
        trino_service=trino_service,
        iceberg_postgres_service=iceberg_postgres_service,
        minio_service=minio_service,
        bucket=bucket,
        endpoint_url=endpoint_url,
        catalog_uri=catalog_uri,
        warehouse=warehouse,
        live_bronze_path=live_bronze_path,
        live_bronze_report=live_bronze_report,
        object_store_probe=object_store_probe,
        run_id=run_id,
        run_status=run_status_value(dagster_run) if dagster_run is not None else None,
        event_log=event_log,
        orchestration_summary=orchestration_summary,
        command_log=command_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return OrchestratedPublicationSmokeResult(output_path=target, report=report)


def load_or_create_live_bronze_report(
    root: Path,
    output_dir: Path,
    *,
    live_bronze_ingestion_smoke_report_path: str | Path | None,
    live_bronze_report_override: dict[str, Any] | None,
    environment: str,
    generated_at: str,
    command_timeout_seconds: int,
) -> tuple[Path | None, dict[str, Any]]:
    if live_bronze_report_override is not None:
        return None, live_bronze_report_override
    path_value = live_bronze_ingestion_smoke_report_path or DEFAULT_BRONZE_REPORT
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    if path.is_file():
        return path, load_json(path)
    result = write_live_bronze_ingestion_smoke_report(
        root,
        output_dir / "live-bronze-ingestion-smoke-report.json",
        output_dir=output_dir / "live-bronze-run",
        environment=environment,
        generated_at=generated_at,
        command_timeout_seconds=command_timeout_seconds,
    )
    return result.output_path, result.report


def build_publication_job(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    runner_id: str,
    catalog_client: Any,
    trino_executor: TrinoExecutor,
    catalog: str,
    bronze_identifier: tuple[str, str],
    silver_identifier: tuple[str, str],
    gold_identifier: tuple[str, str],
    warehouse: str,
    live_bronze_report: dict[str, Any],
):
    @op(retry_policy=RetryPolicy(max_retries=2, delay=0))
    def retry_probe(context) -> dict[str, Any]:
        if context.retry_number == 0:
            raise RuntimeError("deterministic retry probe for orchestrated publication smoke")
        return {"passed": True, "retry_number": context.retry_number, "max_retries": 2, "backoff_seconds": 0}

    @op
    def materialize_live_silver_gold(context) -> dict[str, Any]:
        probe = materialize_publication(
            root=root,
            output_dir=output_dir,
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            runner_id=runner_id,
            catalog_client=catalog_client,
            trino_executor=trino_executor,
            catalog=catalog,
            bronze_identifier=bronze_identifier,
            silver_identifier=silver_identifier,
            gold_identifier=gold_identifier,
            warehouse=warehouse,
            live_bronze_report=live_bronze_report,
        )
        for layer_name, layer in probe.get("layers", {}).items():
            if isinstance(layer, dict):
                context.log_event(
                    AssetMaterialization(
                        asset_key=layer_name,
                        metadata={
                            "iceberg_table": layer.get("iceberg_table"),
                            "snapshot_id": str(layer.get("snapshot_id")),
                            "row_count": layer.get("row_count", 0),
                            "content_hash": layer.get("content_hash"),
                        },
                    )
                )
        return probe

    @op
    def summarize_live_publication(retry: dict[str, Any], publication: dict[str, Any]) -> dict[str, Any]:
        failed_checks = []
        if retry.get("passed") is not True:
            failed_checks.append({"check": "retry_probe_passed", "probe": retry})
        if publication.get("passed") is not True:
            failed_checks.append({"check": "publication_probe_passed", "probe": publication})
        return {
            "passed": not failed_checks,
            "retry_probe": retry,
            "publication": publication,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        }

    @job(name="finance_benefit_live_silver_gold_publication")
    def publication_job():
        summarize_live_publication(retry_probe(), materialize_live_silver_gold())

    return publication_job


def materialize_publication(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    runner_id: str,
    catalog_client: Any,
    trino_executor: TrinoExecutor,
    catalog: str,
    bronze_identifier: tuple[str, str],
    silver_identifier: tuple[str, str],
    gold_identifier: tuple[str, str],
    warehouse: str,
    live_bronze_report: dict[str, Any],
) -> dict[str, Any]:
    paths = publication_paths(output_dir)
    bronze_table = catalog_client.load_table(bronze_identifier)
    bronze_rows_raw = bronze_table.scan().to_arrow().to_pylist()
    bronze_rows = [normalize_bronze_row(row) for row in bronze_rows_raw]
    silver_rows = build_silver_rows(bronze_rows)
    gold_rows = build_gold_rows(silver_rows, snapshot_id=release_id, built_at=generated_at)
    silver_errors = validate_silver_rows(silver_rows)
    gold_errors = validate_gold_rows(gold_rows)
    paths["approved_bronze"].parent.mkdir(parents=True, exist_ok=True)
    bronze_hash = write_jsonl(paths["approved_bronze"], bronze_rows)
    silver_hash = write_jsonl(paths["silver_jsonl"], silver_rows)
    gold_hash = write_jsonl(paths["gold_jsonl"], gold_rows)
    ingestion_manifest = write_live_ingestion_manifest(
        paths["ingestion_manifest"],
        approved_path=paths["approved_bronze"],
        root_dir=paths["ingestion_root"],
        generated_at=generated_at,
        ingested_at=live_bronze_report.get("summary", {}).get("ingested_at") or "2026-01-15T09:15:05Z",
        bronze_hash=bronze_hash,
        row_count=len(bronze_rows),
    )
    create_silver_gold_tables(
        trino_executor,
        catalog=catalog,
        schema=silver_identifier[0],
        warehouse=warehouse,
        silver_table=silver_identifier[1],
        gold_table=gold_identifier[1],
    )
    silver_table_obj = catalog_client.load_table(silver_identifier)
    gold_table_obj = catalog_client.load_table(gold_identifier)
    silver_before = len(silver_table_obj.snapshots())
    gold_before = len(gold_table_obj.snapshots())
    if silver_rows:
        silver_table_obj.append(arrow_table(silver_rows, SILVER_FIELDS))
    if gold_rows:
        gold_table_obj.append(arrow_table(gold_rows, GOLD_FIELDS))
    silver_loaded = catalog_client.load_table(silver_identifier)
    gold_loaded = catalog_client.load_table(gold_identifier)
    silver_after = len(silver_loaded.snapshots())
    gold_after = len(gold_loaded.snapshots())
    silver_snapshot_id = latest_snapshot_id(silver_loaded)
    gold_snapshot_id = latest_snapshot_id(gold_loaded)
    silver_metadata = getattr(silver_loaded, "metadata_location", None)
    gold_metadata = getattr(gold_loaded, "metadata_location", None)
    silver_count = len(silver_loaded.scan().to_arrow().to_pylist())
    gold_count = len(gold_loaded.scan().to_arrow().to_pylist())
    qualified_silver = f"{catalog}.{silver_identifier[0]}.{silver_identifier[1]}"
    qualified_gold = f"{catalog}.{gold_identifier[0]}.{gold_identifier[1]}"
    trino_silver_count = parse_single_int(command_stdout(trino_executor(f"SELECT COUNT(*) FROM {qualified_silver}", "query_live_silver_row_count")))
    trino_gold_count = parse_single_int(command_stdout(trino_executor(f"SELECT COUNT(*) FROM {qualified_gold}", "query_live_gold_row_count")))
    gold_snapshots_probe = metadata_count_probe(
        command_stdout(trino_executor(f'SELECT COUNT(*) FROM {catalog}.{gold_identifier[0]}."{gold_identifier[1]}$snapshots"', "query_live_gold_snapshots")),
        probe_name="live_gold_snapshots",
    )
    gold_files_probe = metadata_count_probe(
        command_stdout(trino_executor(f'SELECT COUNT(*) FROM {catalog}.{gold_identifier[0]}."{gold_identifier[1]}$files"', "query_live_gold_files")),
        probe_name="live_gold_files",
    )
    layer_snapshots = (
        SimpleLayerSnapshot(
            "bronze.events_benefit_settled",
            paths["approved_bronze"],
            len(bronze_rows),
            bronze_hash,
            True,
            (),
        ),
        SimpleLayerSnapshot(
            "silver.finance_benefit_transactions",
            paths["silver_jsonl"],
            len(silver_rows),
            silver_hash,
            not silver_errors,
            silver_errors,
        ),
        SimpleLayerSnapshot(
            "gold.finance_benefit_reconciliation",
            paths["gold_jsonl"],
            len(gold_rows),
            gold_hash,
            not gold_errors,
            gold_errors,
        ),
    )
    manifest = build_manifest(
        snapshot_id=release_id,
        generated_at=generated_at,
        input_path=paths["approved_bronze"],
        output_dir=paths["pipeline_root"],
        layer_snapshots=layer_snapshots,  # type: ignore[arg-type]
        upstream_manifest_path=paths["ingestion_manifest"],
        upstream_manifest=ingestion_manifest,
    )
    paths["pipeline_manifest"].parent.mkdir(parents=True, exist_ok=True)
    paths["pipeline_manifest"].write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    snapshot_evidence = write_snapshot_evidence(
        paths["snapshot_evidence"],
        generated_at=generated_at,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=runner_id,
        pipeline_manifest_path=paths["pipeline_manifest"],
        pipeline_manifest=manifest,
        silver_snapshot_id=silver_snapshot_id,
        gold_snapshot_id=gold_snapshot_id,
        silver_metadata=silver_metadata,
        gold_metadata=gold_metadata,
        silver_content_hash=silver_hash,
        gold_content_hash=gold_hash,
        offset_ledger=live_bronze_report.get("bronze_probe", {}).get("offset_ledger"),
    )
    catalog_bundle_path = paths["catalog_bundle"]
    catalog_bundle_path.parent.mkdir(parents=True, exist_ok=True)
    from enterprise_dp.catalog import build_catalog_bundle

    catalog_bundle = build_catalog_bundle(root, manifest_paths=[paths["pipeline_manifest"]], generated_at=generated_at)
    catalog_bundle_path.write_text(f"{canonical_json(catalog_bundle)}\n", encoding="utf-8")
    release_evidence = write_release_evidence(
        paths["release_evidence"],
        generated_at=generated_at,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=runner_id,
        pipeline_manifest_path=paths["pipeline_manifest"],
        catalog_bundle_path=catalog_bundle_path,
        snapshot_evidence_path=paths["snapshot_evidence"],
        primary_output="gold.finance_benefit_reconciliation",
        gates_passed=not silver_errors and not gold_errors,
        layer_hashes={"silver": silver_hash, "gold": gold_hash},
    )
    previous_pointer_path = paths["active_pointer"]
    previous_pointer_path.parent.mkdir(parents=True, exist_ok=True)
    previous_pointer_path.write_text(
        f"{canonical_json(previous_active_pointer(environment=environment, data_product='gold.finance_benefit_reconciliation'))}\n",
        encoding="utf-8",
    )
    promotion = write_release_promotion_manifest(
        paths["release_evidence"],
        paths["promotion"],
        target_environment=environment,
        requested_by="data-platform-release-manager",
        approver="data-platform-approver",
        generated_at=generated_at,
    )
    activation = write_release_activation_manifest(
        promotion.output_path,
        paths["activation"],
        active_state_path=paths["active_pointer"],
        activated_by="data-platform-operator",
        generated_at=generated_at,
    )
    publication_ops = write_silver_gold_publication_ops_report(
        root,
        paths["publication_ops"],
        environment=environment,
        release_evidence_paths=[paths["release_evidence"]],
        promotion_manifest_paths=[paths["promotion"]],
        activation_manifest_paths=[paths["activation"]],
        active_pointer_paths=[paths["active_pointer"]],
        generated_at=generated_at,
    )
    drift_probe = write_pointer_drift_probe(
        root,
        paths["drift_pointer"],
        environment=environment,
        generated_at=generated_at,
        release_evidence_path=paths["release_evidence"],
        promotion_path=paths["promotion"],
        activation_path=paths["activation"],
        active_pointer_path=paths["active_pointer"],
    )
    passed = (
        len(bronze_rows) > 0
        and silver_count == len(silver_rows)
        and gold_count == len(gold_rows)
        and trino_silver_count == len(silver_rows)
        and trino_gold_count == len(gold_rows)
        and silver_after > silver_before
        and gold_after > gold_before
        and promotion.manifest.get("passed") is True
        and activation.manifest.get("passed") is True
        and publication_ops.report.get("passed") is True
        and drift_probe.get("passed") is True
        and gold_snapshots_probe.get("passed") is True
        and gold_files_probe.get("passed") is True
    )
    return {
        "passed": passed,
        "bronze_row_count": len(bronze_rows),
        "silver_row_count": len(silver_rows),
        "gold_row_count": len(gold_rows),
        "trino_silver_row_count": trino_silver_count,
        "trino_gold_row_count": trino_gold_count,
        "silver_snapshot_count_before": silver_before,
        "silver_snapshot_count_after": silver_after,
        "gold_snapshot_count_before": gold_before,
        "gold_snapshot_count_after": gold_after,
        "silver_snapshot_id": silver_snapshot_id,
        "gold_snapshot_id": gold_snapshot_id,
        "gold_snapshots_probe": gold_snapshots_probe,
        "gold_files_probe": gold_files_probe,
        "layers": {
            "bronze.events_benefit_settled": {"row_count": len(bronze_rows), "content_hash": bronze_hash},
            "silver.finance_benefit_transactions": {
                "iceberg_table": qualified_silver,
                "row_count": len(silver_rows),
                "content_hash": silver_hash,
                "snapshot_id": silver_snapshot_id,
                "metadata_location": silver_metadata,
            },
            "gold.finance_benefit_reconciliation": {
                "iceberg_table": qualified_gold,
                "row_count": len(gold_rows),
                "content_hash": gold_hash,
                "snapshot_id": gold_snapshot_id,
                "metadata_location": gold_metadata,
            },
        },
        "release": artifact_ref(paths["release_evidence"], release_evidence),
        "promotion": artifact_ref(paths["promotion"], promotion.manifest),
        "activation": artifact_ref(paths["activation"], activation.manifest),
        "active_pointer": artifact_ref(paths["active_pointer"], load_json(paths["active_pointer"])),
        "publication_ops": artifact_ref(paths["publication_ops"], publication_ops.report),
        "snapshot_evidence": artifact_ref(paths["snapshot_evidence"], snapshot_evidence),
        "pipeline_manifest": {"uri": paths["pipeline_manifest"].as_posix(), "hash": hash_file(paths["pipeline_manifest"])},
        "catalog_bundle": {"uri": catalog_bundle_path.as_posix(), "hash": hash_file(catalog_bundle_path)},
        "drift_probe": drift_probe,
        "quality_errors": {"silver": list(silver_errors), "gold": list(gold_errors)},
    }


@dataclass(frozen=True)
class SimpleLayerSnapshot:
    name: str
    path: Path
    row_count: int
    content_hash: str
    quality_passed: bool
    quality_errors: tuple[str, ...]

    def as_manifest_entry(self, output_dir: Path) -> dict[str, Any]:
        try:
            relative_path = self.path.relative_to(output_dir).as_posix()
        except ValueError:
            relative_path = self.path.as_posix()
        return {
            "path": relative_path,
            "row_count": self.row_count,
            "content_hash": self.content_hash,
            "quality_passed": self.quality_passed,
            "quality_errors": list(self.quality_errors),
        }


def normalize_bronze_row(row: dict[str, Any]) -> dict[str, Any]:
    event = json.loads(str(row.get("payload_json") or "{}"))
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    return {
        "event_id": event.get("eventId") or row.get("event_id"),
        "event_type": payload.get("eventType") or "BENEFIT_SETTLED",
        "product_id": event.get("productId") or payload.get("sourceProductId"),
        "source_product_id": payload.get("sourceProductId"),
        "org_id": event.get("orgId") or payload.get("orgId"),
        "order_id": payload.get("orderId"),
        "payment_id": payload.get("paymentId"),
        "entitlement_id": payload.get("entitlementId"),
        "beneficiary_id_hash": payload.get("beneficiaryIdHash"),
        "item_id": payload.get("itemId"),
        "currency": payload.get("currency"),
        "benefit_transaction_id": payload.get("benefitTransactionId"),
        "reconciliation_key": payload.get("reconciliationKey"),
        "benefit_type": payload.get("benefitType"),
        "expected_amount_cents": payload.get("expectedAmountCents"),
        "actual_amount_cents": payload.get("actualAmountCents"),
        "expected_points": payload.get("expectedPoints"),
        "actual_points": payload.get("actualPoints"),
        "list_price_cents": payload.get("listPriceCents"),
        "final_amount_cents": payload.get("finalAmountCents"),
        "paid_amount_cents": payload.get("paidAmountCents"),
        "committed_discount_cents": payload.get("committedDiscountCents"),
        "loyalty_points_earned": payload.get("loyaltyPointsEarned"),
        "loyalty_points_burned": payload.get("loyaltyPointsBurned"),
        "reward_amount_cents": payload.get("rewardAmountCents"),
        "refund_amount_cents": payload.get("refundAmountCents"),
        "settlement_status": payload.get("settlementStatus"),
        "benefit_status": payload.get("benefitStatus"),
        "settled_at": payload.get("settledAt"),
        "accounting_date": payload.get("accountingDate"),
        "reason_code": payload.get("reasonCode"),
        "source_record_hash_sha256": row.get("payload_hash"),
        "published_at": event.get("publishedAt"),
        "ingested_at": row.get("ingested_at"),
    }


def create_silver_gold_tables(
    trino_executor: TrinoExecutor,
    *,
    catalog: str,
    schema: str,
    warehouse: str,
    silver_table: str,
    gold_table: str,
) -> None:
    schema_location = f"{warehouse}/{schema}"
    statements = [
        f"DROP TABLE IF EXISTS {catalog}.{schema}.{silver_table}",
        f"DROP TABLE IF EXISTS {catalog}.{schema}.{gold_table}",
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema} WITH (location='{schema_location}')",
        create_table_sql(f"{catalog}.{schema}.{silver_table}", SILVER_FIELDS),
        create_table_sql(f"{catalog}.{schema}.{gold_table}", GOLD_FIELDS),
    ]
    trino_executor("; ".join(statements), "create_live_silver_gold_iceberg_tables")


def create_table_sql(qualified_table: str, fields: tuple[tuple[str, str], ...]) -> str:
    columns = ", ".join(f"{name} {sql_type}" for name, sql_type in fields)
    return f"CREATE TABLE {qualified_table} ({columns}) WITH (format='PARQUET')"


SILVER_FIELDS: tuple[tuple[str, str], ...] = (
    ("transaction_id", "varchar"),
    ("product_id", "varchar"),
    ("source_product_id", "varchar"),
    ("org_id", "varchar"),
    ("order_id", "varchar"),
    ("payment_id", "varchar"),
    ("entitlement_id", "varchar"),
    ("beneficiary_id_hash", "varchar"),
    ("item_id", "varchar"),
    ("currency", "varchar"),
    ("benefit_transaction_id", "varchar"),
    ("reconciliation_key", "varchar"),
    ("benefit_type", "varchar"),
    ("expected_amount_cents", "bigint"),
    ("actual_amount_cents", "bigint"),
    ("expected_points", "bigint"),
    ("actual_points", "bigint"),
    ("list_price_cents", "bigint"),
    ("final_amount_cents", "bigint"),
    ("paid_amount_cents", "bigint"),
    ("committed_discount_cents", "bigint"),
    ("loyalty_points_earned", "bigint"),
    ("loyalty_points_burned", "bigint"),
    ("reward_amount_cents", "bigint"),
    ("refund_amount_cents", "bigint"),
    ("settlement_status", "varchar"),
    ("benefit_status", "varchar"),
    ("settled_at", "varchar"),
    ("accounting_date", "varchar"),
    ("reason_code", "varchar"),
    ("source_event_id", "varchar"),
    ("source_record_hash_sha256", "varchar"),
)

GOLD_FIELDS: tuple[tuple[str, str], ...] = (
    ("product_id", "varchar"),
    ("source_product_id", "varchar"),
    ("dataset_snapshot_id", "varchar"),
    ("reconciliation_id", "varchar"),
    ("org_id", "varchar"),
    ("order_id", "varchar"),
    ("payment_id", "varchar"),
    ("benefit_transaction_id", "varchar"),
    ("reconciliation_key", "varchar"),
    ("benefit_type", "varchar"),
    ("entitlement_id", "varchar"),
    ("beneficiary_id_hash", "varchar"),
    ("item_id", "varchar"),
    ("currency", "varchar"),
    ("expected_amount_cents", "bigint"),
    ("actual_amount_cents", "bigint"),
    ("variance_amount_cents", "bigint"),
    ("expected_points", "bigint"),
    ("actual_points", "bigint"),
    ("variance_points", "bigint"),
    ("list_price_cents", "bigint"),
    ("final_amount_cents", "bigint"),
    ("paid_amount_cents", "bigint"),
    ("committed_discount_cents", "bigint"),
    ("loyalty_points_earned", "bigint"),
    ("loyalty_points_burned", "bigint"),
    ("reward_amount_cents", "bigint"),
    ("refund_amount_cents", "bigint"),
    ("expected_net_revenue_cents", "bigint"),
    ("actual_net_revenue_cents", "bigint"),
    ("reconciliation_delta_cents", "bigint"),
    ("settlement_status", "varchar"),
    ("benefit_status", "varchar"),
    ("reconciliation_status", "varchar"),
    ("reason_code", "varchar"),
    ("accounting_date", "varchar"),
    ("source_event_id", "varchar"),
    ("source_record_hash_sha256", "varchar"),
    ("occurred_at", "varchar"),
    ("settled_at", "varchar"),
    ("built_at", "varchar"),
    ("quality_passed", "boolean"),
)


def arrow_table(rows: list[dict[str, Any]], fields: tuple[tuple[str, str], ...]) -> pa.Table:
    arrays: dict[str, list[Any]] = {}
    schema_fields = []
    for name, sql_type in fields:
        if sql_type == "bigint":
            arrays[name] = [int(row.get(name) or 0) for row in rows]
            schema_fields.append(pa.field(name, pa.int64(), nullable=True))
        elif sql_type == "boolean":
            arrays[name] = [bool(row.get(name)) for row in rows]
            schema_fields.append(pa.field(name, pa.bool_(), nullable=True))
        else:
            arrays[name] = [None if row.get(name) is None else str(row.get(name)) for row in rows]
            schema_fields.append(pa.field(name, pa.string(), nullable=True))
    return pa.table(arrays, schema=pa.schema(schema_fields))


def publication_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "ingestion_root": output_dir / "derived-bronze",
        "approved_bronze": output_dir / "derived-bronze" / "bronze" / "events_benefit_settled.jsonl",
        "ingestion_manifest": output_dir / "derived-bronze" / "manifests" / "bronze.events_benefit_settled.live-publication.json",
        "pipeline_root": output_dir / "pipeline",
        "silver_jsonl": output_dir / "pipeline" / "silver" / "finance_benefit_transactions.jsonl",
        "gold_jsonl": output_dir / "pipeline" / "gold" / "finance_benefit_reconciliation.jsonl",
        "pipeline_manifest": output_dir / "pipeline" / "manifests" / "finance_benefit_reconciliation.live-publication.json",
        "snapshot_evidence": output_dir / "publication" / "lakehouse-snapshot-evidence.json",
        "catalog_bundle": output_dir / "publication" / "catalog-bundle.json",
        "release_evidence": output_dir / "publication" / "release-evidence.json",
        "promotion": output_dir / "publication" / "promotion.json",
        "activation": output_dir / "publication" / "activation.json",
        "active_pointer": output_dir / "publication" / "active" / "gold.finance_benefit_reconciliation.json",
        "publication_ops": output_dir / "publication" / "silver-gold-publication-ops.json",
        "drift_pointer": output_dir / "publication" / "drift-pointer.json",
    }


def write_live_ingestion_manifest(
    path: Path,
    *,
    approved_path: Path,
    root_dir: Path,
    generated_at: str,
    ingested_at: str,
    bronze_hash: str,
    row_count: int,
) -> dict[str, Any]:
    manifest = {
        "pipeline": "bronze_ingestion.live_iceberg_projection.v1",
        "topic": "finance.benefit_settled.v1",
        "bronze_target": "bronze.events_benefit_settled",
        "ingest_run_id": "live-publication-derived-bronze",
        "generated_at": generated_at,
        "ingested_at": ingested_at,
        "quality_passed": True,
        "approved": {
            "path": approved_path.relative_to(root_dir).as_posix(),
            "row_count": row_count,
            "new_row_count": row_count,
            "content_hash": bronze_hash,
        },
        "quarantine": {"row_count": 0},
        "source_positions": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return manifest


def write_snapshot_evidence(
    path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    runner_id: str,
    pipeline_manifest_path: Path,
    pipeline_manifest: dict[str, Any],
    silver_snapshot_id: Any,
    gold_snapshot_id: Any,
    silver_metadata: str | None,
    gold_metadata: str | None,
    silver_content_hash: str,
    gold_content_hash: str,
    offset_ledger: Any,
) -> dict[str, Any]:
    layers = {
        "silver.finance_benefit_transactions": {
            "manifest_layer": pipeline_manifest["layers"]["silver.finance_benefit_transactions"],
            "snapshot": {
                "snapshot_id": str(silver_snapshot_id),
                "metadata_location": silver_metadata,
                "content_hash": silver_content_hash,
            },
        },
        "gold.finance_benefit_reconciliation": {
            "manifest_layer": pipeline_manifest["layers"]["gold.finance_benefit_reconciliation"],
            "snapshot": {
                "snapshot_id": str(gold_snapshot_id),
                "metadata_location": gold_metadata,
                "content_hash": gold_content_hash,
            },
        },
    }
    evidence = {
        "artifact_type": "lakehouse_snapshot_evidence.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "runner_id": runner_id,
        "primary_output": "gold.finance_benefit_reconciliation",
        "dataset_snapshot_id": pipeline_manifest.get("snapshot_id"),
        "pipeline": {
            "manifest_path": pipeline_manifest_path.as_posix(),
            "manifest_hash": hash_file(pipeline_manifest_path),
            "snapshot_id": pipeline_manifest.get("snapshot_id"),
        },
        "layers": layers,
        "primary_snapshot": layers["gold.finance_benefit_reconciliation"]["snapshot"],
        "source_offset_ledger": offset_ledger if isinstance(offset_ledger, dict) else None,
        "failures": [],
        "passed": True,
    }
    evidence["evidence_id"] = stable_id("snapshot-evidence", evidence)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    return evidence


def write_release_evidence(
    path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    runner_id: str,
    pipeline_manifest_path: Path,
    catalog_bundle_path: Path,
    snapshot_evidence_path: Path,
    primary_output: str,
    gates_passed: bool,
    layer_hashes: dict[str, str],
) -> dict[str, Any]:
    gates = [
        {"gate_id": gate_id, "passed": gates_passed, "details": {"mode": "orchestrated_live_publication_smoke"}}
        for gate_id in (
            "P0-CONTRACT-COMPATIBILITY",
            "P0-SCHEMA-REGISTRY-COMPATIBILITY",
            "P0-ACCESS-POLICY",
            "P0-ACCESS-GRANT-EVIDENCE",
            "P0-RETENTION-ERASURE",
            "P0-PRODUCTION-EVIDENCE",
            "P0-INGESTION-LAG",
            "P0-FRESHNESS",
            "P0-PIPELINE-QUALITY",
            "P0-QUALITY-PROFILE",
            "P0-OUTPUT-EVIDENCE",
            "P0-LAKEHOUSE-SNAPSHOT-EVIDENCE",
            "P0-CATALOG-LINEAGE",
        )
    ]
    manifest = load_json(pipeline_manifest_path)
    evidence = {
        "release_id": release_id,
        "environment": environment,
        "generated_at": generated_at,
        "use_case_id": use_case_id,
        "runner_id": runner_id,
        "runner_input_kind": "data_product_snapshot",
        "primary_output": primary_output,
        "output_data_products": ["silver.finance_benefit_transactions", "gold.finance_benefit_reconciliation"],
        "pipeline_run_id": manifest.get("snapshot_id"),
        "snapshot_evidence_uri": snapshot_evidence_path.as_posix(),
        "snapshot_evidence_hash": hash_file(snapshot_evidence_path),
        "artifacts": {
            "pipeline_manifest_path": pipeline_manifest_path.as_posix(),
            "pipeline_manifest_hash": hash_file(pipeline_manifest_path),
            "catalog_bundle_path": catalog_bundle_path.as_posix(),
            "catalog_bundle_hash": hash_file(catalog_bundle_path),
            "snapshot_evidence_uri": snapshot_evidence_path.as_posix(),
            "snapshot_evidence_hash": hash_file(snapshot_evidence_path),
        },
        "quality_report": {"passed": gates_passed, "layer_hashes": layer_hashes},
        "gates": gates,
        "release_passed": gates_passed,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    return evidence


def previous_active_pointer(*, environment: str, data_product: str) -> dict[str, Any]:
    return {
        "artifact_type": "release_active_pointer.v1",
        "pointer_version": 1,
        "activation_id": "previous-local-activation",
        "environment": environment,
        "release_id": "previous-local-release",
        "data_product": data_product,
        "dataset_snapshot_id": "previous-local-snapshot",
        "content_hash": "sha256:" + stable_id("previous", data_product),
        "row_count": 1,
        "activated_at": "2026-01-14T00:00:00Z",
        "activated_by": "data-platform-operator",
        "promotion_manifest_uri": "evidence://previous/promotion.json",
        "promotion_manifest_hash": "sha256:" + stable_id("previous-promotion", data_product),
        "rollback_target": None,
    }


def write_pointer_drift_probe(
    root: Path,
    drift_pointer_path: Path,
    *,
    environment: str,
    generated_at: str,
    release_evidence_path: Path,
    promotion_path: Path,
    activation_path: Path,
    active_pointer_path: Path,
) -> dict[str, Any]:
    pointer = load_json(active_pointer_path)
    pointer["dataset_snapshot_id"] = "drifted-snapshot"
    drift_pointer_path.parent.mkdir(parents=True, exist_ok=True)
    drift_pointer_path.write_text(f"{canonical_json(pointer)}\n", encoding="utf-8")
    report = build_silver_gold_publication_ops_report(
        root,
        environment=environment,
        release_evidence_paths=[release_evidence_path],
        promotion_manifest_paths=[promotion_path],
        activation_manifest_paths=[activation_path],
        active_pointer_paths=[drift_pointer_path],
        generated_at=generated_at,
    )
    failed_products = report.get("decision_board", {}).get("failed_products", [])
    issues = failed_products[0].get("issues", []) if failed_products else []
    return {
        "passed": report.get("passed") is False and "active_pointer_drift" in issues,
        "drift_pointer_path": drift_pointer_path.as_posix(),
        "drift_pointer_hash": hash_file(drift_pointer_path),
        "publication_ops_passed": report.get("passed"),
        "issues": issues,
    }


def failed_publication_checks(
    *,
    object_store_probe: dict[str, Any],
    orchestration_summary: dict[str, Any],
    event_log: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    publication = orchestration_summary.get("publication") if isinstance(orchestration_summary.get("publication"), dict) else {}
    if object_store_probe.get("passed") is not True:
        failed.append({"check": "object_store_bucket_ready", "probe": object_store_probe})
    if orchestration_summary.get("passed") is not True:
        failed.append({"check": "dagster_publication_job_passed", "probe": orchestration_summary})
    if publication.get("publication_ops", {}).get("passed") is not True:
        failed.append({"check": "silver_gold_publication_ops_passed", "probe": publication.get("publication_ops")})
    if publication.get("promotion", {}).get("passed") is not True:
        failed.append({"check": "promotion_manifest_passed", "probe": publication.get("promotion")})
    if publication.get("activation", {}).get("passed") is not True:
        failed.append({"check": "activation_manifest_passed", "probe": publication.get("activation")})
    if publication.get("drift_probe", {}).get("passed") is not True:
        failed.append({"check": "active_pointer_drift_negative_test", "probe": publication.get("drift_probe")})
    if count_event_type(event_log, "STEP_UP_FOR_RETRY") < 1:
        failed.append({"check": "dagster_retry_event_recorded", "retry_event_count": count_event_type(event_log, "STEP_UP_FOR_RETRY")})
    if count_event_type(event_log, "ASSET_MATERIALIZATION") < 2:
        failed.append(
            {
                "check": "silver_gold_asset_materializations_recorded",
                "asset_materialization_count": count_event_type(event_log, "ASSET_MATERIALIZATION"),
            }
        )
    return failed


def build_orchestrated_publication_report(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    runner_id: str,
    compose_path: Path,
    trino_service: str,
    iceberg_postgres_service: str,
    minio_service: str,
    bucket: str,
    endpoint_url: str,
    catalog_uri: str,
    warehouse: str,
    live_bronze_path: Path | None,
    live_bronze_report: dict[str, Any],
    object_store_probe: dict[str, Any],
    run_id: str | None,
    run_status: str | None,
    event_log: list[dict[str, Any]],
    orchestration_summary: dict[str, Any],
    command_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    publication = orchestration_summary.get("publication") if isinstance(orchestration_summary.get("publication"), dict) else {}
    summary = {
        "bronze_row_count": publication.get("bronze_row_count", 0),
        "silver_row_count": publication.get("silver_row_count", 0),
        "gold_row_count": publication.get("gold_row_count", 0),
        "trino_silver_row_count": publication.get("trino_silver_row_count", 0),
        "trino_gold_row_count": publication.get("trino_gold_row_count", 0),
        "silver_snapshot_count_after": publication.get("silver_snapshot_count_after", 0),
        "gold_snapshot_count_after": publication.get("gold_snapshot_count_after", 0),
        "promotion_passed": publication.get("promotion", {}).get("passed"),
        "activation_passed": publication.get("activation", {}).get("passed"),
        "publication_ops_passed": publication.get("publication_ops", {}).get("passed"),
        "active_pointer_drift_negative_test_passed": publication.get("drift_probe", {}).get("passed"),
        "dagster_retry_event_count": count_event_type(event_log, "STEP_UP_FOR_RETRY"),
        "asset_materialization_count": count_event_type(event_log, "ASSET_MATERIALIZATION"),
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "orchestrated_live_publication_report.v1",
        "report_version": 1,
        "capability_ids": ["silver-gold-publication"],
        "report_id": stable_id("orchestrated-live-publication", environment, release_id),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "runner_id": runner_id,
        "runtime_scope": {
            "mode": "local_dagster_in_process_bronze_iceberg_to_silver_gold_publication",
            "covered": [
                "bronze_iceberg_table_read",
                "silver_iceberg_table_written",
                "gold_iceberg_table_written",
                "trino_silver_gold_readback",
                "dagster_run_history_event_log_readback",
                "dagster_retry_event_recorded",
                "silver_gold_asset_materialization_events",
                "release_evidence_generated",
                "promotion_manifest_approved",
                "activation_manifest_activated",
                "active_pointer_with_rollback_target",
                "active_pointer_drift_negative_test",
            ],
            "not_covered": [
                "dagster_daemon_or_schedule_tick_history",
                "distributed_executor_or_kubernetes_run_launcher",
                "production_retry_backoff_runtime_policy",
                "production_backfill_materialization_history",
                "production_catalog_ha",
                "production_catalog_concurrency_locking",
                "production_secret_rotation",
            ],
        },
        "runtime": {
            "compose_file": compose_path.as_posix(),
            "trino_service": trino_service,
            "iceberg_postgres_service": iceberg_postgres_service,
            "minio_service": minio_service,
            "object_store": {"provider": "minio", "endpoint_url": endpoint_url, "bucket": bucket, "warehouse": warehouse},
            "catalog_uri": redact_catalog_uri(catalog_uri),
            "pyiceberg_version": pyiceberg.__version__,
            "dagster_version": dagster.__version__,
            "root": root.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
        "live_bronze_ingestion": {
            "path": live_bronze_path.as_posix() if live_bronze_path else None,
            "hash": hash_file(live_bronze_path) if live_bronze_path and live_bronze_path.is_file() else None,
            "passed": live_bronze_report.get("passed"),
        },
        "dagster": {
            "job_name": "finance_benefit_live_silver_gold_publication",
            "run_id": run_id,
            "run_status": run_status,
            "event_count": len(event_log),
            "op_success_count": count_event_type(event_log, "STEP_SUCCESS"),
        },
        "object_store_probe": object_store_probe,
        "publication": publication,
        "event_log": event_log,
        "commands": command_log,
        "summary": summary,
        "passed": not failed_checks,
    }


def artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "passed": payload.get("passed"),
        "readiness_state": payload.get("readiness_state"),
    }


def latest_snapshot_id(table: Any) -> str | None:
    snapshots = table.snapshots()
    if not snapshots:
        return None
    return str(getattr(snapshots[-1], "snapshot_id", "") or "")


def command_stdout(result: Any) -> str:
    return result.stdout if hasattr(result, "stdout") else str(result or "")


def parse_single_int(stdout: str) -> int:
    for row in csv.reader(io.StringIO(stdout)):
        for cell in row:
            stripped = cell.strip().strip('"')
            if stripped.isdigit():
                return int(stripped)
    return 0


def redact_catalog_uri(uri: str) -> str:
    if "@" not in uri or "://" not in uri:
        return uri
    scheme, rest = uri.split("://", 1)
    return f"{scheme}://***:***@{rest.split('@', 1)[1]}"
