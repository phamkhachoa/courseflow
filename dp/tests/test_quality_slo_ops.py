from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog import build_catalog_bundle
from enterprise_dp.quality_slo_ops import build_quality_slo_ops_report, write_quality_slo_ops_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T16:30:00Z"
DATA_PRODUCT = "gold.recsys_interactions"


def test_quality_slo_ops_allows_local_preflight_without_evidence() -> None:
    report = build_quality_slo_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "quality_slo_release_gates_ops_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["failed_product_count"] == 0


def test_quality_slo_ops_blocks_prod_without_release_runtime_and_alert_evidence() -> None:
    report = build_quality_slo_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle=single_product_catalog(),
        generated_at=GENERATED_AT,
    )
    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}
    product = report["decision_board"]["failed_products"][0]

    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert {
        "release_evidence_attached_for_production_like",
        "quality_runtime_evidence_attached_for_production_like",
        "alert_evidence_attached_for_production_like",
    } <= failed
    assert {"release_evidence_missing", "runtime_quality_missing"} <= set(product["issues"])


def test_quality_slo_ops_passes_prod_with_release_runtime_and_alert_evidence(tmp_path: Path) -> None:
    artifacts = write_quality_slo_artifacts(tmp_path)

    report = build_quality_slo_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle=single_product_catalog(),
        release_evidence_paths=[artifacts["release"]],
        quality_runtime_evidence_path=artifacts["runtime"],
        alert_evidence_path=artifacts["alert"],
        generated_at=GENERATED_AT,
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["runtime_quality_attached"] is True
    assert report["summary"]["runtime_freshness_breach_count"] == 0


def test_quality_slo_ops_blocks_stale_runtime_freshness(tmp_path: Path) -> None:
    artifacts = write_quality_slo_artifacts(
        tmp_path,
        runtime_row_updates={"freshness_status": "RED", "age_seconds": 901, "slo_seconds": 900},
        runtime_summary_updates={"freshness_breach_count": 1},
    )

    report = build_quality_slo_ops_report(
        ROOT,
        environment="prod",
        catalog_bundle=single_product_catalog(),
        release_evidence_paths=[artifacts["release"]],
        quality_runtime_evidence_path=artifacts["runtime"],
        alert_evidence_path=artifacts["alert"],
        generated_at=GENERATED_AT,
    )
    product = report["decision_board"]["failed_products"][0]

    assert report["passed"] is False
    assert "runtime_freshness_breach" in product["issues"]
    assert report["summary"]["runtime_freshness_breach_count"] == 1


def test_quality_slo_ops_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "ops" / "quality-slo.json"
    result = write_quality_slo_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "ops" / "cli-quality-slo.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "quality-slo-release-gates-ops-report",
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


def write_quality_slo_artifacts(
    tmp_path: Path,
    *,
    runtime_row_updates: dict[str, object] | None = None,
    runtime_summary_updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    release_path = tmp_path / "release" / "evidence.json"
    runtime_path = tmp_path / "runtime" / "quality.json"
    alert_path = tmp_path / "alerts" / "slo.json"
    release = {
        "release_id": "quality-slo-release",
        "environment": "prod",
        "generated_at": GENERATED_AT,
        "use_case_id": "ml-feature-governance",
        "runner_id": "recommendation.from_approved_bronze.v1",
        "primary_output": DATA_PRODUCT,
        "output_data_products": [DATA_PRODUCT],
        "quality_profile_id": "p0-gold-ml-feature",
        "quality_profile_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
        "release_evidence_profile_id": "p0-standard-gold-release",
        "release_evidence_profile_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        "freshness_report": {
            DATA_PRODUCT: {"age_seconds": 120, "slo_seconds": 900, "passed": True},
        },
        "quality_report": {
            "pipeline_quality_passed": True,
            "quarantine_rows": 0,
        },
        "gates": [
            {"gate_id": "P0-INGESTION-LAG", "passed": True, "details": {"max_lag_seconds": 60}},
            {"gate_id": "P0-FRESHNESS", "passed": True, "details": {DATA_PRODUCT: {"age_seconds": 120, "slo_seconds": 900}}},
            {"gate_id": "P0-PIPELINE-QUALITY", "passed": True, "details": {"pipeline_quality_passed": True}},
            {"gate_id": "P0-QUALITY-PROFILE", "passed": True, "details": {"profile_id": "p0-gold-ml-feature"}},
            {"gate_id": "P0-RELEASE-EVIDENCE-PROFILE", "passed": True, "details": {"profile_id": "p0-standard-gold-release"}},
            {"gate_id": "P0-OUTPUT-EVIDENCE", "passed": True, "details": {"primary_output": DATA_PRODUCT}},
        ],
        "release_passed": True,
    }
    runtime_row = {
        "data_product": DATA_PRODUCT,
        "quality_tool": "great_expectations",
        "quality_profile_id": "p0-gold-ml-feature",
        "validation_passed": True,
        "failed_check_count": 0,
        "freshness_status": "GREEN",
        "age_seconds": 120,
        "slo_seconds": 900,
        "quarantine_row_count": 0,
    }
    runtime_row.update(runtime_row_updates or {})
    runtime_summary = {
        "data_product_count": 1,
        "failed_check_count": 0,
        "freshness_breach_count": 0,
    }
    runtime_summary.update(runtime_summary_updates or {})
    runtime = {
        "artifact_type": "quality_runtime_evidence.v1",
        "environment": "prod",
        "generated_at": GENERATED_AT,
        "quality_tool": "great_expectations",
        "synthetic": False,
        "summary": runtime_summary,
        "data_products": [runtime_row],
        "passed": runtime_summary["failed_check_count"] == 0 and runtime_summary["freshness_breach_count"] == 0,
    }
    alert = {
        "artifact_type": "slo_alert_evidence.v1",
        "environment": "prod",
        "generated_at": GENERATED_AT,
        "status": "green",
        "summary": {
            "open_p0_incident_count": 0,
            "sla_breached_count": 0,
            "burn_rate_status": "green",
        },
        "passed": True,
    }
    write_json(release_path, release)
    write_json(runtime_path, runtime)
    write_json(alert_path, alert)
    return {"release": release_path, "runtime": runtime_path, "alert": alert_path}


def single_product_catalog() -> dict[str, object]:
    catalog = build_catalog_bundle(ROOT, generated_at=GENERATED_AT)
    products = [
        product
        for product in catalog["data_products"]
        if product["name"] == DATA_PRODUCT
    ]
    catalog["data_products"] = products
    catalog["summary"] = {**catalog["summary"], "data_product_count": len(products)}
    return catalog


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
