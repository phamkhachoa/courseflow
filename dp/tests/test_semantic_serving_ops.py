from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.semantic_metric_certification import write_semantic_metric_certification_report
from enterprise_dp.semantic_serving_ops import (
    build_semantic_metric_serving_ops_report,
    write_semantic_metric_serving_ops_report,
)
from enterprise_dp.semantic_views import write_semantic_view_manifest


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T18:30:00Z"


def test_semantic_serving_ops_allows_local_preflight_without_runtime_evidence() -> None:
    report = build_semantic_metric_serving_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "semantic_metric_serving_ops_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["metric_count"] >= 30
    assert report["summary"]["semantic_view_count"] == report["summary"]["metric_count"] * 2


def test_semantic_serving_ops_blocks_prod_without_deployment_and_usage_evidence(tmp_path: Path) -> None:
    certified_root = build_certified_semantic_root(tmp_path)

    report = build_semantic_metric_serving_ops_report(
        certified_root,
        environment="prod",
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}
    metric = report["decision_board"]["failed_metrics"][0]

    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert {
        "metric_certification_report_attached_for_production_like",
        "semantic_view_manifest_attached_for_production_like",
        "serving_deployment_evidence_attached_for_production_like",
        "usage_evidence_attached_for_production_like",
    } <= failed
    assert {"serving_deployment_missing", "usage_tracking_missing"} <= set(metric["issues"])
    assert report["summary"]["certification_evidence_source"] == "generated_from_root"


def test_semantic_serving_ops_passes_prod_with_certified_metrics_deployment_and_usage(tmp_path: Path) -> None:
    certified_root = build_certified_semantic_root(tmp_path)
    artifacts = write_semantic_serving_artifacts(certified_root, tmp_path)

    report = build_semantic_metric_serving_ops_report(
        certified_root,
        environment="prod",
        semantic_view_manifest_path=artifacts["manifest"],
        metric_certification_report_path=artifacts["certification"],
        serving_deployment_evidence_path=artifacts["deployment"],
        usage_evidence_path=artifacts["usage"],
        generated_at=GENERATED_AT,
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["certified_metric_count"] == report["summary"]["metric_count"]
    assert report["summary"]["certification_evidence_attached"] is True
    assert report["summary"]["certification_approved_metric_count"] == report["summary"]["metric_count"]
    assert report["summary"]["deployment_evidence_attached"] is True
    assert report["summary"]["usage_evidence_attached"] is True


def test_semantic_serving_ops_blocks_manifest_hash_mismatch(tmp_path: Path) -> None:
    certified_root = build_certified_semantic_root(tmp_path)
    artifacts = write_semantic_serving_artifacts(
        certified_root,
        tmp_path,
        deployment_updates={"semantic_view_manifest_hash": "sha256:bad"},
    )

    report = build_semantic_metric_serving_ops_report(
        certified_root,
        environment="prod",
        semantic_view_manifest_path=artifacts["manifest"],
        metric_certification_report_path=artifacts["certification"],
        serving_deployment_evidence_path=artifacts["deployment"],
        usage_evidence_path=artifacts["usage"],
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}

    assert report["passed"] is False
    assert "serving_deployment_manifest_hash_matches" in failed


def test_semantic_serving_ops_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "ops" / "semantic-serving.json"
    result = write_semantic_metric_serving_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "ops" / "cli-semantic-serving.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "semantic-metric-serving-ops-report",
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


def build_certified_semantic_root(tmp_path: Path) -> Path:
    root = tmp_path / "certified-root"
    for directory in ("contracts", "domains", "governance", "use-cases"):
        shutil.copytree(ROOT / directory, root / directory)
    (root / "platform").mkdir(parents=True)
    shutil.copytree(ROOT / "platform" / "serving", root / "platform" / "serving")

    registry_path = root / "platform" / "serving" / "semantic-metrics.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for metric in registry["metrics"]:
        metric["status"] = "certified"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    return root


def write_semantic_serving_artifacts(
    root: Path,
    tmp_path: Path,
    *,
    deployment_updates: dict | None = None,
) -> dict[str, Path]:
    manifest_path = tmp_path / "semantic-serving" / "semantic-views.json"
    manifest = write_semantic_view_manifest(root, manifest_path, generated_at=GENERATED_AT)
    certification_path = tmp_path / "semantic-serving" / "metric-certification.json"
    write_semantic_metric_certification_report(
        root,
        certification_path,
        environment="prod",
        generated_at=GENERATED_AT,
    )
    deployment = {
        "artifact_type": "semantic_serving_deployment_evidence.v1",
        "environment": "prod",
        "generated_at": GENERATED_AT,
        "semantic_view_manifest_hash": hash_file(manifest_path),
        "passed": True,
        "summary": {
            "view_count": len(manifest["views"]),
            "failed_view_count": 0,
        },
        "views": [
            {
                "metric_id": view["metric_id"],
                "engine": view["engine"],
                "view_name": view["view_name"],
                "deployed": True,
                "smoke_test_passed": True,
                "access_policy_checked": True,
            }
            for view in manifest["views"]
        ],
    }
    deployment.update(deployment_updates or {})
    deployment_path = tmp_path / "semantic-serving" / "deployment.json"
    deployment_path.write_text(f"{canonical_json(deployment)}\n", encoding="utf-8")

    usage = {
        "artifact_type": "semantic_metric_usage_evidence.v1",
        "environment": "prod",
        "generated_at": GENERATED_AT,
        "passed": True,
        "summary": {
            "metric_count": manifest["summary"]["metric_count"],
            "usage_tracking_disabled_count": 0,
        },
        "metrics": [
            {
                "metric_id": metric_id,
                "usage_tracking_enabled": True,
                "active_consumer_count": 1,
                "last_queried_at": GENERATED_AT,
            }
            for metric_id in sorted({view["metric_id"] for view in manifest["views"]})
        ],
    }
    usage_path = tmp_path / "semantic-serving" / "usage.json"
    usage_path.write_text(f"{canonical_json(usage)}\n", encoding="utf-8")

    return {"manifest": manifest_path, "certification": certification_path, "deployment": deployment_path, "usage": usage_path}
