from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from enterprise_dp.access_policy import write_access_policy_report
from enterprise_dp.attestations import attestation_signing_payload
from enterprise_dp.orchestration import run_recommendation_slice
from enterprise_dp.catalog import write_catalog_bundle
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.offset_ledger import write_offset_ledger_report
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze
from enterprise_dp.release import build_recommendation_release_evidence
from enterprise_dp.release_profiles import hash_release_profile_registry
from enterprise_dp.schema_registry import write_schema_registry_report
from enterprise_dp.snapshot_evidence import data_product_contract, write_snapshot_evidence_report


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = ROOT / "samples" / "recommendation" / "tracking.jsonl"
INGESTED_AT = "2026-01-15T10:10:00Z"
BUILT_AT = "2026-01-15T10:10:05Z"
EVALUATION_TIME = "2026-01-15T10:10:10Z"
TEST_SIGNING_SEED = bytes(range(32))


def test_recommendation_slice_orchestrates_artifacts_and_passes_release_gates(tmp_path: Path) -> None:
    result = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        release_id="local-slice-pass",
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        schema_id="local-schema-001",
        code_commit_sha="abc123",
        approver="sa-data-platform",
    )

    evidence = json.loads(result.evidence_path.read_text(encoding="utf-8"))
    gates = gates_by_id(evidence)

    assert evidence == result.evidence
    assert evidence["release_passed"] is True
    assert all(gate["passed"] is True for gate in evidence["gates"])
    assert gates["P0-CONTRACT-COMPATIBILITY"]["details"]["errors"] == []
    assert gates["P0-INGESTION-LAG"]["details"]["max_lag_seconds"] <= 900
    assert evidence["quality_report"]["approved_rows"] == 3
    assert evidence["quality_report"]["quarantine_rows"] == 0
    assert evidence["lineage_catalog"]["run_evidence_count"] == 2
    assert evidence["contract_versions"]["topic:recommendation.tracking.v1"] == 1
    assert evidence["code_commit_sha"] == "abc123"
    assert evidence["approver"] == "sa-data-platform"
    assert result.ingestion.manifest_path.is_file()
    assert result.medallion.manifest_path.is_file()
    assert result.catalog_bundle_path.is_file()


def test_recommendation_slice_blocks_release_when_quarantine_exists(tmp_path: Path) -> None:
    good, bad, *_ = read_jsonl(SAMPLE_INPUT)
    bad["headers"] = {"Authorization": "secret-token"}
    source = tmp_path / "mixed.jsonl"
    write_jsonl(source, [good, bad])

    result = run_recommendation_slice(
        ROOT,
        source,
        tmp_path / "out",
        release_id="local-slice-quarantine",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-QUALITY"]["passed"] is False
    assert gates["P0-QUALITY"]["details"]["quarantine_rows"] == 1
    assert result.evidence["quality_report"]["ingestion_quality_passed"] is False
    assert result.evidence["quality_report"]["medallion_quality_passed"] is False
    assert result.evidence_path.is_file()
    assert result.catalog_bundle_path.is_file()


def test_recommendation_slice_blocks_release_when_ingestion_lag_exceeds_slo(tmp_path: Path) -> None:
    result = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path,
        release_id="local-slice-lag",
        ingested_at="2026-01-15T10:30:00Z",
        built_at="2026-01-15T10:30:05Z",
        evaluation_time="2026-01-15T10:30:10Z",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-INGESTION-LAG"]["passed"] is False
    assert gates["P0-INGESTION-LAG"]["details"]["max_lag_seconds"] > 900
    assert gates["P0-QUALITY"]["passed"] is True


def test_recommendation_slice_requires_production_evidence_for_prod(tmp_path: Path) -> None:
    missing = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "missing",
        release_id="prod-missing-evidence",
        environment="prod",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    missing_gates = gates_by_id(missing.evidence)

    assert missing.evidence["release_passed"] is False
    assert missing_gates["P0-PRODUCTION-EVIDENCE"]["passed"] is False
    assert missing_gates["P0-QUALITY"]["passed"] is True

    unverified = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "unverified",
        release_id="prod-unverified-external-evidence",
        environment="prod",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        code_commit_sha="abc123",
        schema_registry_report_uri="s3://dp-evidence/schema-registry/prod-unverified.json",
        schema_registry_report_hash="sha256:abc123",
        validator_output_uri="s3://dp-evidence/validators/prod-unverified.json",
        access_policy_check_id="access-check-001",
        access_policy_report_uri="s3://dp-evidence/access-policy/prod-unverified.json",
        access_policy_report_hash="sha256:def456",
        access_grant_evidence_uri="s3://dp-evidence/access-grants/prod-unverified.json",
        access_grant_evidence_hash="sha256:grant789",
        retention_evidence_uri="s3://dp-evidence/retention/prod-unverified.json",
        retention_evidence_hash="sha256:retention012",
        snapshot_evidence_uri="s3://dp-evidence/snapshots/prod-unverified.json",
        snapshot_evidence_hash="sha256:snapshot345",
        approver="sa-data-platform",
    )
    unverified_gates = gates_by_id(unverified.evidence)

    assert unverified.evidence["release_passed"] is False
    assert unverified_gates["P0-PRODUCTION-EVIDENCE"]["passed"] is True
    assert unverified_gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["passed"] is False
    assert unverified_gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["details"]["reason"] == "external_reference_unverified"
    assert unverified_gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["passed"] is False
    assert unverified_gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["details"]["reason"] == "external_reference_unverified"

    release_id = "prod-complete-evidence"
    probe = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "complete-probe",
        release_id=release_id,
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    attestation_dir = tmp_path / "attestations"
    schema_attestation = write_external_attestation(attestation_dir / "schema.json", "schema_registry", release_id=release_id)
    access_policy_attestation = write_external_attestation(attestation_dir / "access-policy.json", "access_policy", release_id=release_id)
    access_grant_attestation = write_external_attestation(attestation_dir / "access-grant.json", "access_grant", release_id=release_id)
    retention_attestation = write_external_attestation(
        attestation_dir / "retention.json",
        "retention_erasure",
        release_id=release_id,
        data_product="gold.recsys_interactions",
        dataset_snapshot_id=probe.medallion.snapshot_id,
        content_hash=probe.medallion.manifest["content_hash"],
    )
    snapshot_evidence = write_recommendation_snapshot_evidence(
        tmp_path / "snapshot-evidence" / "complete.json",
        release_id=release_id,
        ingestion=probe.ingestion,
        medallion=probe.medallion,
    )

    complete_evidence = build_recommendation_release_evidence(
        ROOT,
        release_id=release_id,
        environment="prod",
        ingestion_manifest_path=probe.ingestion.manifest_path,
        medallion_manifest_path=probe.medallion.manifest_path,
        catalog_bundle_path=probe.catalog_bundle_path,
        approved_bronze_path=probe.ingestion.approved_path,
        output_path=tmp_path / "complete" / "evidence.json",
        generated_at=EVALUATION_TIME,
        code_commit_sha="abc123",
        schema_registry_report_uri=schema_attestation.as_posix(),
        schema_registry_report_hash=sha256_file(schema_attestation),
        validator_output_uri="s3://dp-evidence/validators/prod-complete.json",
        access_policy_check_id="access-check-001",
        access_policy_report_uri=access_policy_attestation.as_posix(),
        access_policy_report_hash=sha256_file(access_policy_attestation),
        access_grant_evidence_uri=access_grant_attestation.as_posix(),
        access_grant_evidence_hash=sha256_file(access_grant_attestation),
        retention_evidence_uri=retention_attestation.as_posix(),
        retention_evidence_hash=sha256_file(retention_attestation),
        snapshot_evidence_uri=snapshot_evidence.as_posix(),
        snapshot_evidence_hash=sha256_file(snapshot_evidence),
        approver="sa-data-platform",
    )
    complete_gates = gates_by_id(complete_evidence)

    assert complete_evidence["release_passed"] is True
    assert complete_gates["P0-PRODUCTION-EVIDENCE"]["passed"] is True
    assert complete_gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["passed"] is True
    assert complete_gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["details"]["checked"] == "external_evidence_attestation.v1"
    assert complete_gates["P0-ACCESS-GRANT-EVIDENCE"]["passed"] is True
    assert complete_gates["P0-RETENTION-ERASURE"]["passed"] is True


def test_recommendation_slice_rejects_retention_attestation_bound_to_wrong_content(tmp_path: Path) -> None:
    release_id = "prod-retention-attestation-wrong-content"
    probe = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "wrong-content-probe",
        release_id=release_id,
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    attestation_dir = tmp_path / "attestations"
    schema_attestation = write_external_attestation(attestation_dir / "schema.json", "schema_registry", release_id=release_id)
    access_policy_attestation = write_external_attestation(attestation_dir / "access-policy.json", "access_policy", release_id=release_id)
    access_grant_attestation = write_external_attestation(attestation_dir / "access-grant.json", "access_grant", release_id=release_id)
    retention_attestation = write_external_attestation(
        attestation_dir / "retention.json",
        "retention_erasure",
        release_id=release_id,
        data_product="gold.recsys_interactions",
        dataset_snapshot_id=probe.medallion.snapshot_id,
        content_hash="sha256:wrong-content",
    )

    result = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "prod-wrong-content",
        release_id=release_id,
        environment="prod",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        code_commit_sha="abc123",
        schema_registry_report_uri=schema_attestation.as_posix(),
        schema_registry_report_hash=sha256_file(schema_attestation),
        validator_output_uri="s3://dp-evidence/validators/prod-retention-attestation-wrong-content.json",
        access_policy_check_id="access-check-001",
        access_policy_report_uri=access_policy_attestation.as_posix(),
        access_policy_report_hash=sha256_file(access_policy_attestation),
        access_grant_evidence_uri=access_grant_attestation.as_posix(),
        access_grant_evidence_hash=sha256_file(access_grant_attestation),
        retention_evidence_uri=retention_attestation.as_posix(),
        retention_evidence_hash=sha256_file(retention_attestation),
        approver="sa-data-platform",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-RETENTION-ERASURE"]["passed"] is False
    assert gates["P0-RETENTION-ERASURE"]["details"]["required"]["content_hash"] is False


def test_recommendation_slice_builds_prod_retention_report_from_job_evidence_input(tmp_path: Path) -> None:
    release_id = "prod-retention-input-evidence"
    probe = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "probe",
        release_id=release_id,
        environment="local",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )
    retention_input = write_retention_job_evidence(
        tmp_path / "retention-job.json",
        release_id=release_id,
        snapshot_id=probe.medallion.snapshot_id,
        content_hash=probe.medallion.manifest["content_hash"],
    )
    attestation_dir = tmp_path / "attestations"
    schema_attestation = write_external_attestation(attestation_dir / "schema.json", "schema_registry", release_id=release_id)
    access_policy_attestation = write_external_attestation(attestation_dir / "access-policy.json", "access_policy", release_id=release_id)
    access_grant_attestation = write_external_attestation(attestation_dir / "access-grant.json", "access_grant", release_id=release_id)

    result = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "prod",
        release_id=release_id,
        environment="prod",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        code_commit_sha="abc123",
        schema_registry_report_uri=schema_attestation.as_posix(),
        schema_registry_report_hash=sha256_file(schema_attestation),
        validator_output_uri="s3://dp-evidence/validators/prod-retention-input.json",
        access_policy_check_id="access-check-001",
        access_policy_report_uri=access_policy_attestation.as_posix(),
        access_policy_report_hash=sha256_file(access_policy_attestation),
        access_grant_evidence_uri=access_grant_attestation.as_posix(),
        access_grant_evidence_hash=sha256_file(access_grant_attestation),
        retention_evidence_input_path=retention_input,
        approver="sa-data-platform",
    )
    gates = gates_by_id(result.evidence)
    retention_report = json.loads(Path(result.evidence["retention_evidence_uri"]).read_text(encoding="utf-8"))

    assert result.evidence["release_passed"] is False
    assert gates["P0-PRODUCTION-EVIDENCE"]["passed"] is False
    assert gates["P0-LAKEHOUSE-SNAPSHOT-EVIDENCE"]["passed"] is False
    assert gates["P0-RETENTION-ERASURE"]["passed"] is True
    assert gates["P0-RETENTION-ERASURE"]["details"]["production_uses_external_input"] is True
    assert retention_report["environment"] == "prod"
    assert retention_report["evidence_source"]["type"] == "external_input"
    assert retention_report["passed"] is True


def test_recommendation_slice_rejects_prod_attestation_environment_mismatch(tmp_path: Path) -> None:
    release_id = "prod-attestation-environment-mismatch"
    attestation_dir = tmp_path / "attestations"
    schema_attestation = write_external_attestation(attestation_dir / "schema.json", "schema_registry", release_id=release_id, environment="dev")
    access_policy_attestation = write_external_attestation(attestation_dir / "access-policy.json", "access_policy", release_id=release_id, environment="dev")
    access_grant_attestation = write_external_attestation(attestation_dir / "access-grant.json", "access_grant", release_id=release_id, environment="dev")
    retention_attestation = write_external_attestation(attestation_dir / "retention.json", "retention_erasure", release_id=release_id, environment="dev")

    result = run_recommendation_slice(
        ROOT,
        SAMPLE_INPUT,
        tmp_path / "prod-mismatch",
        release_id=release_id,
        environment="prod",
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        code_commit_sha="abc123",
        schema_registry_report_uri=schema_attestation.as_posix(),
        schema_registry_report_hash=sha256_file(schema_attestation),
        validator_output_uri="s3://dp-evidence/validators/prod-attestation-env-mismatch.json",
        access_policy_check_id="access-check-001",
        access_policy_report_uri=access_policy_attestation.as_posix(),
        access_policy_report_hash=sha256_file(access_policy_attestation),
        access_grant_evidence_uri=access_grant_attestation.as_posix(),
        access_grant_evidence_hash=sha256_file(access_grant_attestation),
        retention_evidence_uri=retention_attestation.as_posix(),
        retention_evidence_hash=sha256_file(retention_attestation),
        approver="sa-data-platform",
    )
    gates = gates_by_id(result.evidence)

    assert result.evidence["release_passed"] is False
    assert gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["passed"] is False
    assert gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["details"]["required"]["environment"] is False
    assert gates["P0-SCHEMA-REGISTRY-COMPATIBILITY"]["details"]["expected_environment"] == "prod"


def test_cli_runs_recommendation_slice(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "run-recommendation-slice",
            "--root",
            str(ROOT),
            "--input",
            str(SAMPLE_INPUT),
            "--output-dir",
            str(tmp_path),
            "--release-id",
            "cli-local-slice",
            "--environment",
            "local",
            "--ingested-at",
            INGESTED_AT,
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
    assert output["release_id"] == "cli-local-slice"
    assert output["release_passed"] is True
    assert output["gates"]["P0-CATALOG-LINEAGE"] is True
    assert Path(output["evidence_path"]).is_file()


def test_release_evidence_supports_default_generated_timestamp(tmp_path: Path) -> None:
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        tmp_path / "ingestion",
        ingested_at=INGESTED_AT,
        ingest_run_id="default-timestamp-ingest",
    )
    medallion = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        tmp_path / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="default-timestamp-recsys",
        built_at=BUILT_AT,
    )
    catalog_bundle_path = tmp_path / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        ROOT,
        catalog_bundle_path,
        manifest_paths=[ingestion.manifest_path, medallion.manifest_path],
        generated_at=EVALUATION_TIME,
    )
    schema_registry_report = write_schema_registry_report(
        ROOT,
        tmp_path / "evidence" / "schema-registry.default-timestamp.json",
        topic_name="recommendation.tracking.v1",
        generated_at=EVALUATION_TIME,
    )
    access_policy_report = write_access_policy_report(
        ROOT,
        tmp_path / "evidence" / "access-policy.default-timestamp.json",
        data_product_name="gold.recsys_interactions",
        environment="local",
        release_id="default-timestamp",
        dataset_snapshot_id=medallion.snapshot_id,
        table_version=medallion.manifest["content_hash"],
        content_hash=medallion.manifest["content_hash"],
        row_count=medallion.manifest["row_count"],
        generated_at=EVALUATION_TIME,
    )

    evidence = build_recommendation_release_evidence(
        ROOT,
        release_id="default-timestamp",
        environment="local",
        ingestion_manifest_path=ingestion.manifest_path,
        medallion_manifest_path=medallion.manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        approved_bronze_path=ingestion.approved_path,
        output_path=tmp_path / "evidence" / "default-timestamp.json",
        schema_registry_report_uri=schema_registry_report.output_path.as_posix(),
        access_policy_check_id=access_policy_report.report["check_id"],
        access_policy_report_uri=access_policy_report.output_path.as_posix(),
    )

    assert evidence["generated_at"].endswith("Z")
    assert "release_passed" in evidence
    assert evidence["schema_registry_report_hash"] == sha256_file(schema_registry_report.output_path)
    assert evidence["access_policy_report_hash"] == sha256_file(access_policy_report.output_path)


def gates_by_id(evidence: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(gate["gate_id"]): gate
        for gate in evidence["gates"]
        if isinstance(gate, dict)
    }


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    content = "".join(
        f"{json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n"
        for record in records
    )
    path.write_text(content, encoding="utf-8")


def write_external_attestation(
    path: Path,
    evidence_kind: str,
    *,
    release_id: str,
    environment: str = "prod",
    data_product: str | None = None,
    dataset_snapshot_id: str | None = None,
    content_hash: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "external_evidence_attestation.v1",
        "evidence_kind": evidence_kind,
        "subject_uri": f"s3://dp-evidence/{evidence_kind}/prod-complete.json",
        "subject_hash": f"sha256:{hashlib.sha256(evidence_kind.encode('utf-8')).hexdigest()}",
        "environment": environment,
        "release_id": release_id,
        "producer": "data-platform-control-plane",
        "generated_at": EVALUATION_TIME,
        "signature_algorithm": "Ed25519",
        "signing_key_id": "local-test-ed25519-2026",
        "passed": True,
    }
    if data_product is not None:
        payload["data_product"] = data_product
    if dataset_snapshot_id is not None:
        payload["dataset_snapshot_id"] = dataset_snapshot_id
    if content_hash is not None:
        payload["content_hash"] = content_hash
    signature = Ed25519PrivateKey.from_private_bytes(TEST_SIGNING_SEED).sign(attestation_signing_payload(payload))
    payload["signature"] = f"base64:{base64.b64encode(signature).decode()}"
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n",
        encoding="utf-8",
    )
    return path


def write_retention_job_evidence(path: Path, *, release_id: str, snapshot_id: str, content_hash: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "retention_erasure_job_evidence.v1",
        "producer": "retention-orchestrator",
        "generated_at": EVALUATION_TIME,
        "data_product": "gold.recsys_interactions",
        "release_id": release_id,
        "dataset_snapshot_id": snapshot_id,
        "table_version": content_hash,
        "content_hash": content_hash,
        "evidence": {
            "retention_job_run_id": {
                "id": "retention-job-001",
                "status": "passed",
                "job_run_id": "retention-job-001",
                "observed_at": EVALUATION_TIME,
            },
            "subject_key_coverage": {
                "id": "coverage-001",
                "status": "passed",
                "coverage_percent": 100.0,
                "observed_at": EVALUATION_TIME,
            },
            "expired_record_scan": {
                "id": "expired-scan-001",
                "status": "passed",
                "expired_record_count": 0,
                "observed_at": EVALUATION_TIME,
            },
            "erasure_request_replay": {
                "id": "erasure-replay-001",
                "status": "passed",
                "sample_request_count": 3,
                "replay_passed": True,
                "observed_at": EVALUATION_TIME,
            },
            "residual_subject_scan": {
                "id": "residual-scan-001",
                "status": "passed",
                "residual_match_count": 0,
                "observed_at": EVALUATION_TIME,
            },
            "legal_hold_check": {
                "id": "legal-hold-001",
                "status": "passed",
                "active_legal_hold_count": 0,
                "observed_at": EVALUATION_TIME,
            },
        },
    }
    path.write_text(
        f"{json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'))}\n",
        encoding="utf-8",
    )
    return path


def write_recommendation_snapshot_evidence(path: Path, *, release_id: str, ingestion: object, medallion: object) -> Path:
    replay = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        SAMPLE_INPUT,
        Path(getattr(ingestion, "manifest_path")).parents[1],
        ingested_at="2026-01-15T10:12:00Z",
        ingest_run_id=f"{release_id}-replay",
        schema_id="registry:recommendation.tracking.v1:1",
    )
    ledger = write_offset_ledger_report(
        ROOT,
        path.parent / "offset-ledger.json",
        source_id="lms-courseflow-recommendation-tracking-collector",
        environment="prod",
        ingestion_manifest_path=getattr(ingestion, "manifest_path"),
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id=f"iceberg-bronze-{release_id}",
        table_metadata_uri="s3://dp-prod-lakehouse/warehouse/bronze/events_recommendation_tracking/metadata/00001.metadata.json",
        table_metadata_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        committed_at="2026-01-15T10:12:05Z",
        generated_at=EVALUATION_TIME,
    )
    metadata_path = path.parent / "snapshot-metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "format": "iceberg",
                "snapshots": [
                    recommendation_snapshot_metadata_entry(
                        data_product="silver.learner_activity",
                        snapshot_id=f"iceberg-silver-{release_id}",
                        upstream_snapshot_ids=[f"iceberg-bronze-{release_id}"],
                        layer_manifest=getattr(medallion, "manifest")["layers"]["silver.learner_activity"],
                    ),
                    recommendation_snapshot_metadata_entry(
                        data_product="gold.recsys_interactions",
                        snapshot_id=f"iceberg-gold-{release_id}",
                        upstream_snapshot_ids=[f"iceberg-silver-{release_id}"],
                        layer_manifest=getattr(medallion, "manifest")["layers"]["gold.recsys_interactions"],
                    ),
                ],
            },
            ensure_ascii=True,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    result = write_snapshot_evidence_report(
        ROOT,
        path,
        environment="prod",
        pipeline_manifest_path=getattr(medallion, "manifest_path"),
        snapshot_metadata_path=metadata_path,
        primary_output="gold.recsys_interactions",
        source_offset_ledger_path=ledger.output_path,
        release_id=release_id,
        use_case_id="ml-feature-governance",
        runner_id="recommendation.from_approved_bronze.v1",
        code_commit_sha="abc123",
        release_evidence_profile_id="local-medallion-release.v1",
        release_evidence_profile_hash=hash_release_profile_registry(ROOT),
        generated_at=EVALUATION_TIME,
    )
    assert result.report["passed"] is True
    return result.output_path


def recommendation_snapshot_metadata_entry(
    *,
    data_product: str,
    snapshot_id: str,
    upstream_snapshot_ids: list[str],
    layer_manifest: dict[str, object],
) -> dict[str, object]:
    contract = data_product_contract(ROOT, data_product)
    layer = str(contract["layer"]).lower()
    table_name = data_product.split(".", 1)[1]
    return {
        "data_product": data_product,
        "layer": contract["layer"],
        "iceberg_table_identifier": f"prod_lakehouse.{layer}.{table_name}",
        "snapshot_id": snapshot_id,
        "parent_snapshot_id": None,
        "sequence_number": 1,
        "operation": "append",
        "committed_at": "2026-01-15T10:12:10Z",
        "metadata_uri": f"s3://dp-prod-lakehouse/warehouse/{layer}/{table_name}/metadata/00001.metadata.json",
        "metadata_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        "manifest_list_uri": f"s3://dp-prod-lakehouse/warehouse/{layer}/{table_name}/metadata/snap-00001.avro",
        "manifest_list_hash": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        "schema_id": f"contract:{data_product}:v{contract['contract_version']}",
        "schema_hash": contract["schema_hash"],
        "partition_spec_id": f"{data_product}.partition.v1",
        "partition_spec_hash": "sha256:4444444444444444444444444444444444444444444444444444444444444444",
        "min_event_time": "2026-01-15T10:00:00Z",
        "max_event_time": "2026-01-15T10:08:00Z",
        "freshness_timestamp": "2026-01-15T10:12:10Z",
        "upstream_snapshot_ids": upstream_snapshot_ids,
        "row_count": layer_manifest["row_count"],
        "content_hash": layer_manifest["content_hash"],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
