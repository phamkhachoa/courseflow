from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.control_tower import (
    build_data_product_control_tower_report,
    validate_data_product_control_tower_report,
    write_data_product_control_tower_report,
)
from enterprise_df.orchestration import run_use_case
from enterprise_df.pipelines.control_tower import run_control_tower_gold_materialization


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"


def test_control_tower_report_aggregates_enterprise_data_product_evidence() -> None:
    report = build_data_product_control_tower_report(
        ROOT,
        generated_at="2026-06-16T11:00:00Z",
    )

    assert report["artifact_type"] == "data_product_control_tower_report.v1"
    assert report["readiness_state"] == "not_ready"
    assert report["p0_ready"] is False
    assert report["passed"] is False
    assert report["summary"]["data_product_count"] >= 13
    assert report["summary"]["capability_blocker_count"] >= 1
    assert report["summary"]["gold_release_coverage"]["gold_count"] >= 6
    assert "data-product-control-tower" in report["scope"]["use_cases"]
    assert "enterprise-data-foundation" in report["scope"]["products"]
    assert report["inputs"]["catalog_bundle"]["source"] == "generated_from_root"
    assert report["inputs"]["capability_maturity_report"]["readiness_state"] == "not_ready"
    assert any(row["gate"] == "contract_active" for row in report["gate_matrix"])
    assert any(blocker["scope"] == "platform_capability" for blocker in report["blockers"])

    inventory = data_product(report, "gold.data_product_inventory")
    assert inventory["product"] == "enterprise-data-foundation"
    assert inventory["domain"] == "enterprise-reporting"
    assert inventory["quality"]["quality_profiles"][0]["id"] == "p0-data-product-control-tower"
    assert inventory["readiness_state"] == "blocked"

    validation = validate_data_product_control_tower_report(report)
    assert validation.errors == []


def test_control_tower_report_uses_release_evidence_when_attached(tmp_path: Path) -> None:
    run = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path / "finance-run",
        use_case_id="finance-benefit-reconciliation",
        release_id="control-tower-finance-release",
        environment="local",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
        snapshot_id="control-tower-finance-snapshot",
    )
    report = build_data_product_control_tower_report(
        ROOT,
        catalog_bundle_path=run.catalog_bundle_path,
        release_evidence_paths=[run.evidence_path],
        generated_at="2026-06-16T11:00:00Z",
    )

    finance = data_product(report, "gold.finance_benefit_reconciliation")
    assert finance["release_evidence"]["covered"] is True
    assert finance["release_evidence"]["passed"] is True
    assert finance["release_evidence"]["release_count"] == 1
    assert report["release_evidence"]["covered_data_products"] == [
        "gold.finance_benefit_reconciliation",
        "silver.finance_benefit_transactions",
    ]


def test_control_tower_writer_and_cli_block_until_p0_ready(tmp_path: Path) -> None:
    output_path = tmp_path / "control-tower" / "report.json"
    result = write_data_product_control_tower_report(
        ROOT,
        output_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "control-tower" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-06-16T11:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["readiness_state"] == "not_ready"
    assert summary["p0_ready"] is False
    assert summary["passed"] is False
    assert summary["blocker_count"] >= 1
    assert cli_output.is_file()


def test_control_tower_materializes_four_operational_gold_outputs(tmp_path: Path) -> None:
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    result = run_control_tower_gold_materialization(
        report_path,
        tmp_path / "pipeline",
        snapshot_id="control-tower-snapshot",
        built_at="2026-06-16T11:05:00Z",
    )

    assert result.manifest["pipeline"] == "control_tower.materialize_gold.from_report.v1"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["input"]["artifact_type"] == "data_product_control_tower_report.v1"
    assert set(result.manifest["layers"]) == {
        "gold.data_product_inventory",
        "gold.contract_compliance_daily",
        "gold.quality_sla_daily",
        "gold.lineage_coverage_daily",
    }
    assert result.manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.contract_compliance_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.contract_compliance_daily",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.lineage_coverage_daily",
        },
    ]

    inventory = read_jsonl(result.inventory_path)
    contract = read_jsonl(result.contract_compliance_path)
    quality = read_jsonl(result.quality_sla_path)
    lineage = read_jsonl(result.lineage_coverage_path)
    assert len(inventory) == len(contract) == len(quality) == len(lineage) >= 13

    inventory_row = next(row for row in inventory if row["data_product_name"] == "gold.data_product_inventory")
    assert inventory_row["environment"] == "local"
    assert inventory_row["business_owner"] == "enterprise-data-platform-po"
    assert inventory_row["technical_owner"] == "senior-data-platform"
    assert inventory_row["quality_profile_id"] == "p0-data-product-control-tower"
    assert inventory_row["active_snapshot_id"] == "control-tower-snapshot"
    assert inventory_row["lifecycle_state"] == "DRAFT_CONTRACT"

    contract_row = next(row for row in contract if row["data_product_name"] == "gold.data_product_inventory")
    assert contract_row["compatibility_status"] == "NOT_ATTACHED"
    assert contract_row["breaking_change_risk"] == "LOW"
    assert contract_row["privacy_policy_passed"] is True
    assert contract_row["highest_severity"] in {"P0", "NONE"}

    quality_row = next(row for row in quality if row["data_product_name"] == "gold.data_product_inventory")
    assert quality_row["release_gate_status"] == "MISSING"
    assert quality_row["sla_status"] in {"RED", "UNKNOWN", "GREEN"}
    assert "assignee" in quality_row

    lineage_row = next(row for row in lineage if row["data_product_name"] == "gold.data_product_inventory")
    assert lineage_row["catalog_publish_status"] == "NOT_ATTACHED"
    assert "missing_lineage_reason" in lineage_row
    assert "owner_action_required" in lineage_row


def test_control_tower_materialization_rejects_wrong_artifact_type(tmp_path: Path) -> None:
    bad_input = tmp_path / "bad.json"
    bad_input.write_text(json.dumps({"artifact_type": "other.v1", "data_products": []}), encoding="utf-8")

    try:
        run_control_tower_gold_materialization(bad_input, tmp_path / "pipeline")
    except ValueError as exc:
        assert "data_product_control_tower_report.v1" in str(exc)
    else:
        raise AssertionError("wrong artifact_type was accepted")


def test_control_tower_use_case_materialization_passes_local_release_gates(tmp_path: Path) -> None:
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        generated_at="2026-06-16T11:00:00Z",
    )
    result = run_use_case(
        ROOT,
        report_path,
        tmp_path / "run",
        use_case_id="data-product-control-tower",
        release_id="control-tower-release",
        environment="local",
        built_at="2026-06-16T11:05:00Z",
        evaluation_time="2026-06-16T11:06:00Z",
        snapshot_id="control-tower-release-snapshot",
    )
    gates = {gate["gate_id"]: gate["passed"] for gate in result.evidence["gates"]}

    assert result.runner_id == "control_tower.materialize_gold.from_report.v1"
    assert result.primary_output == "gold.data_product_inventory"
    assert result.evidence["release_passed"] is True
    assert gates["P0-OUTPUT-EVIDENCE"] is True
    assert gates["P0-QUALITY-PROFILE"] is True
    assert gates["P0-CATALOG-LINEAGE"] is True
    assert result.pipeline.inventory_path.is_file()


def data_product(report: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in report["data_products"] if item["name"] == name)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
