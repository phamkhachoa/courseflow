from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.catalog_runtime_ops import write_catalog_runtime_ops_report


ROOT = Path(__file__).resolve().parents[1]


def test_catalog_runtime_ops_report_passes_with_managed_catalog_evidence(tmp_path: Path) -> None:
    evidence = write_managed_catalog_runtime_evidence(tmp_path / "catalog-runtime-evidence.json", environment="staging")

    result = write_catalog_runtime_ops_report(
        ROOT,
        tmp_path / "catalog-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]

    assert report["artifact_type"] == "catalog_runtime_ops_report.v1"
    assert report["capability_id"] == "production-catalog-runtime"
    assert report["mode"] == "runtime_attested"
    assert report["readiness_state"] == "production_like_ready"
    assert report["passed"] is True
    assert summary["replica_count"] == 3
    assert summary["availability_zones"] == 3
    assert summary["multi_az"] is True
    assert summary["failover_passed"] is True
    assert summary["stale_commit_rejected"] is True
    assert summary["backup_enabled"] is True
    assert summary["pitr_enabled"] is True
    assert summary["audit_failed_event_count"] == 0


def test_catalog_runtime_ops_report_fails_closed_for_local_environment(tmp_path: Path) -> None:
    evidence = write_managed_catalog_runtime_evidence(tmp_path / "catalog-runtime-evidence.json", environment="local")

    result = write_catalog_runtime_ops_report(
        ROOT,
        tmp_path / "catalog-runtime-ops.json",
        environment="local",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )

    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["readiness_state"] == "not_ready"
    assert "environment_production_like" in failed_checks


def test_catalog_runtime_ops_report_rejects_thin_runtime_evidence(tmp_path: Path) -> None:
    evidence = write_managed_catalog_runtime_evidence(tmp_path / "catalog-runtime-evidence.json", environment="staging")
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["failover"]["failover_passed"] = False
    payload["concurrency"]["stale_commit_rejected"] = False
    payload["backup_restore"]["pitr_enabled"] = False
    evidence.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_catalog_runtime_ops_report(
        ROOT,
        tmp_path / "catalog-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] >= 3
    assert {"failover_passed", "stale_commit_rejected", "pitr_enabled"}.issubset(failed_checks)


def test_catalog_runtime_ops_report_rejects_sample_or_unredacted_evidence(tmp_path: Path) -> None:
    evidence = write_managed_catalog_runtime_evidence(tmp_path / "catalog-runtime-evidence.json", environment="staging")
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    payload["sample"] = True
    payload["client_secret"] = "plain-secret-value"
    evidence.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_catalog_runtime_ops_report(
        ROOT,
        tmp_path / "catalog-runtime-ops.json",
        environment="staging",
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    failed_checks = {item["name"] for item in result.report["checks"] if item["passed"] is not True}

    assert result.report["passed"] is False
    assert "sample_evidence_denied" in failed_checks
    assert "plaintext_secret_material_absent" in failed_checks


def test_catalog_runtime_ops_cli(tmp_path: Path) -> None:
    evidence = write_managed_catalog_runtime_evidence(tmp_path / "catalog-runtime-evidence.json", environment="staging")
    output = tmp_path / "catalog-runtime-ops.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "catalog-runtime-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(output),
            "--environment",
            "staging",
            "--evidence",
            str(evidence),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["readiness_state"] == "production_like_ready"
    assert summary["stale_commit_rejected"] is True
    assert output.is_file()


def write_managed_catalog_runtime_evidence(path: Path, *, environment: str) -> Path:
    release_id = f"{environment}-catalog-runtime-release"
    change_ticket = "CHG-DP-CATALOG-20260616"
    warehouse_uri = f"s3://enterprise-dp-{environment}/warehouse"
    service_identity = f"svc-dp-{environment}-table-format"
    upstream_hash = fake_sha256("trino-iceberg-minio-smoke-report")
    payload = {
        "artifact_type": "managed_catalog_runtime_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "evidence_source": "external_attestation",
        "production_evidence": True,
        "sample": False,
        "redacted": True,
        "release_id": release_id,
        "change_ticket": change_ticket,
        "catalog": {
            "provider": "iceberg-rest",
            "catalog_id": f"dp-{environment}-iceberg-rest",
            "service_id": "table_format",
            "service_identity": service_identity,
            "endpoint_uri": f"https://iceberg-rest.{environment}.dp.example",
            "warehouse_uri": warehouse_uri,
            "metadata_store": "postgresql-ha",
            "catalog_hash": fake_sha256(f"{environment}:catalog-state"),
        },
        "deployment": {
            "replica_count": 3,
            "availability_zones": 3,
            "multi_az": True,
            "health_check_passed": True,
            "managed_service": True,
            "ha_mode": "managed_ha",
        },
        "failover": {
            "failover_tested": True,
            "failover_passed": True,
            "failover_seconds": 45,
            "read_after_failover_passed": True,
            "write_after_failover_passed": True,
        },
        "concurrency": {
            "optimistic_locking": True,
            "concurrent_commit_probe_passed": True,
            "stale_commit_rejected": True,
            "lost_update_prevented": True,
            "latest_snapshot_preserved": True,
            "cross_engine_read_after_conflict_passed": True,
            "conflict_count": 1,
        },
        "backup_restore": {
            "backup_enabled": True,
            "pitr_enabled": True,
            "restore_tested": True,
            "restore_test_passed": True,
            "rpo_minutes": 5,
            "rto_minutes": 30,
        },
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/catalog-runtime",
            "events_hash": fake_sha256("catalog-runtime-audit-events"),
            "event_count": 19,
            "failed_event_count": 0,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "subject_hash": fake_sha256("catalog-runtime-attestation-subject"),
        },
        "upstream_evidence": [
            {
                "name": "trino_iceberg_minio_smoke",
                "artifact_type": "trino_iceberg_minio_smoke_report.v1",
                "artifact_hash": upstream_hash,
                "passed": True,
            }
        ],
        "binding": {
            "release_id_hash": fake_sha256(release_id),
            "change_ticket_hash": fake_sha256(change_ticket),
            "warehouse_uri_hash": fake_sha256(warehouse_uri),
            "catalog_service_identity_hash": fake_sha256(service_identity),
            "upstream_evidence_hashes": [upstream_hash],
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def fake_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
