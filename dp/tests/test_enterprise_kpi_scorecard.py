from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from enterprise_dp.orchestration import run_use_case
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry
from enterprise_dp.pipelines.scorecard import run_executive_scorecard_from_semantic_snapshot


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "enterprise-reporting" / "semantic_metric_snapshot.json"
BUILT_AT = "2026-01-15T11:00:00Z"
EVALUATION_TIME = "2026-01-15T11:00:05Z"
RUNNER_ID = "enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1"


def test_executive_scorecard_runner_materializes_non_pii_gold_outputs(tmp_path: Path) -> None:
    result = run_executive_scorecard_from_semantic_snapshot(
        SAMPLE_INPUT,
        tmp_path,
        snapshot_id="executive-scorecard-snapshot",
        built_at=BUILT_AT,
    )
    kpi_rows = read_jsonl(result.enterprise_kpi_path)
    scorecard_rows = read_jsonl(result.executive_scorecard_path)
    metric_ids = {row["metric_id"] for row in kpi_rows}
    source_products = set(result.manifest["source_data_products"])

    assert result.snapshot_id == "executive-scorecard-snapshot"
    assert result.manifest["pipeline"] == RUNNER_ID
    assert result.manifest["input"]["artifact_type"] == "semantic_metric_snapshot.v1"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["row_count"] == len(scorecard_rows)
    assert len(kpi_rows) == 11
    assert len(scorecard_rows) == 11
    assert "revenue_net" in metric_ids
    assert "critical_access_risk_subject_count" in metric_ids
    assert "p0_data_product_blocker_count" in metric_ids
    assert "quality_sla_breach_count" in metric_ids
    assert "contract_compliance_rate" in metric_ids
    assert "runtime_lineage_gap_count" in metric_ids
    assert "gold.finance_revenue_daily" in source_products
    assert "gold.data_product_inventory" in source_products
    assert {
        "type": "RUN_LAYER_TRANSFORM",
        "source": "gold.enterprise_kpi_daily",
        "target": "gold.executive_scorecard_daily",
    } in result.manifest["lineage_edges"]
    assert result.manifest["layers"]["gold.enterprise_kpi_daily"]["quality_passed"] is True
    assert result.manifest["layers"]["gold.executive_scorecard_daily"]["quality_passed"] is True
    assert all("customer_id_hash" not in row for row in kpi_rows)
    assert all("subject_id_hash" not in row for row in kpi_rows)
    assert all("email" not in row for row in scorecard_rows)


def test_pipeline_registry_runs_executive_scorecard(tmp_path: Path) -> None:
    result = default_pipeline_registry().run(
        RUNNER_ID,
        PipelineRunRequest(
            input_path=SAMPLE_INPUT,
            output_dir=tmp_path,
            options={
                "snapshot_id": "registry-scorecard-snapshot",
                "built_at": BUILT_AT,
            },
        ),
    )

    assert result.snapshot_id == "registry-scorecard-snapshot"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["layers"]["gold.executive_scorecard_daily"]["row_count"] == 11
    assert result.executive_scorecard_path.is_file()


def test_executive_scorecard_runner_rejects_wrong_artifact_type(tmp_path: Path) -> None:
    payload = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
    payload["artifact_type"] = "data_product_control_tower_report.v1"
    bad_input = tmp_path / "bad_snapshot.json"
    bad_input.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="expected artifact_type=semantic_metric_snapshot.v1"):
        run_executive_scorecard_from_semantic_snapshot(bad_input, tmp_path / "out")


def test_executive_scorecard_runner_rejects_direct_identifier_fields(tmp_path: Path) -> None:
    payload = json.loads(SAMPLE_INPUT.read_text(encoding="utf-8"))
    payload["metrics"][0]["customer_id_hash"] = "hash-leaked-to-executive-layer"
    bad_input = tmp_path / "direct_identifier_snapshot.json"
    bad_input.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="direct identifier"):
        run_executive_scorecard_from_semantic_snapshot(bad_input, tmp_path / "out")


def test_run_use_case_orchestrates_enterprise_kpi_scorecard(tmp_path: Path) -> None:
    result = run_use_case(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        use_case_id="enterprise-kpi-scorecard",
        release_id="local-enterprise-kpi-test",
        environment="local",
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        snapshot_id="enterprise-kpi-use-case-snapshot",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is True
    assert result.ingestion is None
    assert result.runner_id == RUNNER_ID
    assert result.topic is None
    assert result.primary_output == "gold.executive_scorecard_daily"
    assert result.evidence["runner_input_kind"] == "semantic_metric_snapshot"
    assert result.evidence["input_data_products"] == [
        "gold.finance_revenue_daily",
        "gold.finance_benefit_reconciliation",
        "gold.customer_360_profile",
        "gold.access_risk_daily",
        "gold.support_sla_daily",
        "gold.recsys_interactions",
        "gold.data_product_inventory",
        "gold.contract_compliance_daily",
        "gold.quality_sla_daily",
        "gold.lineage_coverage_daily",
    ]
    assert result.evidence["output_data_products"] == [
        "gold.enterprise_kpi_daily",
        "gold.executive_scorecard_daily",
    ]
    assert result.evidence["quality_profile_id"] == "p0-enterprise-kpi-scorecard"
    assert gates["P0-INGESTION-LAG"]["passed"] is True
    assert gates["P0-FRESHNESS"]["passed"] is True
    assert gates["P0-PIPELINE-QUALITY"]["passed"] is True
    assert gates["P0-QUALITY-PROFILE"]["passed"] is True
    assert gates["P0-ACCESS-GRANT-EVIDENCE"]["passed"] is True
    assert gates["P0-RETENTION-ERASURE"]["passed"] is True
    assert gates["P0-CATALOG-LINEAGE"]["passed"] is True
    assert gates["P0-RELEASE-EVIDENCE-PROFILE"]["passed"] is True
    assert result.pipeline.manifest_path.is_file()
    assert result.catalog_bundle_path.is_file()
    assert result.evidence_path.is_file()


def test_cli_runs_enterprise_kpi_scorecard_use_case(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-use-case",
            "--root",
            str(ROOT),
            "--use-case-id",
            "enterprise-kpi-scorecard",
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-enterprise-kpi-test",
            "--environment",
            "local",
            "--built-at",
            BUILT_AT,
            "--evaluation-time",
            EVALUATION_TIME,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["use_case_id"] == "enterprise-kpi-scorecard"
    assert output["runner_id"] == RUNNER_ID
    assert output["topic"] is None
    assert output["primary_output"] == "gold.executive_scorecard_daily"
    assert output["release_passed"] is True
    assert output["gates"]["P0-RELEASE-EVIDENCE-PROFILE"] is True
    assert Path(output["pipeline_manifest_path"]).is_file()
    assert Path(output["evidence_path"]).is_file()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def gates_by_id(evidence: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(gate["gate_id"]): gate
        for gate in evidence["gates"]
        if isinstance(gate, dict)
    }
