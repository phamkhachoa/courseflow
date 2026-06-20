from __future__ import annotations

from pathlib import Path

from enterprise_dp.quality_profiles import evaluate_quality_profile, validate_quality_profile_registry


ROOT = Path(__file__).resolve().parents[1]


def test_repository_quality_profile_registry_is_valid() -> None:
    result = validate_quality_profile_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_quality_profile_evaluator_blocks_empty_primary_output() -> None:
    evaluation = evaluate_quality_profile(
        ROOT,
        profile_id="p0-finance-benefit-reconciliation",
        use_case_id="finance-benefit-reconciliation",
        primary_output="gold.finance_benefit_reconciliation",
        output_data_products=[
            "silver.finance_benefit_transactions",
            "gold.finance_benefit_reconciliation",
        ],
        ingestion_manifest={"quarantine": {"row_count": 0}},
        pipeline_manifest={
            "upstream_quality_passed": True,
            "layers": {
                "silver.finance_benefit_transactions": {
                    "quality_passed": True,
                    "content_hash": "sha256:silver",
                    "row_count": 4,
                },
                "gold.finance_benefit_reconciliation": {
                    "quality_passed": True,
                    "content_hash": "sha256:gold",
                    "row_count": 0,
                },
            },
        },
    )
    checks = {check["name"]: check for check in evaluation["checks"]}

    assert evaluation["passed"] is False
    assert checks["primary_output_min_rows"]["passed"] is False
    assert checks["quarantine_threshold"]["passed"] is True
