from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.portfolio import (
    build_enterprise_portfolio_readiness_report,
    validate_enterprise_portfolio_readiness_report,
    write_enterprise_portfolio_readiness_report,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T12:00:00Z"
SOURCE_ACTIVATION_LEDGER = ROOT / "governance" / "source-activations.yaml"


def test_portfolio_report_surfaces_group_wide_p0_gaps() -> None:
    report = build_enterprise_portfolio_readiness_report(
        ROOT,
        generated_at=GENERATED_AT,
        source_activation_ledger_path=SOURCE_ACTIVATION_LEDGER,
    )

    assert report["artifact_type"] == "enterprise_portfolio_readiness_report.v1"
    assert report["portfolio_scope"] == "group-enterprise-data-platform"
    assert report["readiness_state"] == "not_ready"
    assert report["p0_ready"] is False
    assert report["summary"]["product_count"] >= 8
    assert report["summary"]["p0_use_case_count"] >= 3
    assert report["summary"]["p0_source_gap_count"] >= 1
    assert report["summary"]["p0_static_source_gap_count"] == (
        report["summary"]["p0_effective_source_gap_count"] + report["summary"]["p0_activation_covered_count"]
    )
    assert report["source_activation_ledger"]["enabled"] is True
    assert report["source_activation_ledger"]["by_state"]["active"] == 1
    assert "enterprise-kpi-scorecard" in report["decision_board"]["blocked_p0_use_cases"]
    assert any(
        action["id"] == "enterprise-kpi-scorecard" and action["action"] == "clear_p0_source_readiness_gaps"
        for action in report["decision_board"]["next_actions"]
    )

    billing = product(report, "billing-platform")
    assert billing["status"] == "pilot"
    assert billing["first_slice"]["contract_status"] == "existing"
    assert billing["first_slice"]["existing_topic_count"] == 1
    assert billing["first_slice"]["existing_data_product_count"] == 3
    assert "enterprise-revenue-intelligence" in billing["required_by_p0_use_cases"]
    assert "finance-benefit-reconciliation" in billing["required_by_p0_use_cases"]
    assert billing["source_readiness"]["p0_static_source_gap_count"] == 1
    assert billing["source_readiness"]["p0_effective_source_gap_count"] == 0
    assert billing["source_readiness"]["activation_covered_count"] == 1
    assert billing["source_readiness"]["activations"][0]["activation_id"] == "activate-billing-platform-source-staging-20260118"
    assert "p0_sources_production_ready" not in blocker_gates(billing)

    revenue = use_case(report, "enterprise-revenue-intelligence")
    assert revenue["priority"] == "P0"
    assert revenue["status"] == "pilot"
    assert revenue["implementation"]["pipeline_count"] == 1
    assert revenue["data_product_contracts"]["planned"] == []
    assert revenue["draft_source_products"] == []
    assert "p0_source_readiness" in blocker_gates(revenue)

    finance = use_case(report, "finance-benefit-reconciliation")
    assert finance["priority"] == "P0"
    assert finance["status"] == "pilot"
    assert finance["implementation"]["pipeline_count"] == 1
    assert finance["draft_source_products"] == []
    assert "p0_source_readiness" in blocker_gates(finance)

    scorecard = use_case(report, "enterprise-kpi-scorecard")
    assert scorecard["priority"] == "P0"
    assert scorecard["status"] == "pilot"
    assert scorecard["implementation"]["pipeline_count"] == 1
    assert scorecard["data_product_contracts"]["planned"] == []
    assert scorecard["draft_source_products"] == []
    assert "p0_source_readiness" in blocker_gates(scorecard)

    validation = validate_enterprise_portfolio_readiness_report(report)
    assert validation.errors == []


def test_portfolio_without_activation_overlay_keeps_static_source_gap() -> None:
    report = build_enterprise_portfolio_readiness_report(
        ROOT,
        generated_at=GENERATED_AT,
    )

    assert report["source_activation_ledger"]["enabled"] is False
    assert report["summary"]["p0_static_source_gap_count"] == report["summary"]["p0_effective_source_gap_count"]

    billing = product(report, "billing-platform")
    assert billing["source_readiness"]["p0_static_source_gap_count"] == 1
    assert billing["source_readiness"]["p0_effective_source_gap_count"] == 1
    assert "p0_sources_production_ready" in blocker_gates(billing)


def test_portfolio_writer_and_cli_return_nonzero_until_p0_ready(tmp_path: Path) -> None:
    output_path = tmp_path / "portfolio" / "report.json"
    result = write_enterprise_portfolio_readiness_report(
        ROOT,
        output_path,
        generated_at=GENERATED_AT,
        source_activation_ledger_path=SOURCE_ACTIVATION_LEDGER,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "portfolio" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "portfolio-readiness-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            GENERATED_AT,
            "--source-activation-ledger",
            str(SOURCE_ACTIVATION_LEDGER),
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
    assert summary["summary"]["p0_blocker_count"] >= 1
    assert "enterprise-kpi-scorecard" in summary["blocked_p0_use_cases"]
    assert cli_output.is_file()


def product(report: dict[str, object], product_code: str) -> dict[str, object]:
    products = report["product_matrix"]
    assert isinstance(products, list)
    return next(item for item in products if isinstance(item, dict) and item["product_code"] == product_code)


def use_case(report: dict[str, object], use_case_id: str) -> dict[str, object]:
    use_cases = report["use_case_matrix"]
    assert isinstance(use_cases, list)
    return next(item for item in use_cases if isinstance(item, dict) and item["use_case_id"] == use_case_id)


def blocker_gates(item: dict[str, object]) -> set[str]:
    blockers = item["blockers"]
    assert isinstance(blockers, list)
    return {str(blocker["gate"]) for blocker in blockers if isinstance(blocker, dict)}
