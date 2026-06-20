from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog import write_catalog_bundle
from enterprise_dp.catalog_publish import build_catalog_publish_manifest, write_catalog_publish_manifest
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze
from enterprise_dp.semantic_views import write_semantic_view_manifest


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"


def test_catalog_publish_manifest_is_ready_for_production_like_publish(tmp_path: Path) -> None:
    catalog_path, openlineage_path, semantic_views_path = build_publish_inputs(tmp_path)

    result = write_catalog_publish_manifest(
        catalog_path,
        tmp_path / "publish" / "catalog-publish.json",
        target_system="datahub",
        environment="prod",
        endpoint="https://datahub.enterprise.example",
        openlineage_events_path=openlineage_path,
        semantic_views_manifest_path=semantic_views_path,
        requested_by="data-platform-release-manager",
        change_ticket="CHG-DP-1001",
        generated_at="2026-01-15T12:30:00Z",
    )
    manifest = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert manifest == result.manifest
    assert manifest["artifact_type"] == "catalog_publish_manifest.v1"
    assert manifest["publish_state"] == "ready_for_publish"
    assert manifest["passed"] is True
    assert manifest["catalog_bundle"]["hash"].startswith("sha256:")
    assert manifest["openlineage"]["hash"].startswith("sha256:")
    assert manifest["semantic_views"]["view_count"] >= 9
    assert manifest["publish_payload"]["data_products"] >= 9
    assert manifest["publish_payload"]["lineage_edges"] > 0


def test_catalog_publish_manifest_blocks_prod_without_required_artifacts(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "bundle.json"
    write_catalog_bundle(ROOT, catalog_path, generated_at="2026-01-15T12:00:00Z")

    manifest = build_catalog_publish_manifest(
        catalog_path,
        target_system="openmetadata",
        environment="prod",
        endpoint=None,
        requested_by=None,
        change_ticket=None,
        generated_at="2026-01-15T12:30:00Z",
    )
    failures = {failure["check"] for failure in manifest["failures"]}

    assert manifest["passed"] is False
    assert manifest["publish_state"] == "blocked"
    assert "production_endpoint_declared" in failures
    assert "requested_by_declared" in failures
    assert "change_ticket_declared" in failures
    assert "production_openlineage_attached" in failures
    assert "production_semantic_views_attached" in failures


def test_catalog_publish_manifest_cli_writes_ready_local_manifest(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog" / "bundle.json"
    output_path = tmp_path / "publish" / "manifest.json"
    write_catalog_bundle(ROOT, catalog_path, generated_at="2026-01-15T12:00:00Z")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "catalog-publish-manifest",
            "--catalog",
            str(catalog_path),
            "--output",
            str(output_path),
            "--target-system",
            "datahub",
            "--environment",
            "local",
            "--generated-at",
            "2026-01-15T12:30:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert summary["passed"] is True
    assert summary["publish_state"] == "ready_for_publish"
    assert manifest["target"]["environment"] == "local"


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
        ingest_run_id="catalog-publish-ingest-run",
    )
    recommendation = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="catalog-publish-recsys-snapshot",
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
        producer="https://enterprise-dp.local/openlineage-export",
    )
    write_semantic_view_manifest(
        ROOT,
        semantic_views_path,
        engine="all",
        generated_at="2026-01-15T12:15:00Z",
    )
    return catalog_path, openlineage_path, semantic_views_path
