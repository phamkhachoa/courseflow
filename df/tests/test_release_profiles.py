from __future__ import annotations

from pathlib import Path

from enterprise_df.release_profiles import evaluate_release_profile, validate_release_profile_registry


ROOT = Path(__file__).resolve().parents[1]


def test_repository_release_profile_registry_is_valid() -> None:
    result = validate_release_profile_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_release_profile_requires_artifacts_and_gates() -> None:
    evaluation = evaluate_release_profile(
        ROOT,
        profile_id="local-medallion-release.v1",
        use_case_id="finance-benefit-reconciliation",
        runner_input_kind="approved_bronze_jsonl",
        environment="local",
        evidence={
            "schema_registry_report_uri": "/tmp/schema.json",
            "access_policy_report_uri": "/tmp/access.json",
            "access_grant_evidence_uri": "/tmp/access-grant.json",
            "retention_evidence_uri": "/tmp/retention.json",
            "quality_profile_hash": "sha256:quality",
            "artifacts": {
                "pipeline_manifest_hash": "sha256:pipeline",
            },
            "gates": [
                {"gate_id": "P0-CONTRACT-COMPATIBILITY", "passed": True},
                {"gate_id": "P0-SCHEMA-REGISTRY-COMPATIBILITY", "passed": True},
                {"gate_id": "P0-ACCESS-POLICY", "passed": True},
                {"gate_id": "P0-ACCESS-GRANT-EVIDENCE", "passed": True},
                {"gate_id": "P0-RETENTION-ERASURE", "passed": True},
                {"gate_id": "P0-PRODUCTION-EVIDENCE", "passed": True},
                {"gate_id": "P0-INGESTION-LAG", "passed": True},
                {"gate_id": "P0-FRESHNESS", "passed": True},
                {"gate_id": "P0-PIPELINE-QUALITY", "passed": True},
                {"gate_id": "P0-QUALITY-PROFILE", "passed": True},
                {"gate_id": "P0-OUTPUT-EVIDENCE", "passed": True},
                {"gate_id": "P0-LAKEHOUSE-SNAPSHOT-EVIDENCE", "passed": True},
                {"gate_id": "P0-CATALOG-LINEAGE", "passed": True},
            ],
        },
    )
    checks = {check["name"]: check for check in evaluation["checks"]}

    assert evaluation["passed"] is False
    assert checks["required_gates_passed"]["passed"] is True
    assert checks["required_artifacts_present"]["passed"] is False
