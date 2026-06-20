from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.contract_impact import (
    build_contract_impact_report,
    validate_contract_impact_report,
    write_contract_impact_report,
)


ROOT = Path(__file__).resolve().parents[1]
BILLING_TOPIC = "finance.billing_transaction.settled.v1"


def test_contract_impact_report_maps_topic_to_downstream_products_and_use_cases() -> None:
    report = build_contract_impact_report(
        ROOT,
        topic_name=BILLING_TOPIC,
        generated_at="2026-06-16T12:00:00Z",
    )

    assert report["artifact_type"] == "contract_impact_report.v1"
    assert report["passed"] is True
    assert report["compatibility"]["passed"] is True
    assert report["impact"]["release_decision"] == "review_required"
    assert report["impact"]["affected_p0_use_case_count"] >= 2
    assert report["impact"]["affected_gold_count"] >= 1
    assert "bronze.events_billing_transaction_settled" in affected_product_names(report)
    assert "gold.finance_revenue_daily" in affected_product_names(report)
    assert {"enterprise-revenue-intelligence", "enterprise-kpi-scorecard"} <= affected_use_case_ids(report)
    assert any(approval["role"] == "topic_owner" for approval in report["required_approvals"])

    validation = validate_contract_impact_report(report)
    assert validation.errors == []


def test_contract_impact_report_blocks_breaking_schema_change_with_p0_use_case_impact(tmp_path: Path) -> None:
    schema_report = tmp_path / "schema-registry" / "billing-breaking.json"
    schema_report.parent.mkdir(parents=True)
    schema_report.write_text(
        json.dumps(
            {
                "artifact_type": "schema_registry_compatibility_report.v1",
                "report_version": 1,
                "generated_at": "2026-06-16T12:00:00Z",
                "registry_uri": "local-test",
                "mode": "local_preflight",
                "compatibility_passed": False,
                "subject_count": 1,
                "summary": {"passed_subjects": 0, "failed_subjects": 1},
                "subjects": [
                    {
                        "subject": f"{BILLING_TOPIC}-value",
                        "topic": BILLING_TOPIC,
                        "contract_path": "contracts/topics/finance.billing_transaction.settled.v1.yaml",
                        "contract_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "contract_version": 2,
                        "product": "billing-platform",
                        "domain": "finance",
                        "compatibility": "BACKWARD_TRANSITIVE",
                        "prior_versions_checked": ["finance.billing_transaction.settled.v1"],
                        "compatibility_passed": False,
                        "checks": [
                            {
                                "check": "backward_transitive_local",
                                "passed": False,
                                "details": {
                                    "prior_topic": "finance.billing_transaction.settled.v1",
                                    "violations": [
                                        "$.payload.amount: type narrowed from ['number'] to ['integer']",
                                        "$: new required fields added: ['settlementBatchId']",
                                    ],
                                },
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = build_contract_impact_report(
        ROOT,
        topic_name=BILLING_TOPIC,
        schema_registry_report_path=schema_report,
        generated_at="2026-06-16T12:05:00Z",
    )

    assert report["passed"] is False
    assert report["compatibility"]["breaking_change_count"] == 2
    assert report["impact"]["release_decision"] == "blocked"
    assert report["impact"]["risk_level"] == "P0"
    assert report["impact"]["affected_p0_use_case_count"] >= 2


def test_contract_impact_writer_and_cli_return_nonzero_for_blocked_change(tmp_path: Path) -> None:
    schema_report = tmp_path / "schema-registry" / "blocked.json"
    schema_report.parent.mkdir(parents=True)
    schema_report.write_text(
        json.dumps(
            {
                "artifact_type": "schema_registry_compatibility_report.v1",
                "report_version": 1,
                "compatibility_passed": False,
                "subject_count": 1,
                "subjects": [
                    {
                        "subject": f"{BILLING_TOPIC}-value",
                        "topic": BILLING_TOPIC,
                        "contract_path": "contracts/topics/finance.billing_transaction.settled.v1.yaml",
                        "contract_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "contract_version": 2,
                        "product": "billing-platform",
                        "domain": "finance",
                        "compatibility": "BACKWARD_TRANSITIVE",
                        "prior_versions_checked": ["finance.billing_transaction.settled.v1"],
                        "compatibility_passed": False,
                        "checks": [
                            {
                                "check": "backward_transitive_local",
                                "passed": False,
                                "details": {"violations": ["$: new required fields added: ['x']"]},
                            }
                        ],
                    }
                ],
                "summary": {"passed_subjects": 0, "failed_subjects": 1},
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "impact" / "report.json"
    result = write_contract_impact_report(
        ROOT,
        output_path,
        topic_name=BILLING_TOPIC,
        schema_registry_report_path=schema_report,
        generated_at="2026-06-16T12:05:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "impact" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "contract-impact-report",
            "--root",
            str(ROOT),
            "--topic",
            BILLING_TOPIC,
            "--schema-registry-report",
            str(schema_report),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert cli_output.is_file()
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["release_decision"] == "blocked"
    assert summary["risk_level"] == "P0"


def affected_product_names(report: dict[str, object]) -> set[str]:
    return {str(item["name"]) for item in report["affected_data_products"] if isinstance(item, dict)}


def affected_use_case_ids(report: dict[str, object]) -> set[str]:
    return {str(item["id"]) for item in report["affected_use_cases"] if isinstance(item, dict)}
