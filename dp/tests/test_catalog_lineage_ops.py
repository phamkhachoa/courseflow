from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog import hash_file, write_catalog_bundle
from enterprise_dp.catalog_lineage_ops import (
    build_catalog_lineage_ops_report,
    write_catalog_lineage_ops_report,
)
from enterprise_dp.catalog_publish import write_catalog_publish_manifest
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze
from enterprise_dp.semantic_views import write_semantic_view_manifest


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
GENERATED_AT = "2026-06-16T16:00:00Z"


def test_catalog_lineage_ops_allows_local_preflight_without_runtime_evidence() -> None:
    report = build_catalog_lineage_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "catalog_lineage_ops_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["summary"]["catalog_publish_status"] == "NOT_ATTACHED"
    assert report["passed"] is True


def test_catalog_lineage_ops_blocks_prod_without_publish_and_lineage_evidence(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "bundle.json"
    write_catalog_bundle(ROOT, catalog_path, generated_at=GENERATED_AT)

    report = build_catalog_lineage_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle_path=catalog_path,
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}

    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert {
        "catalog_publish_manifest_attached_for_production_like",
        "openlineage_attached_for_production_like",
        "openlineage_events_non_empty_for_production_like",
        "publish_receipt_attached_for_production_like",
    } <= failed


def test_catalog_lineage_ops_blocks_prod_without_publish_receipt(tmp_path: Path) -> None:
    catalog_path, openlineage_path, semantic_views_path = build_publish_inputs(tmp_path)
    publish = write_catalog_publish_manifest(
        catalog_path,
        tmp_path / "publish" / "catalog-publish.json",
        target_system="datahub",
        environment="prod",
        endpoint="https://datahub.enterprise.example",
        openlineage_events_path=openlineage_path,
        semantic_views_manifest_path=semantic_views_path,
        requested_by="data-platform-release-manager",
        change_ticket="CHG-DP-1001",
        generated_at=GENERATED_AT,
    )

    report = build_catalog_lineage_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle_path=catalog_path,
        catalog_publish_manifest_path=publish.output_path,
        openlineage_events_path=openlineage_path,
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}

    assert "publish_receipt_attached_for_production_like" in failed
    assert report["summary"]["catalog_publish_manifest_attached"] is True
    assert report["summary"]["openlineage_event_count"] == 2
    assert report["summary"]["catalog_publish_status"] == "BLOCKED"
    assert report["passed"] is False


def test_catalog_lineage_ops_blocks_prod_receipt_openlineage_hash_mismatch(tmp_path: Path) -> None:
    catalog_path, openlineage_path, semantic_views_path = build_publish_inputs(tmp_path)
    publish = write_catalog_publish_manifest(
        catalog_path,
        tmp_path / "publish" / "catalog-publish.json",
        target_system="datahub",
        environment="prod",
        endpoint="https://datahub.enterprise.example",
        openlineage_events_path=openlineage_path,
        semantic_views_manifest_path=semantic_views_path,
        requested_by="data-platform-release-manager",
        change_ticket="CHG-DP-1001",
        generated_at=GENERATED_AT,
    )
    receipt_path = write_publish_receipt(
        tmp_path / "publish" / "receipt.json",
        environment="prod",
        catalog_path=catalog_path,
        publish_manifest_path=publish.output_path,
        openlineage_path=openlineage_path,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["openlineage_hash"] = "sha256:" + ("0" * 64)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    report = build_catalog_lineage_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle_path=catalog_path,
        catalog_publish_manifest_path=publish.output_path,
        openlineage_events_path=openlineage_path,
        publish_receipt_path=receipt_path,
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}

    assert "publish_receipt_openlineage_hash_matches" in failed
    assert report["passed"] is False


def test_catalog_lineage_ops_blocks_invalid_openlineage_jsonl(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "bundle.json"
    openlineage_path = tmp_path / "lineage" / "bad.jsonl"
    write_catalog_bundle(ROOT, catalog_path, generated_at=GENERATED_AT)
    openlineage_path.parent.mkdir(parents=True)
    openlineage_path.write_text("{bad-json}\n", encoding="utf-8")

    report = build_catalog_lineage_ops_report(
        ROOT,
        environment="local",
        catalog_bundle_path=catalog_path,
        openlineage_events_path=openlineage_path,
        generated_at=GENERATED_AT,
    )

    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert "openlineage_jsonl_parse_passed" in failed
    assert report["passed"] is False


def test_catalog_lineage_ops_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "ops" / "catalog-lineage.json"
    result = write_catalog_lineage_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "ops" / "cli-catalog-lineage.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "catalog-lineage-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--environment",
            "local",
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["readiness_state"] == "local_preflight_ready"
    assert cli_output.is_file()


def write_publish_receipt(
    path: Path,
    *,
    environment: str,
    catalog_path: Path,
    publish_manifest_path: Path,
    openlineage_path: Path,
) -> Path:
    payload = {
        "artifact_type": "catalog_publish_receipt.v1",
        "environment": environment,
        "target": {"system": "datahub", "endpoint": "https://datahub.enterprise.example"},
        "status": "succeeded",
        "published_at": GENERATED_AT,
        "catalog_bundle_hash": hash_file(catalog_path),
        "catalog_publish_manifest_hash": hash_file(publish_manifest_path),
        "openlineage_hash": hash_file(openlineage_path),
        "entity_count": 1,
        "lineage_edge_count": 1,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def build_publish_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    catalog_path = tmp_path / "catalog" / "bundle.json"
    openlineage_path = tmp_path / "lineage" / "openlineage.jsonl"
    semantic_views_path = tmp_path / "serving" / "semantic-views.json"
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at="2026-01-15T11:00:05Z",
        ingest_run_id="catalog-lineage-ops-ingest-run",
    )
    recommendation = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="catalog-lineage-ops-recsys-snapshot",
        built_at="2026-01-15T11:00:10Z",
    )
    write_catalog_bundle(
        ROOT,
        catalog_path,
        manifest_paths=[ingestion.manifest_path, recommendation.manifest_path],
        generated_at="2026-01-15T12:00:00Z",
    )
    write_openlineage_events(
        catalog_path,
        openlineage_path,
        namespace="enterprise-dp://prod",
        producer="https://enterprise-dp.prod.example/openlineage-export",
    )
    write_semantic_view_manifest(
        ROOT,
        semantic_views_path,
        engine="all",
        generated_at="2026-01-15T12:15:00Z",
    )
    return catalog_path, openlineage_path, semantic_views_path
